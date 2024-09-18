SkyPortal provides an API to access most of its underlying
functionality. To use it, you will need an API token. This
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

#### Command line (curl)

```shell
curl -s -H 'Authorization: token ea70a5f0-b321-43c6-96a1-b2de225e0339' http://localhost:5000/api/sysinfo
```

### Request parameters

There are two ways to pass information along with a request: path and body parameters.

#### Path parameters

Path parameters (also called query or URL parameters) are embedded in
the URL called. For example, you can specify `numPerPage` or
`pageNumber` path parameters when calling `/api/candidates` as
follows:

```shell
curl -s -H 'Authorization: token ea70a5f0-b321-43c6-96a1-b2de225e0339' \
     http://localhost:5000/api/candidates?numPerPage=100&pageNumber=1
```

When using Python's `requests` library, a dictionary of path
parameters can be passed in via the `params` keyword argument:

```python
token = 'ea70a5f0-b321-43c6-96a1-b2de225e0339'

response = requests.get(
    "http://localhost:5000/api/sources",
    params={"includeComments": True, "includeThumbnails": False},
    headers={'Authorization': f'token {token}'},
)
```

#### Body parameters

Request body parameters (or simply: the body of the request)
contains data uploaded to a specific endpoint. These are the
parameters listed under `REQUEST BODY SCHEMA: application/json` in the
API docs.

When using Python's `requests` library, body parameters are specified
using the `json` keyword argument:

```python
token = "abc"
response = requests.post(
    "http://localhost:5000/api/sources",
    json={
        "id": "14gqr",
        "ra": 353.36647,
        "dec": 33.646149,
        "group_ids": [52, 97],
    },
    headers={"Authorization": f"token {token}"},
)
```

### Response

In the above examples, the SkyPortal server is located at
`http://localhost:5000`. In case of success, the HTTP response is 200:

```

HTTP code: 200, OK
JSON response: {'status': 'success', 'data': {}, 'version': '0.9.dev0+git20200819.84c453a'}

```

On failure, it is 400; the JSON response has `status="error"` with the reason
for the failure given in `message`:

```js
{
  "status": "error",
  "message": "Invalid API endpoint",
  "data": {},
  "version": "0.9.1"
}
```

### Pagination

Several API endpoints (notably the sources and candidates APIs) enforce
pagination to limit the number of records that can be fetched per request.
These APIs expose parameters that facilitate pagination (see the various
API docs for details). A sample pagination script is included here:

```python
import requests
import time


base_url = "https://fritz.science/api/sources"
token = "your_token_id_here"
group_ids = [4, 71]  # If applicable
max_retries = 3


params = {
    'page': 1,
    'group_ids': ','.join([str(gid) for gid in group_ids],
    'num_per_page': 500,
    'totalMatches': None
}

all_sources = []

retries_remaining = max_retries
while retries_remaining > 0:
    r = requests.get(
        base_url,
        params=params,
        headers={"Authorization": f"token {token}"},
    )

    if r.status_code == 429:
        print("Request rate limit exceeded; waiting 1s before trying again...")
        time.sleep(1)
        continue

    data = r.json()

    if data["status"] == "success":
        retries_remaining = max_retries
    else:
        print(f"Error: {data["message"]}; waiting 5s before trying again...")  # log as appropriate
        retry_attempts -= 1
        time.sleep(5)
        continue

    all_sources.extend(data["data"]["sources"])
    total_matches = data["data"]["totalMatches"]

    print(f"Fetched {len(all_sources)} of {total_matches} sources.")

    if len(all_sources) >= total_matches:
        break

    params[page] += 1
```
