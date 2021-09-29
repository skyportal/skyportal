# Advanced usage

## Posting color-magnitude data to generate an HR diagram

For stellar targets we are interested in showing the HR diagram
based on the color-magnitude data from a cross match to, e.g., the Gaia catalog.
Currently we support only Gaia inputs on the front-end,
but in a future release we may expand the notion of the HR diagram
to arbitrary catalogs.

This is done by posting an `Annotation` to the source, with correctly formatted data.
If at least one properly formatted `Annotation` with Gaia color-magnitude data
exists on the source, an HR diagram will be rendered for it.

First let's see how to post an `Annotation` using the `requests` package.
Here is a working example:

```
import requests
import json

url = 'http://localhost:5000'
token = '239868fa-8307-41ad-983f-4a8180609df6'
header = {"Authorization": f"token {token}", "content_type": "application/json"}
data = {'obj_id': '2021example',
        'origin': 'cross_match_robot',
        'Gaia': {'Mag_G', 10.2,
                 'Mag_Bp': 9.8,
                 'Mag_Rp': 10.5,
                 'Plx': 8.5
                 }
        }

response = requests.post(
      f'{url}/api/sources/2021example/annotation',
      header=header,
      data=json.dumps(data)
    )

```

Let's look at this line by line.

The `url` should point to the SkyPortal instance,
in this case running on a local machine.

The `token` should be generated for your user
through the profile page.
The token must have the ACL to annotate.

The `header` is used to pass along the SkyPortal authentication token.

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
the system only recognizes annotations
with a specific schema:
- One of the keys in the `Annotation` data must be named `Gaia`.
- The value of that key must be a dictionary.
- That dictionary must contain the following entries:
- `Mag_G', 'Mag_Bp', 'Mag_Rp', 'Plx'.
- All these names (including the catalog name) may be made customizable
  in a future release. Currently, the HR diagram is drawn only for Gaia data.
- The names are searched ignoring case, and removing underscores.
  So, for example, the dictionary can contain `mag_g` or `MagG`,
  and would still be accepted as data for an HR diagram.
  Please do not include multiple data keys with indistinguishable names,
  i.e., both `mag_g` and `Mag_G` in the same `Annotation` as this will
  cause undefined behavior.

Finally, the return value `response` from the request
should contain a `status==200` and a data dictionary
with the data that was posted.
If the posting was unsuccessful,
the status would be 400.



## Spectroscopic lines

The line list implemented on SkyPortal was derived using the [NIST atomic database](https://www.nist.gov/pml/atomic-spectra-database), employing the methods of [Gal-Yam  2019](https://ui.adsabs.harvard.edu/abs/2019ApJ...882..102G/abstract).
