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
        'data': {
            'Gaia': {
                'Mag_G', 10.2,
                'Mag_Bp': 9.8,
                'Mag_Rp': 10.5,
                'Plx': 8.5
               }
            }
        }

response = requests.post(
      f'{url}/api/sources/2021example/annotations',
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
and it should contain the annotation `data`,
that is a dictionary with arbitrary entries.

In general, the `origin` field is used to
enumerate the different services that would
annotate each source.
Each origin can only post a single `Annotation`
to each source, but that `Annotation` can contain arbitrary data.

In the case of the color-magnitude plot,
the system only recognizes annotations
with a specific schema:
- One of the keys in the annotation `data` must be named `Gaia`.
- The value of that key must be another dictionary.
- That dictionary must contain the following entries:
- 'Mag_G', 'Mag_Bp', 'Mag_Rp', 'Plx'.
- All these names (including the catalog name) may be made customizable
  in a future release. Currently, the HR diagram is drawn only for Gaia data.
- The names are searched ignoring case, and removing underscores.
  So, for example, the dictionary can contain `mag_g` or `MagG`,
  and would still be accepted as data for an HR diagram.
  Please do not include multiple data keys with indistinguishable names,
  i.e., both `mag_g` and `Mag_G` in the same `Annotation` as this will
  cause undefined behavior.
- The parallax ("Plx") is given in units of milli-arcsec.

Finally, the return value `response` from the request
should contain a `status==200` and a data dictionary
with the data that was posted.
If the posting was unsuccessful,
the status would be 400.

## Managing Taxonomies

Taxonomies are used for classification. There is typically a sitewide taxonomy that all users of SkyPortal can see. By default, we seed a new SP database with the latest taxonomy from the [Time-domain Astronomy Taxonomy
 (Github)](https://github.com/profjsb/timedomain-taxonomy) (`tdtax`). From time to time, the latest taxonomy may be upgraded as new subclasses of sources are discovered and SP admins may need to push a new version of the taxonomy to the live application.

### Upgrading the Sitewide Taxonomy

To upgrade to the latest `tdtax`, as an admin, you will need to generate a token with a "Post taxonomy" ACL. Next install the latest `tdtax` on your system:

```
pip install -U tdtax
```

Next, in Python:

```python
import requests
import tdtax

tax_obj =  {'name': 'Sitewide Taxonomy',
            'provenance': 'https://github.com/profjsb/timedomain-taxonomy',
            'hierarchy': tdtax.taxonomy,
            'version': str(tdtax.__version__),
}

token = "USE-YOUR-TOKEN-HERE"
def api(method, endpoint, data=None):
    headers = {'Authorization': f'token {token}'}
    response = requests.request(method, endpoint, json=data, headers=headers)
    return response

response = api('POST',
               'URL_TO_SKYPORTAL_INSTANCE/api/taxonomy',
                data=tax_obj)

print(response.json())
```
You should then see something like:

```
{'status': 'success',
 'data': {'taxonomy_id': 9},
 'version': '0.9.dev0+git...'}
```

If the `name` of the taxonomy is exactly the same as a taxonomy already in the system, this new taxonomy will supercede that taxonomy. That is, by default it will be set to be the latest version (`IsLatest = True`) and shown to end users in the dropdown menu on the Source page. Older classifications will be still associated with the `taxonomy_id` they were originally connected to.

### Posting a New Taxonomy

You may wish to post a new custom taxonomy, for example to enable classifications that are outside the scope of the sitewide taxonomy. When posting a new taxonomy, it is usually preferable to limit its availability to specific, relevant groups. In this way, you can assign your own classifications where needed without extending them across the entire site.

To post a new taxonomy to specific groups, follow the instructions above, but add the `group_ids` parameter (containing the array of group ids to receive the taxonomy) to `tax_obj`. Ensure your new taxonomy is in a nested JSON format.

Once the taxonomy is posted, users who are members of the specified groups will be able to see and use the new classifications. To add the taxonomy to another group, perform another `POST` request containing the desired group id.

### NOTE: Deleting a Taxonomy

In very rare cases you may wish to delete a taxonomy (e.g., if you made a typo when loading it). This should be done with extreme care: if anyone has classifications associated with that taxonomy their classifications will be lost upon delete.

## Spectroscopic lines

The selection of element and galaxy lines on SkyPortal were derived from the NIST atomic database (<https://www.nist.gov/pml/atomic-spectra-database>) , using the methods of Gal-Yam (2019) (<https://ui.adsabs.harvard.edu/abs/2019ApJ...882..102G/abstract>). Telluric and Skylines were migrated from the ZTF Marshal.
Element lines and galaxy lines move according to the set redshift or expansion velocity. Tellurics and skylines remain static.
