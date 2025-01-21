#!/usr/bin/env python

r"""

direct_insert_to_tables

Directly upload rows to the database (using the credentials in config.yaml).

First, figure out what you want to upload and get that data from
a database backup. For example:

```
$ PGPASSWORD="<secret>" psql -h <database-backup-ip> -U <user> <dbname>
psql> \copy (select * from classifications WHERE created_at > '<DATE>')
         TO 'new_classifications.csv' csv header;
```

This will create a new file called `new_classifications.csv`.

Then run this script:
```
PYTHONPATH=. python tools/direct_insert_to_tables.py new_classifications.csv \
             classifications --delete_id=True --config=<location of config files>
```

The first argument is the filename, the second is the table name, and the third is the delete_id flag.
You can also provide a location of where the files are stored (`new_data_dir`, default is `./`)
and a verbose flag (`verbose`, default is `False`).
Each row is added sequentially and referential integrity issues are caught.

"""

import fire
import pandas as pd

from baselayer.app.env import load_env
from baselayer.app.models import init_db

_, cfg = load_env()
db_info = cfg["database"]
engine = init_db(**cfg["database"])


def insert_data(filename, tablename, delete_id=True, new_data_dir="./", verbose=False):
    r"""
    Direcly insert data to the database. Only do this
    as a last resort if you cannot add data via the API.

    tables format: (filename, db table name, delete `id`)
       you probably want to remove the `id` column from most
       tables except for followuprequests and objs

    """
    # Load the data
    opd = pd.read_csv(new_data_dir + filename)

    print(f"Length of {tablename} file = {len(opd)}.")

    if delete_id and tablename != "objs":
        del opd["id"]
    else:
        if verbose:
            print(f"Note: not deleting the `id` for this table {tablename}.")

    total = 0
    for index, row in opd.iterrows():
        try:
            rdf = pd.DataFrame([row])
            # make sure if_exists = "append" so as not to overwrite the data
            _ = rdf.to_sql(
                tablename, engine, if_exists="append", index=False, method=None
            )
            print(f"Inserted {rdf['obj_id']} into `{tablename}`.")
            total += 1
        except Exception as e:
            print(f"Error inserting into `{tablename}`: {row['obj_id']}")
            if verbose:
                print(f"Error message: {e}")

    print(f"Added {total} rows to {tablename}.")


if __name__ == "__main__":
    fire.Fire(insert_data)
