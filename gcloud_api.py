import requests
import json
import time
import datetime
import os
import sys


class GrafanaCloudApi:
    
    def __init__(self, token, logger, org_slug=None,grafna_root_url = "https://grafana.com"):
        self.token = token
        self.org_slug = org_slug
        self.grafana_root_url = grafna_root_url
        self.logger = logger
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }
    

    def handle_response(self, response,success_codes=[200,201,204]):
        response.raise_for_status()
        
        if response.status_code not in success_codes:
            print(f"Error: {response.text}")
            sys.exit(1)
        # handle if response is empty
        if response.text == "": return response
        else: return response.json()
    

    # ---------------------------------------------------------------------------
    # Stacks
    def get_stacks(self,org_slug=None):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#list-stacks
        success_codes = [200]
        org_slug = org_slug if org_slug is not None else self.org_slug
        self.logger.info(f"Getting stacks for org {org_slug}")
        url = f'{self.grafana_root_url}/api/orgs/{org_slug}/instances'
        response = self.handle_response(requests.get(url, headers=self.headers),success_codes)
        stack_names = [stack["name"] for stack in response["items"]]
        self.logger.debug(f"Found {len(response['items'])} stacks. {stack_names}")
        return response
    
    def create_stack(self,name,slug,url=None,description=None,labels=None,region="us"):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#create-stack
        # TODO: do something with the response codes
        success_codes = [200]
        body = {
            "name": name,
            "slug": slug,
            "region": region,
        }
        if url is not None: body["url"] = url
        if description is not None: body["description"] = description
        if labels is not None: body["labels"] = labels
        # POST https://grafana.com/api/instances
        url = f'{self.grafana_root_url}/api/instances'
        self.logger.info(f"Creating stack {name}")
        response = self.handle_response(requests.post(url, headers=self.headers, data=json.dumps(body)),success_codes)
        self.logger.debug(f"Created stack {name} {response}")
        return response

    def update_stack(self,stack_id_or_slug,name=None,description=None,labels=None):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#update-stack
        success_codes = [200]
        body = {k: v for k, v in {
            'description': description,
            'labels': labels,
            'name': name
        }.items() if v is not None}
        url = f'{self.grafana_root_url}/api/instances/{stack_id_or_slug}'
        self.logger.info(f"Updating stack {stack_id_or_slug}")
        response = self.handle_response(requests.post(url, headers=self.headers, data=json.dumps(body)),success_codes)
        self.logger.debug(f"Updated stack {stack_id_or_slug} {response}")
        return response 

    def delete_stack(self,stack_id):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#delete-stack
        success_codes = [200]
        url = f'{self.grafana_root_url}/api/instances/{stack_id}'
        self.logger.info(f"Deleting stack {stack_id}")
        response = self.handle_response(requests.delete(url, headers=self.headers),success_codes)
        self.logger.debug(f"Deleted stack {stack_id}")
        return response
    
    def upsert_stack(self,name,slug,url=None,region="us",description=None,labels=None):
        # Method 
        self.logger.info(f"Syncing stack {name}")
        existing_stacks = self.get_stacks()                                                                                          # get all stacks
        body = { k: v for k, v in {                                                                                                 # create body
            "name": name,
            "slug": slug,
            "url": url,
            "region": region,
            "description": description,
            "labels": labels
        }.items() if v is not None }
        existing_stack = next((stack for stack in existing_stacks["items"] if stack["name"] == name), None)                     # find existing stack   
        if existing_stack is None:  new_stack = self.create_stack(name,slug,url,region,description,labels)                  # create new stack if not found
        else: self.update_stack(existing_stack["id"],name,description,labels)                                                      # update existing stack
        existing_stacks = self.get_stacks()                                                                                         # get all stacks                                    
        new_stack = next((stack for stack in existing_stacks["items"] if stack["name"] == name), None)                        # find new stack
        return new_stack

    def restart_stack(self,stack_slug):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#restart-grafana
        url = f'{self.grafana_root_url}/api/instances/{stack_slug}/restart'
        self.logger.info(f"Restarting stack {stack_slug}")
        response = self.handle_response(requests.post(url, headers=self.headers))
        self.logger.debug(f"Restarted stack {stack_slug}")
        return response

    # def create_stack_api_key(self,stack_slug,name,role,secondsToLive=None):
    #     # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#create-hosted-grafana-instance-api-keys
    #     success_codes = [200]
    #     url = f'{self.grafana_root_url}/api/instances/{stack_slug}/api/auth/keys'
    #     self.logger.info(f"Creating stack api key for stack {stack_slug}")
    #     body = {
    #         "name": name,
    #         "role": role,
    #     }
    #     if secondsToLive is not None: body["secondsToLive"] = secondsToLive
    #     response = self.handle_response(requests.post(url, headers=self.headers, data=json.dumps(body)),success_codes)
    #     self.logger.debug(f"Created stack api key for stack {stack_slug}")
    #     return response

    def list_stack_datasources(self,stack_slug):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#list-data-sources
        url = f'{self.grafana_root_url}/api/instances/{stack_slug}/datasources'
        success_codes = [200]
        self.logger.info(f"Listing datasources for stack {stack_slug}")
        response = self.handle_response(requests.get(url, headers=self.headers),success_codes)
        self.logger.debug(f"Found {len(response['items'])} datasources for stack {stack_slug}")
        return response

    #------------------------------------------------
    # Access Policies
    def get_access_policies(self,name=None,realmType=None,realmIdentifier=None,pageSize=None,pageCursor=None,region='us',status=None):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#list-access-policies
        success_codes = [200]
        self.logger.info(f"Getting access policies")
        url = f'{self.grafana_root_url}/api/v1/accesspolicies'
        params = {k: v for k, v in {
                'name': name,
                'realmType': realmType,
                'realmIdentifier': realmIdentifier,
                'pageSize': pageSize,
                'pageCursor': pageCursor,
                'region': region,
                'status': status
            }.items() if v is not None}
        response = self.handle_response(requests.get(url, headers=self.headers, params=params),success_codes)
        self.logger.debug(f"Found {len(response['items'])} access policies")
        return response
    
    def get_access_policy(self,access_policy_id,region=None):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#list-one-access-policy
        success_codes = [200]
        params = {'region': region}
        self.logger.info(f"Getting access policy {access_policy_id}")
        url = f'{self.grafana_root_url}/api/v1/accesspolicies/{access_policy_id}'
        response = self.handle_response(requests.get(url, headers=self.headers, params=params),success_codes)
        self.logger.debug(f"Found access policy {access_policy_id} {response}")
        return response


    def create_access_policy(self,policy_name,display_name,label_policies,region,realmIdentifier,realmType="stack",scopes=["metrics:read", "logs:read", "traces:read", "alerts:read"],conditions=None):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#create-an-access-policy
        success_codes = [200]
        self.logger.info(f"Creating access policy {policy_name}")
        url = f'{self.grafana_root_url}/api/v1/accesspolicies'
        realms = [{
                "type":realmType,
                "identifier":str(realmIdentifier),
                "labelPolicies":label_policies
                }]
        data = {}
        data["name"] = policy_name
        data["displayName"] = display_name
        data["realms"] = realms
        data["scopes"] = scopes
        # data["conditions"] = conditions
         
        params = {'region': region}
        response = self.handle_response(requests.post(url, headers=self.headers, params=params, data=json.dumps(data)),success_codes)
        self.logger.debug(f"Created access policy {policy_name} {response}")
        return response
    
    def update_access_policy(self,access_policy_id,display_name,label_policies,region,realmIdentifier,realmType="stack",scopes=["metrics:read", "logs:read", "traces:read", "alerts:read"],conditions=None):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#update-an-access-policy
        success_codes = [200]
        self.logger.info(f"Updating access policy {access_policy_id}")
        url = f'{self.grafana_root_url}/api/v1/accesspolicies/{access_policy_id}'
        realms = [{
                "type":realmType,
                "identifier":str(realmIdentifier),
                "labelPolicies":label_policies
                }]
        data = {}
        data["displayName"] = display_name
        data["realms"] = realms
        data["scopes"] = scopes
        # data["conditions"] = conditions

        params = {'region': region}
        response = self.handle_response(requests.post(url, headers=self.headers, params=params, data=json.dumps(data)),success_codes)
        self.logger.debug(f"Updated access policy {access_policy_id}")
        return response
    
    def delete_access_policy(self,access_policy_id,region):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#delete-an-access-policy
        self.logger.info(f"Deleting access policy {access_policy_id}")
        success_codes = [204]
        params = {'region': region}
        url = f'{self.grafana_root_url}/api/v1/accesspolicies/{access_policy_id}'
        response = self.handle_response(requests.delete(url, headers=self.headers, params=params),success_codes)
        self.logger.debug(f"Deleted access policy {access_policy_id}")
        return response



    def upsert_access_policy(self,policy_name,display_name,label_policies,region,realmIdentifier,realmType="stack",scopes=["metrics:read", "logs:read", "traces:read", "alerts:read"],conditions=None):
        # Method 
        self.logger.info(f"Upserting access policy {policy_name}")
        existing_access_policies = self.get_access_policies(realmType=realmType,realmIdentifier=realmIdentifier,region=region)
        existing_access_policy = next((access_policy for access_policy in existing_access_policies["items"] if access_policy["name"] == policy_name), None)
        if existing_access_policy is None: 
            try:
                response = self.create_access_policy(policy_name,display_name,label_policies,region,realmIdentifier,realmType,scopes,conditions)
            except:
                #  delete the access policy and try again
                self.delete_access_policy(policy_name,region)
                response = self.create_access_policy(policy_name,display_name,label_policies,region,realmIdentifier,realmType,scopes,conditions)
            
        else: response = self.update_access_policy(existing_access_policy["id"],display_name,label_policies,region,realmIdentifier,realmType,scopes,conditions)
        self.logger.debug(f"Upserted access policy {policy_name} {response}")
        existing_access_policies = self.get_access_policies(realmType=realmType,realmIdentifier=realmIdentifier,region=region)
        new_access_policy = next((access_policy for access_policy in existing_access_policies["items"] if access_policy["name"] == policy_name), None)
        return new_access_policy
    # ------------------------------------------------
         

    # Access Policy Tokens
    def get_access_policy_tokens(self,region='us',access_policy_id=None,access_policy_name=None,access_policy_realm_type=None,access_policy_realm_identifier=None,name=None,expiresBefore=None,expiresAfter=None,pageSize=None,pageCursor=None,access_policy_status=None):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#list-a-set-of-tokens
        self.logger.info(f"Getting access policy tokens for access policy {access_policy_id}")
        params = { k : v for k, v in {
        'region': region,'accessPolicyName': access_policy_name, 'accessPolicyRealmType': access_policy_realm_type, 'accessPolicyRealmIdentifier': access_policy_realm_identifier, 'name': name, 'expiresBefore': expiresBefore, 'expiresAfter': expiresAfter, 'pageSize': pageSize, 'pageCursor': pageCursor, 'status': access_policy_status
        }.items() if v is not None}

        url = f'{self.grafana_root_url}/api/v1/tokens'
        response = self.handle_response(requests.get(url, headers=self.headers, params=params))
        self.logger.debug(f"Found {len(response['items'])} access policy tokens")
        return response
    
    def get_access_policy_token(self,token_id,region):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#list-a-single-token
        self.logger.info(f"Getting access policy token {token_id}")
        url = f'{self.grafana_root_url}/api/v1/tokens/{token_id}'
        params = {'region': region}
        response = self.handle_response(requests.get(url, headers=self.headers, params=params))
        self.logger.debug(f"Found access policy token {token_id} {response}")
        return response
    
    def update_token_name(self,token_id,new_name,region):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#update-a-token
        self.logger.info(f"Updating access policy token {token_id}")
        url = f'{self.grafana_root_url}/api/v1/tokens/{token_id}'
        params = {'region': region}
        data = {
            "display_name": new_name
        }
        response = self.handle_response(requests.post(url, headers=self.headers, params=params, data=json.dumps(data)))
        self.logger.debug(f"Updated access policy token {token_id} {response}")
        return response

    def delete_access_policy_token(self,token_id,region):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#delete-an-access-policy
        success_codes = [204]
        self.logger.info(f"Deleting access policy token {token_id}")
        url = f'{self.grafana_root_url}/api/v1/tokens/{token_id}'
        params = {'region': region}
        response = self.handle_response(requests.delete(url, headers=self.headers, params=params),success_codes)
        self.logger.debug(f"Deleted access policy token {token_id}")
        return response

    def create_access_policy_token(self,name,display_name,access_policy_id,region,expire_date=None):
        # https://grafana.com/docs/grafana-cloud/developer-resources/api-reference/cloud-api/#create-a-token
        self.logger.info(f"Creating access policy token for access policy {access_policy_id}")
        url = f'{self.grafana_root_url}/api/v1/tokens'
        params = {'region': region} 
        data = { k : v for k, v in {
            "name": name,
            "displayName": display_name,
            "accessPolicyId": access_policy_id,
            "expiresAt": expire_date.isoformat() if expire_date is not None else None
        }.items() if v is not None}
        response = self.handle_response(requests.post(url, headers=self.headers, params=params, data=json.dumps(data)))
        self.logger.debug(f"Created access policy token {name} {response}")
        return response


    def upsert_access_policy_token(self,name,display_name,access_policy_id,region,expire_date=None,replace=True):
        # Method 
        self.logger.info(f"Upserting access policy token {name}")
        existing_access_policy_tokens = self.get_access_policy_tokens(region)
        existing_access_policy_token = next((access_policy_token for access_policy_token in existing_access_policy_tokens["items"] if access_policy_token["name"] == name), None)
        if existing_access_policy_token is None: response = self.create_access_policy_token(name,display_name,access_policy_id,region,expire_date)
        elif not replace: response = self.update_token_name(existing_access_policy_token["id"],display_name,region)
        else:
            self.delete_access_policy_token(existing_access_policy_token["id"],region)
            response = self.create_access_policy_token(name,display_name,access_policy_id,region,expire_date) 
        self.logger.debug(f"Upserted access policy token {name} {response}")
        return response