# skyportal-py-models

Pydantic models describing SkyPortal API requests and responses, shared by
[`skyportal-py`](../python-client) and the server.

Every module maps to one SkyPortal API resource and holds the payload and
response models for it. The client re-exports them alongside its endpoint
functions, so these name the same class:

```python
from skyportal_py.groups import Group
from skyportal_py_models.groups import Group
```

All models use `extra="forbid"`: an unknown field in a request payload or a
server response raises a validation error rather than passing silently.
