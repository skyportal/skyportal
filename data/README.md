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
  
  Also, it adds a python script that allows to load data from Grandma's collaboration owncloud, you can use it with 2 commands :
  -In this directory using : python3 seed_grandma.py "owncloud_username" "owncloud_password"
  
  -In SkyPortal main directory using : make seed_grandma PARAMS='"owncloud_username" "owncloud_password"'
  
  IMPORTANT : as seed_grandma import users data which is not public. You need to add grandma.sql file to this folder yourself, then run sql_to_csv.py, before running seed_grandma
