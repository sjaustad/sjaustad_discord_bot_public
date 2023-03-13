import requests, re, asyncio
class API:
    def __init__(self):
        self.client_id = "wiw9lnt2tlrra1opq65defj6u00aje"
        self.client_secret = "ivf7e4o1p74q9ks05jhdf0iso59kjc"
        self.token_url = "https://id.twitch.tv/oauth2/token"
        self.base_url = "https://api.igdb.com/v4"
        self.access_token = None
        self.expiry = None
        self.newToken()

    def newToken(self):
        client_info = {
            "client_id":self.client_id,
            "client_secret":self.client_secret,
            "grant_type":"client_credentials"
        }
        response = requests.post(self.token_url, json=client_info)
        key_info = response.json()
        self.access_token = key_info['access_token']
        self.expiry = key_info['expires_in']
    
    async def apiRequest(self, end_point, request_data):
        if self.access_token is None:
            return print("No access token, cannot proceed")
        headers = {
            'Client-ID': self.client_id,
            'Authorization': f"Bearer {self.access_token}"
        }
        try:
            request_data = request_data.encode() # Remove non-ascii characters
        except AttributeError:
            pass #Already encoded data
        response = requests.post(f"{self.base_url}/{end_point}", headers=headers, data=request_data)
        results = response.json()
        try:
            if results['message'] == 'Too Many Requests':
                print("Too many requests, waiting...")
                await asyncio.sleep(0.25)
                return await self.apiRequest(end_point, request_data)
        except (TypeError, KeyError):
            return results





