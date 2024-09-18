import json

import jinja2

from baselayer.app.env import load_env

_, cfg = load_env()

# open the openapi.json file
# and patch the doc/api.html.template file with the new content
with open('openapi.json') as f:
    openapi_spec = json.load(f)

# here, we could add a list of servers to the openapi_spec
# for the scalar docs to let the users point to when testing an endpoint
servers = cfg.get("docs.servers", [])
# validate that servers have only 2 keys: url and description
if not isinstance(servers, list) and servers is not None:
    raise ValueError("API servers must be a list.")
if servers is not None:
    for server in servers:
        if not all(k in server for k in ("url", "description")):
            raise ValueError("Each server must have 'url' and 'description' keys.")
    openapi_spec['servers'] = servers
else:
    openapi_spec['servers'] = []

# Create a Jinja2 template environment
template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./"))

# Load the template file
template = template_env.get_template("doc/openapi.html.template")

# Render the template with the OpenAPI spec
output = template.render(openapi_spec=json.dumps(openapi_spec, indent=2))

# Write the output to a new HTML file
with open("doc/openapi.html", "w") as f:
    f.write(output)
