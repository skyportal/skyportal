#!/usr/bin/env python

r"""

patch_db_tables

Directly upload rows to the database (using the credentials in config.yaml).

First, figure out what you want to upload and get that data from
a database backup. For example:

```
$ PGPASSWORD="<secret>" psql -h <database-backup-ip> -U <user> <dbname>
psql> \copy (select * from classifications WHERE created_at > '<DATE>')
         TO 'new_classifications.csv' csv header;
```

This will create a new file called `new_classifications.csv`.
Edit this script and change `new_data_dir` and `tables` variables
accordingly.

Then run this script:
```
python tools/upload.py --config=/etc/skyportal/config.yaml
```

Each row is added sequentially and referential integrity issues are caught.

"""

import pandas as pd
from sqlalchemy import create_engine

from baselayer.app.env import load_env

# EDIT ME: new_data_dir, tables, verbose
new_data_dir = "./"

# tables format: (filename, db table name, delete `id`)
#   you probably want to remove the `id` column from most
#   tables except for followuprequests and objs

# tables = [("new_objs.csv", "objs", False)]
tables = [("new_classifications.csv", "classifications", True)]
# tables = [("new_followuprequests.csv", "followuprequests", True)]
# tables = [("new_comments.csv", "comments", True)]
# tables = [("new_spectra.csv", "spectra", True)]
# tables = [("new_annotations_1.csv", "annotations", True)]
# tables = [("new_missing_followuprequests.csv", "followuprequests", False)]

verbose = False

####

env, cfg = load_env()

db_info = cfg["database"]


engine = create_engine(
    f"postgresql://{db_info['user']}:{'' if db_info['password'] is None else db_info['password']}"
    f"@{db_info['host']}:{db_info['port']}/{db_info['database']}"
)


for table in tables:

    # Load the objects
    objs_file = table[0]
    opd = pd.read_csv(new_data_dir + objs_file)

    print(f"Length of {table[1]} file = {len(opd)}.")

    if table[2] and table[1] != 'objs':
        del opd["id"]
    else:
        if verbose:
            print("Note: not deleting the `id` for this table {table[1]}.")

    total = 0

    for index, row in opd.iterrows():
        try:
            rdf = pd.DataFrame([row])
            # make sure if_exists = "append" so as not to overwrite the data
            inserted = rdf.to_sql(
                table[1], engine, if_exists="append", index=False, method=None
            )
            print(f"Inserted {rdf['obj_id']} into `{table[1]}`.")
            total += 1
        except Exception as e:
            print(f"Error inserting into `{table[1]}`: {row['obj_id']}")
            if verbose:
                print(f"Error message: {e}")

    print(f"Added {total} to {table[1]}")
