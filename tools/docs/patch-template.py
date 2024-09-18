import json

import jinja2

# open the openapi.json file
# and patch the doc/api.html.template file with the new content
with open('openapi.json') as f:
    openapi_spec = json.load(f)

# add a list of servers to the openapi spec
openapi_spec['servers'] = [
    {'url': 'https://fritz.science', 'description': 'Fritz - Production'},
    {'url': 'https://preview.fritz.science', 'description': 'Fritz - Preview'},
    {'url': 'http://localhost:8000', 'description': 'SkyPortal - Dev'},
]

# Create a Jinja2 template environment
template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./"))

# Load the template file
template = template_env.get_template("doc/openapi.html.template")

# Render the template with the OpenAPI spec
output = template.render(openapi_spec=json.dumps(openapi_spec, indent=2))

# Write the output to a new HTML file
with open("doc/openapi.html", "w") as f:
    f.write(output)
