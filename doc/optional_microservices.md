# Optional Microservices

## Details about Microservices

SkyPortal's architecture relies heavy on microservices using supervisor to manage them. For example, the app (backend, api based) runs as multiple instances of a microservice, gcnevents are ingested as a listener running as a microservice, and so on. Most services (other than ones coming from baselayer) can be found in the `services` directory.
Each microservice has a dedicated directory containing a python file, and a config file for supervisor.

If one desires to add more functionality to the app, which is not part of the core, one can easily add a new microservice. Moreover, optional services can be added to SkyPortal core as well, but they are not activated by default. This is done to keep the core as light as possible, and to allow users to activate only the services they need.

## Fink Broker Microservice

Following this logic of optional microservice, we developed a Fink broker microservice. This microservice can be added by specifying the related configuration in the `config.yaml` file of SkyPortal. The microservice will then be activated and will start listening to the Fink broker. When a new alert is received, it will be ingested into SkyPortal and will be available for the user to interact with.

The microservice is activated by adding the following configuration in the `config.yaml` file before starting SkyPortal:

```yaml

fink:
  client_id: <your_client_id>
  client_secret: <your_client_secret> (optional, can be left empty if you don't have a secret)
  client_group_id: <your_group_id>
  topics:
  - fink_kn_candidates_ztf
  - fink_early_kn_candidates_ztf
  - fink_rate_based_kn_candidates_ztf
  - fink_sn_candidates_ztf
  - fink_early_sn_candidates_ztf
  - <and so on>
  servers: <list of servers as a comma separated string>

```

Then, as SkyPortal is started, the microservice will start listening to new alerts from Fink broker. For every new alert, a candidate will be posted, as well as auto-annotations, and the fink classification. If the alert is on a new object, the object and the source(s) will be created as well.
When the services starts for the first time (or if the config is modified), a filter will be created for each topic, as well as a Fink stream and a Fink Group.
If you want to the sources and candidates to be posted to your group, you need to make sure that all users have access to the Stream, after which you can associate it to your group (as well as the filters for the topics you want to use).

It also comes with additional dependencies, which can be found in the `requirements.txt` located in the `services/fink` directory. You can install them after installing SkyPortal's dependencies by running:

```bash

pip install -r services/fink/requirements.txt

```
