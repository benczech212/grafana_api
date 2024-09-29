import requests
import sys
import base64


class PrometheusApi:
    def __init__(self, url, user, token):
        self.url = url
        self.token = token
        self.user = user
        self.headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic ' + base64.b64encode(f"{self.user}:{self.token}".encode()).decode()
        }
 
    def handle_response(self, response):
        response.raise_for_status()
        if response.status_code != 200:
            print(f"Error: {response.text}")
            sys.exit(1)
        return response.json()


    def query(self, query):
        url = f'{self.url}/api/prom/api/v1/query'
        params = {'query': query}
        response = requests.get(url, headers=self.headers, params=params)
        return self.handle_response(response)
    