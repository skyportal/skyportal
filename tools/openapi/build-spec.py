from skyportal import app_server
from baselayer.app.env import load_env

import json

env, cfg = load_env()
app = app_server.make_app(cfg, [], {})
f = open("openapi.yml", "w")
f.write(app.openapi_spec.to_yaml())
f.close()
f = open("openapi.json", "w")

json.dump(app.openapi_spec.to_dict(), f)
print("OpenAPI spec written to openapi.{yml,json}")
