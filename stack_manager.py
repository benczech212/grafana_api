from gcloud_api import GrafanaCloudApi
from grafana_api import GrafanaApi
from prometheus_api import PrometheusApi
import yaml
import logging
import os
import sys
import datetime
CONFIG_FILE = "config.yml"
SECRET_FILE = "secrets.yml"




def load_yml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)
   





class StackManager:
    def __init__(self,config,secrets):
        self.config = config
        self.secrets = secrets
        self.logger = self.setup_logger()
        self.cloud_api = GrafanaCloudApi(secrets["GRAFANA_CLOUD_TOKEN"], self.logger,org_slug=config["org_slug"])
        self.stacks = self.cloud_api.get_stacks()
        self.main_stack_name = config['main_stack']['name']
        self.main_stack = [stack for stack in self.stacks["items"] if stack["name"] == self.main_stack_name]
        if not self.main_stack:
            self.logger.error(f"Main stack {self.main_stack_name} not found")
            sys.exit(1)
        else: self.main_stack = self.main_stack[0]
        self.main_stack_grafana_api = GrafanaApi(secrets["GRAFANA_TOKEN"],self.main_stack["url"],self.logger)
        self.client_info = self.get_clients_from_prometheus(self.stacks,self.main_stack_name)
            
    def setup_logger(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config["log_level"])
        ch = logging.StreamHandler()
        ch.setLevel(self.config["log_level"])
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        log_file_path = self.config["log_file"]
        if not os.path.exists(log_file_path):
            with open(log_file_path, 'w') as log_file:
                log_file.write('')
        fh = logging.FileHandler(log_file_path)
        fh.setLevel(self.config["log_level"])
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        print(f"Log file created at {self.config['log_file']}")
        return self.logger
    
    
    def create_stacks(self,primary_key="client_name",env={'client_environment':"Production"},excludes=None):
        excludes = self.config["client_names_to_skip"] if not excludes else excludes
        self.logger.info("Creating stacks")
        env_key, env_value = list(env.items())[0]
        unique_environments = set([client["client_name"] for client in self.client_info.values() if client[env_key] == env_value and client[primary_key] not in excludes])
        self.logger.debug(f"Unique environments: {unique_environments}")
        for environment in unique_environments:
            self.logger.info(f"Creating stack for {environment}")
            slug = 'fortna-' + environment.lower().replace(" ", "-")
            
            # Create stack
            self.logger.info(f"Creating stack {environment} with slug {slug}")
            new_stack = self.cloud_api.upsert_stack(name=environment,slug=slug,region=self.main_stack["regionSlug"],description=f"Stack for {environment}",labels={"client-name": environment, "client-slug": slug, "client-environment": "Production"})
            new_grafana_api = GrafanaApi(secrets["GRAFANA_TOKEN"],new_stack["url"],self.logger)
            # Create access policy
            self.logger.info(f'Creating access policy for {environment}')
            new_access_policy = self.create_access_policy(new_stack,environment,slug)
            
            # Create access policy token
            self.logger.info(f"Creating access policy token for {environment}")
            token_name = f"{slug}-token"
            token_display_name = f"Token for {environment}"
            token_expire_date = datetime.datetime.now() + datetime.timedelta(days=365)
            new_token = self.create_access_policy_token(token_name,token_display_name,new_access_policy["id"],new_stack["regionSlug"],token_expire_date)
            
            # Create prometheus datasource
            self.logger.info(f"Creating datasource for {environment}")
            self.create_prometheus_datasource(new_grafana_api,environment,slug,self.main_stack["hmInstancePromUrl"],self.main_stack["hmInstancePromId"],new_token)
         
       
            


    def create_prometheus_datasource(self,api,name,uid,url,user,password,org_id=1,is_default=True):
        data = {
            "name": name,
            "orgId": org_id,
            "uid": uid,
            "type": "prometheus",
            "typeName": "Prometheus",
            "typeLogoUrl": "public/app/plugins/datasource/prometheus/img/prometheus_logo.svg",
            "access": "proxy",
            "url": f"{url}/api/prom",
            "basicAuth":True,
            "basicAuthUser": str(user),
            # "basicAuthPassword": token_value,
            "secureJsonData": {"basicAuthPassword": password},
            "isDefault": is_default,
            "jsonData":
                {
                    "prometheusType": "Mimir",
                    "prometheusVersion": "2.9.1",
                    "timeInterval": "60s"
                }
            }
        new_datasource = api.upsert_datasource(data)
        
            
    def create_access_policy(self,new_stack,client_name,slug,scopes=["metrics:read","logs:read","traces:read"]):
        name = f"{slug}-access-policy"
        display_name = f"Access policy - Data from {self.main_stack['name']} for {new_stack['name']} in stack {slug}"
        stack_id = self.main_stack["id"]
        region = new_stack["regionSlug"]
        
        label_policies = [{"selector":"{client_name=\""+client_name+"\", client_environment=\"Production\"}"}]
        new_access_policy = self.cloud_api.upsert_access_policy(name,display_name,label_policies,region,stack_id,realmType="stack",scopes=scopes)
        return new_access_policy
         

    def create_access_policy_token(self,token_name,token_display_name,access_policy_id,region,token_expire_date=None):
        new_token = self.cloud_api.upsert_access_policy_token(token_name,token_display_name,access_policy_id,region,token_expire_date)
        return new_token['token']



    def get_clients_from_prometheus(self,stacks,main_stack_name,primary_key="client_key",labels=["client_name", "client_location", "client_environment", "client_key"]):
        self.logger.info("Getting clients from Prometheus")
        by_string = ",".join(labels)
        filter_string = ",".join([f'{label}!=""' for label in labels])
        query_string = f'count by({by_string}) (sum by({by_string}) (up{{{filter_string}}}))'
        main_stack = [stack for stack in stacks["items"] if stack["name"] == main_stack_name]
        if not main_stack:
            self.logger.error(f"Main stack {main_stack_name} not found")
            return {}
        else: main_stack = main_stack[0]
        promethues_url = main_stack["hmInstancePromUrl"]
        prometheus_user = main_stack["hmInstancePromId"]
        prometheus_token = secrets.get("PROMETHEUS_TOKEN")
        prom_api = PrometheusApi(promethues_url,prometheus_user,prometheus_token)
        response = prom_api.query(query_string)
        results = response.get("data", {}).get("result", [])
        clients = {}
        for result in results:
            client_info = {}
            for label in labels:
                client_info[label] = result.get("metric", {}).get(label, "")
            key = client_info.pop(primary_key, "")
            clients[key] = client_info
        return clients



 
config = load_yml(CONFIG_FILE)
secrets = load_yml(SECRET_FILE)
stack_manager = StackManager(config,secrets)
stack_manager.create_stacks()
