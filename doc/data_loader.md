# Data loader

To populate SkyPortal with initial data, use `tools/data_loader.py`.
This is also used when doing `make load_seed_data` and `make
load_demo_data`.

The data loader reads a data file in YAML format.  This YAML files
matches the SkyPortal API: each entry corresponds to an API endpoint,
and contains a list of objects to post (see `data/db_demo.yaml` for an
example).

## References

The attributes of a posted object can be saved as references:

```
groups:
  - name: Program A
    group_admins:
      - testadmin@cesium-ml.org
    =id: program_A
```

Here, the `id` field of the created group is stored as `program_A`.
This can now be used when, e.g., posting a telescope:

```
telescope:
  - name: Palomar 1.5m
    nickname: P60
    lat: 33.3633675
    lon: -116.8361345
    elevation: 1870
    diameter: 1.5
    skycam_link: http://bianca.palomar.caltech.edu/images/allsky/AllSkyCurrentImage.JPG
    group_ids:
      - =program_A
```

Endpoints can also contain references:

```
groups/=program_A/users:
  - username: viewonlyuser@cesium-ml.org
    admin: false

```

Here, the endpoint will become, e.g., `groups/6/users`.

## Files

Lists of objects to post can be loaded through a top-level file entry:

```
telescope:
  file: telescopes.yaml
```

If objects reference `png` files, those will be read in and posted as
b64-encoded bytes:

```
thumbnail:
  - obj_id: 14gqr
    ttype: new
    data:
      file: ../skyportal/tests/data/14gqr_new.png
```

CSV files are read as columns, each of which becomes an entry in the
posted object:

```
photometry:
  - obj_id: 14gqr_unsaved_copy
    file: phot.csv
    group_ids:
      - =program_A
```

Here, `phot.csv` has columns `filter`, `mjd`, etc., so each of those
would become an entry in the posted object, each with a list of
values.
