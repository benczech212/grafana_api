import requests
import json
import sys


class GrafanaApi:
    def __init__(self, token,grafana_root_url,logger):
        # 
        self.token = token
        self.logger = logger
        self.grafana_root_url = grafana_root_url
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }
    def handle_response(self, response):
        success_codes = [200,201,204]
        if response.status_code not in success_codes:
            print(f"Error: {response.text}")
            response.raise_for_status()
            sys.exit(1)
        # handle if response is empty
        if response.text == "": return response
        else: return response.json()


    ############################################################
    # Roles
    def get_roles(self):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/http-api/access_control/#get-all-roles
        self.logger.info(f"Getting roles")
        url = f'{self.grafana_root_url}/api/access-control/roles'
        response = self.handle_response(requests.get(url, headers=self.headers))
        self.logger.debug(f"Found {len(response)} roles")
        return response
    
    def get_role(self,role_uid):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/http-api/access_control/#get-a-custom-role
        self.logger.info(f"Getting role {role_uid}")
        url = f'{self.grafana_root_url}/api/access-control/roles/{role_uid}'
        response = self.handle_response(requests.get(url, headers=self.headers))
        self.logger.debug(f"Got role {role_uid}\n{response}")
        return response

    def create_role(self,name,uid,display_name,description,group,permissions):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/http-api/access_control/#create-a-new-custom-role
        self.logger.info(f"Creating role {name}")
        url = f'{self.grafana_root_url}/api/access-control/roles'
        data = {
            "uid": uid,
            "name": name,
            "displayName": display_name,
            "description": description,
            "group": group,
            "permissions": permissions

        }
        try: response = self.handle_response(requests.post(url, headers=self.headers, data=json.dumps(data)))
        except: response = self.get_role(uid)
        self.logger.debug(f"Created role {name} {response}")
        return response
    
    def delete_role(self,role_uid,params = {'force': True}):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/http-api/access_control/#delete-a-custom-role
        self.logger.info(f"Deleting role {role_uid}")
        url = f'{self.grafana_root_url}/api/access-control/roles/{role_uid}'
        response = self.handle_response(requests.delete(url, headers=self.headers, params=params))
        self.logger.debug(f"Deleted role {role_uid}")
        return response
    

    ############################################################
    # Folders
    def get_folders(self):
        url = f"{self.grafana_root_url}/api/folders"
        response = self.handle_response(requests.get(url, headers=self.headers))
        return response

    def get_folder(self,folder_uid,handle=True):
        self.logger.debug(f"Getting folder {folder_uid}")
        url = f"{self.grafana_root_url}/api/folders/{folder_uid}"
        response = requests.get(url, headers=self.headers)
        if handle: response = self.handle_response(response)
        self.logger.debug(f"Got folder {folder_uid}")
        return response

    def create_folder(self,folder_title,folder_uid,parent_folder_uid=None,org_id=1):
        try: folder_exists = True if self.get_folder(folder_uid,handle=False) else False
        except: folder_exists = False
        
        if not folder_exists:    
            self.logger.debug("Creating folder")
            url = f"{self.grafana_root_url}/api/folders"
            data = {"title": folder_title, "uid": folder_uid, "orgId": org_id}
            response = self.handle_response(requests.post(url, headers=self.headers, data=json.dumps(data)))
            if parent_folder_uid: self.move_folder(folder_uid,parent_folder_uid)
            self.logger.debug(f"Created folder {folder_title}")
            return response
        else:
            self.logger.debug(f"Folder {folder_uid} already exists")
            return folder_exists

    def move_folder(self,folder_uid,parent_folder_uid):
        self.logger.debug(f"Moving folder {folder_uid} to {parent_folder_uid}")
        url = f"{self.grafana_root_url}/api/folders/{folder_uid}/move"
        data = {"parentUid": parent_folder_uid}
        response = self.handle_response(requests.post(url, headers=self.headers, data=json.dumps(data)))
        self.logger.debug(f"Moved folder {folder_uid} to {parent_folder_uid}")
        return response
    
    def ensure_folder(self,folder_title,folder_uid,parent_folder_uid=None,org_id=1):
        existing_folders = self.get_folders()
        folder = next((folder for folder in existing_folders if folder["uid"] == folder_uid), None)
        if folder is None: folder = self.create_folder(folder_title,folder_uid,parent_folder_uid,org_id)
        return self.get_folder(folder_uid)
            

        
        
        

    ############################################################
    # Folder Permissions
    def get_folder_permisions(self,folder_uid):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/http-api/folder_permissions/#get-permissions-for-a-folder
        self.logger.info(f"Getting folder permissions for folder {folder_uid}")
        url = f'{self.grafana_root_url}/api/folders/{folder_uid}/permissions'
        response = self.handle_response(requests.get(url, headers=self.headers))
        self.logger.debug(f"Found {len(response['items'])} folder permissions")
        return response
    
    def update_folder_permissions(self,folder_uid,items):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/http-api/folder_permissions/#update-permissions-for-a-folder
        self.logger.info(f"Updating folder permissions for folder {folder_uid}")
        url = f'{self.grafana_root_url}/api/folders/{folder_uid}/permissions'
        data = {
            "items": items
        }
        response = self.handle_response(requests.post(url, headers=self.headers, data=json.dumps(data)))
        self.logger.debug(f"Updated folder permissions for folder {folder_uid}")
        return response
    ############################################################
    # Datasources
    def get_datasources(self):
        self.logger.info(f"Getting datasources")
        url = f"{self.grafana_root_url}/api/datasources"
        response = self.handle_response(requests.get(url, headers=self.headers))
        self.logger.debug(f"Found {len(response)} datasources")
        return response
        
    def delete_datasource_by_name(self,datasource_name):
        self.logger.info(f"Deleting datasource {datasource_name}")
        url = f"{self.grafana_root_url}/api/datasources/name/{datasource_name}"
        response = self.handle_response(requests.delete(url, headers=self.headers))
        self.logger.debug(f"Deleted datasource {datasource_name}")
        return response
    
    def delete_datasource_by_uid(self,datasource_ui):
        self.logger.info(f"Deleting datasource {datasource_ui}")
        url = f"{self.grafana_root_url}/api/datasources/uid/{datasource_ui}"
        response = self.handle_response(requests.delete(url, headers=self.headers))
        self.logger.debug(f"Deleted datasource {datasource_ui}")
        return response
    
    
    def get_datasource_by_uid(self,datasource_uid):
        self.logger.info(f"Getting datasource {datasource_uid}")
        url = f"{self.grafana_root_url}/api/datasources/uid/{datasource_uid}"
        response = self.handle_response(requests.get(url, headers=self.headers))
        self.logger.debug(f"Got datasource {datasource_uid}")
        return response
    
    def create_datasource(self,data):
        self.logger.info("Creating datasource")
        url = f"{self.grafana_root_url}/api/datasources"
        response = self.handle_response(requests.post(url, headers=self.headers, data=json.dumps(data)))
        self.logger.debug(f"Created datasource {response}")
        return response
    
    
    def upsert_datasource(self,data,delete_conflicts=False):
        existing_datasources = self.get_datasources()
        new_datasource_name = data["name"]
        new_datasource_uid = data["uid"]
        datasource = next((datasource for datasource in existing_datasources if datasource["name"] == new_datasource_name), None) # Check if datasource exists by name
        if datasource is None: datasource = next((datasource for datasource in existing_datasources if datasource["uid"] == new_datasource_uid), None) # Check if datasource exists by uid
        if datasource is not None and delete_conflicts: self.delete_datasource_by_uid(datasource["uid"]) # Delete datasource if it exists and delete_conflicts is True
        if datasource is None: datasource = self.create_datasource(data) # Create datasource if it does not exist
        
        return self.get_datasource_by_uid(new_datasource_uid)
    
    def ensure_datasource_type(self,datasource_type,name,uid,url,user,password,org_id=1):
        self.logger.info(f"Creating datasource type {datasource_type}")
        if datasource_type == "prometheus":
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
            "isDefault":False,
            "jsonData":
                {
                    "prometheusType": "Mimir",
                    "prometheusVersion": "2.9.1",
                    "timeInterval": "60s"
                }
            }
        elif datasource_type == "loki":
            data = {
            "name": name,
            "uid": uid,
            "orgId": org_id,
            "type": "loki",
            "typeName": "Loki",
            "typeLogoUrl": "public/app/plugins/datasource/loki/img/loki_logo.svg",
            "access": "proxy",
            "url": url,
            "basicAuth":True,
            "basicAuthUser": str(user),
            "secureJsonData": {"basicAuthPassword": password},
            "isDefault":False,
            "jsonData":
                {
                    "lokiType":"Loki",
                    "manageAlerts": False,
                    "timeout": "300"
                }
            }
        else:
            self.logger.error(f"Datasource type {datasource_type} not supported")
            sys.exit(1)
        return self.upsert_datasource(data)

    ############################################################
    ## Teams
    def get_team(self,team_id):
        self.logger.info(f"Getting team {team_id}")
        url = f"{self.grafana_root_url}/api/teams/{team_id}"
        response = self.handle_response(requests.get(url, headers=self.headers))
        self.logger.debug(f"Got team {team_id}")
        return response

    def get_teams(self):
        self.logger.info(f"Getting teams")
        url = f"{self.grafana_root_url}/api/teams/search"
        response = self.handle_response(requests.get(url, headers=self.headers))
        team_count = response["totalCount"]
        self.logger.debug(f"Found {team_count} teams")
        return response['teams']
    
    def create_team(self,team_name,org_id=1):
        self.logger.info(f"Creating team {team_name}")
        url = f"{self.grafana_root_url}/api/teams"
        data = {"name": team_name, "orgId": org_id}
        response = self.handle_response(requests.post(url, headers=self.headers, data=json.dumps(data)))
        new_team_id = response["teamId"]
        self.logger.debug(f"Created team {team_name}")
        return self.get_team(new_team_id)
    
    def delete_team(self,team_id):
        self.logger.info(f"Deleting team {team_id}")
        url = f"{self.grafana_root_url}/api/teams/{team_id}"
        response = self.handle_response(requests.delete(url, headers=self.headers))
        self.logger.debug(f"Deleted team {team_id}")
        return response


    ############################################################        
    # Team roles
    def add_team_role_assignment(self,team_id,role_uid):
        self.logger.info(f"Adding role {role_uid} to team {team_id}")
        url = f'{self.grafana_root_url}/api/access-control/teams/{team_id}/roles'
        data = {
            "roleUid": role_uid
        }
        response = self.handle_response(requests.post(url, headers=self.headers, data=json.dumps(data)))
        self.logger.debug(f"Added role {role_uid} to team {team_id}")
        return response
    


    def create_team_datasource_permissions(self,datasource_uid,team,permission):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/http-api/datasource_permissions/#add-or-revoke-access-to-a-data-source-for-a-team
        self.logger.info("Creating team datasource permissions")
        team_id = str(team["id"])
        url = f"{self.grafana_root_url}/api/access-control/datasources/{datasource_uid}/teams/{team_id}"
        data = {"permission":permission}
        response = self.handle_response(requests.post(url, headers=self.headers, data=json.dumps(data)))
        return response



    
    def delete_role_datasource_permissions(self,datasource_uid,role_name):
        self.logger.info("Removing role datasource permissions")
        url = f"{self.grafana_root_url}/api/access-control/datasources/{datasource_uid}/builtInRoles/{role_name}"
        response = self.handle_response(requests.delete(url, headers=self.headers))
        return response
    
    def create_role_datasource_permissions(self,datasource_uid,role_name,permission):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/http-api/datasource_permissions/#add-or-revoke-access-to-a-data-source-for-a-basic-role
        self.logger.info("Creating role datasource permissions")
        url = f"{self.grafana_root_url}/api/access-control/datasources/{datasource_uid}/builtInRoles/{role_name}"
        data = {"permission":permission}
        # Query, Edit Admin
        response = self.handle_response(requests.post(url, headers=self.headers, data=json.dumps(data)))
        return response