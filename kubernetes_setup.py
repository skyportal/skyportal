import os
from collections import Counter
from os.path import join as pjoin
import jinja2
import yaml

from baselayer.app.env import load_env
from baselayer.log import make_log
import argparse

log = make_log("kubernetes")

# this is a list of strings, each corresponding to a service or a substring in a service's name
# these services don't need a 'ports.<service>' key specified in the config file
services_no_ports = [
    'websocket_server',
    'analysis',
    'nginx',
    'gcn_service',
    'pdl_service',
    'health_monitor',
    'reminders',
    'external_logging',
    'recurrent_apis',
    'webpack',
    'message_proxy',
    'cron',
    'recurring_apis',
    'watch_list',
    'external_logging',
]


def get_services():
    env, cfg = load_env()

    services = {}
    for path in cfg["services.paths"]:
        if os.path.exists(path):
            path_services = [
                d for d in os.listdir(path) if os.path.isdir(pjoin(path, d))
            ]
            services.update({s: pjoin(path, s) for s in path_services})

    duplicates = [k for k, v in Counter(services.keys()).items() if v > 1]
    if duplicates:
        raise RuntimeError(f"Duplicate service definitions found for {duplicates}")

    disabled = cfg["services.disabled"] or []
    enabled = cfg["services.enabled"] or []

    both = set().union(disabled).intersection(enabled)
    if both:
        raise RuntimeError(
            f"Invalid service specification: {both} in both enabled and disabled"
        )

    if disabled == "*":
        disabled = services.keys()
    if enabled == "*":
        enabled = []

    services_to_run = set(services.keys()).difference(disabled).union(enabled)

    services_to_run_dict = {}
    for service in services_to_run:
        services_to_run_dict[service] = {
            'path': services[service],
        }
        # to it, add a host and port key, taken from the config file's hosts and ports
        # keys, respectively
        services_to_run_dict[service]["host"] = f"{service.replace('_', '-')}-service"
        services_to_run_dict[service]["port"] = cfg["ports"].get(service, "")
        if not any([s in service for s in services_no_ports]):
            # this service has no port specified in the config file ports.<service>
            if services_to_run_dict[service]["port"] == "":
                log(f"WARNING: No port specified for service {service}")
        elif 'analysis' in service:
            # analysis services have their ports defined in the config file
            # in the analysis_services.<service>.port
            if service not in cfg['analysis_services']:
                log(f"WARNING: No port specified for service {service}")
            else:
                services_to_run_dict[service]["port"] = cfg['analysis_services'][
                    service
                ]['port']
        if service == "app":
            # the app service has a different host name
            services_to_run_dict[service]["processes"] = cfg["server.processes"]

    log(f"Preparing images for {len(services_to_run)} services:")
    for service in services_to_run:
        log(f"  {service}")

    return services_to_run_dict


def setup_k8_services():
    services = get_services()
    # if we don't have a kubernetes/config directory, create it
    if not os.path.exists('./kubernetes/config'):
        os.mkdir('./kubernetes/config')
    else:
        # we delete all the files in the kubernetes/config directory
        for f in os.listdir('./kubernetes/config'):
            os.remove(f'./kubernetes/config/{f}')

    # then, we iterate over the services list to create a list of already used ports
    used_ports = []
    for service, conf in services.items():
        if conf['port'] != "":
            used_ports.append(conf['port'])
    # create a config file for each service
    # we have a config_templates directory with 3 templates:
    # 1. service.yaml.template, which works for any service
    # 2. app.yaml.template, which works only for the app service
    # 3. nginx.yaml.template, which works only for the nginx service as a load balancer

    # we want to iterate over the services dict, and for each service, create a config file
    for service, conf in services.items():
        template = "service.yaml.template"
        docker_image = "baselayer-service"
        processes = 1
        if service == "app":
            template = "app.yaml.template"
            docker_image = "skyportal-service"
            processes = conf['processes']
        elif service == "nginx":
            template = "nginx.yaml.template"
            docker_image = "skyportal-nginx"
        elif "baselayer" not in conf['path']:
            docker_image = "skyportal-service"

        # read the template file
        with open(f'./kubernetes/config_templates/{template}') as f:
            template_file = f.read()
        # create a jinja2 template object
        template = jinja2.Template(template_file)
        # render the template
        rendered_template = template.render(
            service=service.replace('_', '-'),
            service_name=service,
            image=docker_image,
            host=conf['host'],
            port=conf['port'],
            processes=processes,
        )
        # if the service has no port, remove the Service section from the config file (everything after the ---)
        if conf['port'] == "":
            rendered_template = rendered_template.split('---')[0]
            # remove the ports key from the rendered template

        # write the rendered template to a file
        with open(f'./kubernetes/config/{service}.yaml', 'w') as f:
            f.write(rendered_template)

        if conf['port'] == "":
            # load the yaml
            config = yaml.full_load(rendered_template)
            # remove spec.template.spec.containers.ports
            config['spec']['template']['spec']['containers'][0].pop('ports')
            # write the yaml file
            with open(f'./kubernetes/config/{service}.yaml', 'w') as f:
                yaml.dump(config, f)

    # we also have a persistent-volume.yaml.template file, which we want to render
    # TODO: make the size of the persistent volume configurable
    # for now, we just copy it over to the kubernetes/config directory
    os.system(
        'cp ./kubernetes/config_templates/persistent-volume.yaml.template ./kubernetes/config/persistent-volume.yaml'
    )


def generate_k8_config():
    # we want to get the kubernetes.yaml config,
    # and patch the hosts and ports to add each of the services
    services = get_services()
    config = yaml.full_load(open('./kubernetes/kubernetes.yaml'))
    # we want to iterate over the services dict, and for each service, add a host and port
    if config.get('hosts') in [None, {}]:
        config['hosts'] = {}
    if config.get('ports') in [None, {}]:
        config['ports'] = {}

    for service, conf in services.items():
        if conf['port'] != "":
            print(conf['host'])
            config['ports'][service] = conf['port']
            config['hosts'][service] = conf['host']

    config['hosts']['app_internal'] = 'app-service'
    config['ports']['app_internal'] = 65000
    # write the yaml file
    with open('./kubernetes/kubernetes.yaml', 'w') as f:
        yaml.dump(config, f)


def build_docker_images(
    images=['baselayer-service', 'skyportal-service', 'skyportal-nginx']
):
    # we want to build the docker images from the ./kubernetes/docker_files directory
    generate_k8_config()
    # we have 2 docker images: service.Dockefile and nginx.Dockerfile
    # the service.Dockerfile can generate 2 images: baselayer-service and skyportal-service using stage builds

    # first generate the baselayer-service image
    if 'baselayer-service' in images:
        os.system(
            'docker build -t baselayer-service -f ./kubernetes/docker_files/service.Dockerfile --target baselayer .'
        )
    # then generate the skyportal-service image
    if 'skyportal-service' in images:
        os.system(
            'docker build -t skyportal-service -f ./kubernetes/docker_files/service.Dockerfile --target skyportal .'
        )
    # then generate the skyportal-nginx image
    if 'skyportal-nginx' in images:
        os.system(
            'docker build -t skyportal-nginx -f ./kubernetes/docker_files/nginx.Dockerfile .'
        )


def apply_k8_config():
    # first we delete all current deployments
    for service in os.listdir('./kubernetes/config'):
        if service == 'persistent-volume.yaml':
            continue
        os.system(f'kubectl delete -f ./kubernetes/config/{service}')

    # first we want to create a persistent volume if it doesn't exist
    os.system('kubectl apply -f ./kubernetes/config/persistent-volume.yaml')

    # we want to apply the kubernetes config files in the ./kubernetes/config directory
    for service in os.listdir('./kubernetes/config'):
        os.system(f'kubectl apply -f ./kubernetes/config/{service}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=False)
    parser.add_argument('--build', type=bool, required=False)
    parser.add_argument('--init', type=bool, required=False)
    parser.add_argument('--images', type=str, required=False, default='all')
    parser.add_argument('--apply', type=bool, required=False)

    args = parser.parse_args()

    if args.init:
        # we want to create a kubernetes/config directory, and populate it with the
        # config files for each service
        setup_k8_services()
        generate_k8_config()
    elif args.build:
        all_images = ['baselayer-service', 'skyportal-service', 'skyportal-nginx']
        # keep only the images that we want to build
        images = args.images.split(',')
        if 'all' in images:
            images = all_images
        else:
            images = [i for i in images if i in all_images]

        if len(images) == 0:
            print("No valid images specified")
            exit(1)
        # we want to build the docker images from the ./kubernetes/docker_files directory
        build_docker_images(images=images)
    elif args.apply:
        # we want to apply the kubernetes config files in the ./kubernetes/config directory
        apply_k8_config()
