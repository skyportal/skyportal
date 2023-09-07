# Usage

## Permissions

Access to resources in Skyportal is controlled in two ways:

- *ACLs* control which actions a user is allowed to perform: create a new user, upload spectra, post comments, etc.
- *Groups* are sets of sources that are accessible to members of that group
    - Members can also be made an *admin* of the group, which gives them group-specific permissions to add new users, etc.
    - The same source source can belong to multiple groups

*Roles* are collections of *ACLs*, and are a convenient way of giving
users the same subset of permissions.

## Adding roles to users

- User permissions can be managed on the `/users/` page (click through from profile)

## Adding users to groups

- Groups membership can be managed on the `/groups/` page (click through from profile)

## Managing source classifications

On the frontend, classifications can be managed from an individual source page or a group sources page.

### On a source page:

- Scroll to Classifications, choose the desired group(s) for the classification from the Choose Group dropdown
- Select the desired taxonomy from the Taxonomy dropdown
- In the Classification dropdown, choose the appropriate label
- Assign a probability in the range [0, 1] in the Probability box
- Click SUBMIT to post the classification
- Classifications can be deleted using the trash bin button

### On a group sources page:

- Click the dropdown arrow to the left of a source id
- Under Post Classifications, select a taxonomy from the dropdown
- Select one of the Nonstellar or Stellar variable categories
- The resulting dropdown contains sliders for each classification that can be dragged to the desired probability among [0, 0.25, 0.5, 0.75, 1]
- If Normalize Probabilities is toggled, probabilities on a given level of the taxonomy will be scaled to sum to unity
- Click SUBMIT CLASSIFICATIONS when finished

### Programmatic access:

- The API allows classifications to be managed using HTTP requests (see <https://skyportal.io/docs/api.html>).
- The `GET` request allows existing classifications for a source with id `source_id` to be retrieved:
```
status, data = api(
        'GET',
        f'sources/{source_id}/classifications',
        token=classification_token
    )
```
- The `POST` request uploads new classifications for multiple sources using the following structure:
```
data = {
         'classifications': [
             {
                 'obj_id': public_source.id,
                 'classification': 'Algol',
                 'taxonomy_id': taxonomy_id,
                 'probability': 1.0,
                 'group_ids': [public_group.id],
             },
             {
                 'obj_id': public_source.id,
                 'classification': 'Time-domain Source',
                 'taxonomy_id': taxonomy_id,
                 'probability': 1.0,
                 'group_ids': [public_group.id],
             },
         ]
     }
```
```
status, data = api(
         'POST',
         'classification',
         data=post_data,
         token=classification_token,
     )
```
- Classifications can be modified and deleted with the `PUT` and `DELETE` requests, respectively. These requests require the integer classification ID provided by the `GET` request. Both requests are made to the endpoint `'classification/{classification_id}'`.

## Important Makefile targets

Run `make` to get a list of Makefile targets.  Here are some commonly
used ones:

General:

- help : Describe make targets

DB preparation:

- db_init : Create database
- db_clear : Drop and re-create DB

Launching:

- run : Launch the web application
- log : Tail all log files

Testing:

- test : Launch web app & execute frontend tests
- test_headless : (Linux only) The above, but without a visible browser

Development:

- lint-githook : Install a Git pre-commit hook that lints staged
                 chunks (this is done automatically when you lint
                 for the first time).


## Code formatting / linters

To set up `pre-commit` for automatically reformatting Python and JavaScript changes, run `pip install pre-commit && pre-commit install`.

`pre-commit` is run each time a new change is committed. If an error can be fixed automatically (such as a spacing issue), the tool does that automatically, and you can re-attempt the commit. Otherwise, you may have to make the change manually.
