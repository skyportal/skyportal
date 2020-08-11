# Datasets

These YAML files contain data for configuring SkyPortal instances.

Specifically, it contains:

- *Seeding data*: common telescopes, instruments, and a taxonomy.  You
  will likely want to load this data for every deployed instance of
  SkyPortal, and can do so with the `make load_seed_data` command.

- *Demo data*: example data that illustrates the functionality of
  SkyPortal.  This can be used for demonstrating the system, but
  will not be loaded into a research installation.  Load this dataset using
  `make load_demo_data`.
