
import urllib
import requests

api_token = "f652c854-67d7-4ae8-a0b8-1ac9d8c23290"
host = "http://localhost:5000"

endpoint = "gcn_event"

url = urllib.parse.urljoin(host, f'/api/{endpoint}')
headers = {'Authorization': f'token {api_token}'}

datafile = f'GBM.xml'
with open(datafile, 'rb') as fid:
    payload = fid.read()
data = {'xml': payload}

r = requests.post(url, headers=headers, json=data)
print(r.text)

