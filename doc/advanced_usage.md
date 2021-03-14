# Advanced usage

## Posting color-magnitude data

For stellar targets we are interested in showing the HR diagram
based on the color-magnitude data from a cross match to, e.g., the Gaia catalog.
This is done by posting an `Annotation` to the source, with correctly formatted data.

First lets see how to post an `Annotation` using the `request` package.
Here is a working example:

```
import requests
import json

url = http://localhost:5000
token = '239868fa-8307-41ad-983f-4a8180609df6'
header = {"Authorization": f"token {token}", "content_type": "application/json"}
parameters = {}
data = {'obj_id': '2021example',
        'origin': 'cross_match_robot',
        'Gaia': {'Mag_G', 10.2, 'Mag_Bp': 9.8, 'Mag_Rp': 10.5, 'Plx': 8.5}
        }

r = requests.post(
    f'{url}/api/annotation',
    header=header,
    params=parameters,
    data=json.dumps(data))

```

Lets look at this one by one.

The `url` should point to the SkyPortal instance,
in this case running on a local machine.

The `token` should be generated for your user
through the profile page.
The token must have the ACL to annotate.

The `header` uses the token above
and defines what kind of HTTP call is expected.

The `parameters` are used to define query parameters,
which are often very useful in GET calls,
but in this case are left empty.
Query parameters can also be appended to the URL
using a `?` before each `keyword=value` pair,
and each pair is separated using a `&`.

The `data` field is a dictionary that contains
information to be posted to the database.
In this case the data must be formatted
to comply with the `Annotation` API,
namely it must have a valid `obj_id`
of an existing object that is accessible to the user,
it must contain a non-empty string for the `origin`
and it should contain the `Annotation` data,
that is a dictionary with arbitrary entries.

In general, the `origin` field is used to
enumerate the different services that would
annotate each source.
Each origin can only post a single `Annotation`
to each source, but that `Annotation` can contain arbitrary data.

In the case of the color-magnitude plot,
the system only recongnizes annotations
with a specific schema:
- One of the keys in the `Annotation` data must be named `Gaia`.
- The value of that key must be a dictionary.
- That dictionary must contain the following entries:
- `Mag_G', 'Mag_Bp', 'Mag_Rp', 'Plx'.
- All these names (including the catalog name) will be made customizable
  on a future release. Currently the HR diagram is drawn only for Gaia data.
- The names are searched ignoring case, and removing underscores.
  So, for example, the dictionary can contain `mag_g` or `MagG`,
  and would still be accepted as data for an HR diagram.
  Please do not include multiple data keys with indistinguishable names,
  i.e., both `mag_g` and `Mag_G` in the same `Annotation` as this will
  cause undefinced behavior.

Finally, the return value `r` from the request
should contain a `status==200` and a return data dictionary
with the data that was posted.
If the posting was unsuccessful,
the status would be 400.
