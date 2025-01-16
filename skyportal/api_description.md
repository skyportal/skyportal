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

```sh
curl -s -H 'Authorization: token ea70a5f0-b321-43c6-96a1-b2de225e0339' http://localhost:5000/api/sysinfo
```

### Request parameters

There are two ways to pass information along with a request: path and body parameters.

#### Path parameters

Path parameters (also called query or URL parameters) are embedded in
the URL called. For example, you can specify `numPerPage` or
`pageNumber` path parameters when calling `/api/candidates` as
follows:

```sh
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

### Responses

#### Success

In the above examples, the SkyPortal server is located at
`http://localhost:5000`. In case of success, the HTTP response is 200:

```text
HTTP code: 200, OK
JSON response: {'status': 'success', 'data': {}, 'version': '0.9.dev0+git20200819.84c453a'}
```

#### Failure

On failure, it is 400; the JSON response has `status="error"` with the reason
for the failure given in `message`:

```json
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
API docs for details). Some of these endpoints (like the sources and candidates APIs) let you query lists of records that are dynamic, and often updated. In such cases, to avoid missing records or fetching duplicates, it is **strongly recommended** to use the **caching mechanism** provided by the API. Below, you'll find examples of how to paginate through the sources API with and without caching.

#### Without caching

Here is an example of how to paginate through the sources API without any caching. This is valid and the simplest way to paginate through the results of any paginated API endpoint. However, we recommend using the caching mechanism if it is available for the endpoint you are querying (see the following section).

_Warnings_:

- The `totalMatches` is not returned by all endpoints that implement caching. Please check the API documentation for the endpoint you are querying, and we recommend logging the results while debugging to make sure all is in order.

```python
import requests
import time

base_url = "https://fritz.science/api"
url = base_url + "/sources"
token = "your_token_id_here"
headers = {"Authorization": f"token {token}"}
group_ids = [4, 71]  # If applicable
max_retries = 3

params = {
    'pageNumber': 1,
    'numPerPage': 100,
    'group_ids': group_ids,
    'totalMatches': None
}

all_sources = []

retries_remaining = max_retries
while retries_remaining > 0:
    r = requests.get(
        url,
        params=params,
        headers=headers,
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

#### With caching (recommended)

If caching is enabled, the server will return a `queryID` in the response when querying the first page. This `queryID` can be used to fetch the next page of results, by simply passing it as a parameter in the next request. This way, the server can keep track of the state of the query and return the next page of results without missing or duplicating any records.

_Warnings_:

- The `queryID` is only valid for a limited time (by default 6 hours, but this can be configured by the server admin). Passed that time, the `queryID` will expire and you will need to start a new query from the beginning. You can also keep looping over the pages past the timeout, but the server will return a new queryID and consistency isn't guaranteed for the following pages.
- Not all endpoints support caching. Make sure to check the API documentation for the endpoint you are querying (look for the `useCache` & `queryID` parameters).

```python
import requests
import time

base_url = "https://fritz.science/api"
url = base_url + "/sources"
token = "your_token_id_here"
headers = {"Authorization": f"token {token}"}
group_ids = [4, 71]  # If applicable
max_retries = 3

params = {
    'pageNumber': 1,
    'numPerPage': 100,
    'group_ids': group_ids,
    'totalMatches': None,
    'useCache': True, # Enable caching
    'queryID': None # Server will return this in the first response
}

all_sources = []

retries_remaining = max_retries
while retries_remaining > 0:
    r = requests.get(
        url,
        params=params,
        headers=headers,
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
    params["queryID"] = data["data"]["queryID"] # Pass the queryID to the next request

    print(f"Fetched {len(all_sources)} of {total_matches} sources.")

    if len(all_sources) >= total_matches:
        break

    params[page] += 1
```

### API Endpoints
