import json

from baselayer.app.app_server import handlers as baselayer_handlers
from skyportal import openapi
from skyportal.app_server import skyportal_handlers

spec = openapi.spec_from_handlers(baselayer_handlers + skyportal_handlers)

f = open('openapi.yml', 'w')
f.write(spec.to_yaml())
f.close()
f = open('openapi.json', 'w')

json.dump(spec.to_dict(), f)
print("OpenAPI spec written to openapi.{yml,json}")
