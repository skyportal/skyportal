## config/ directory

This is where specific data to be loaded into SkyPortal lives in YAML files that are referred to in the `data_load` section of the `../config.yaml` in the parent directory:

`config.yaml`:

```
...
data_load:
  - db_seed
    file: configs/db_seed.yaml
  - db_demo
    file: configs/db_demo.yaml
```

