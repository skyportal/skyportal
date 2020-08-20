SkyPortal provides an API to access most of its underlying
functionality. To begin to use it, you will need an API token. This
can be generated via the web application from your profile page or, if
you are an admin, you may use the system provisioned token stored
inside of `.tokens.yaml`.

### Accessing the SkyPortal API

Once you have a token, you may access SkyPortal programmatically as
follows.

#### Python

```python
import requests

token = 'ea70a5f0-b321-43c6-96a1-b2de225e0339'

def api(method, endpoint, data=None):
    headers = {'Authorization': f'token {token}'}
    response = requests.request(method, endpoint, json=data, headers=headers)
    return response

response = api('GET', 'http://localhost:5000/api/sysinfo')

print(f'HTTP code: {response.status_code}, {response.reason}')
if response.status_code in (200, 400):
    print(f'JSON response: {response.json()}')
```

For example, if the server is running, this should yield:

```
HTTP code: 200, OK
JSON response: {'status': 'success', 'data': {}, 'version': '0.9.dev0+git20200819.84c453a'}
```

#### Command line (curl)

```shell
curl -s -H 'Authorization: token ea70a5f0-b321-43c6-96a1-b2de225e0339' http://localhost:5000/api/sysinfo
```

### Response

In the above examples, the SkyPortal server is located at
`http://localhost:5000`. The HTTP response is 200 on
success and 400 on failure. In case of failure, the response packet
has `status="error"` and the reason for the failure in `message`.
For example:

```js
{
  "status": "error",
  "message": "Invalid API endpoint",
  "data": {},
  "version": "0.9.1"
}
```
