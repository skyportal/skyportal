For this to work, you need to add the following config in your config.yaml file:

fink:
client_id: <your_fink_client_id>
client_secret: null
client_group_id: <your_fink_client_group_id>
servers: <fink_servers_ip>
topics: - fink_kn_candidates_ztf - fink_early_kn_candidates_ztf - fink_rate_based_kn_candidates_ztf - fink_sn_candidates_ztf
testing: false
schema: ./data/schema_test.avsc
maxtimeout: 5
