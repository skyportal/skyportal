import requests
import telnetlib
import time
import os
import datetime

import jinja2
import yaml

from baselayer.app.env import load_env
from baselayer.log import make_log

env, cfg = load_env()
log = make_log('status_monitor')


def probe():
    probes = {}

    def health(status, status_code=-1, extra=None):
        now = datetime.datetime.now().replace(microsecond=0).isoformat()
        now = now.replace('T', ' ')
        return {
            'time': now,
            'status': status,
            'status_code': status_code,  # 0 for success
            'extra': extra or '',
        }

    def success(*args, **kwargs):
        kwargs['status_code'] = 0
        return health(*args, **kwargs)

    def failure(*args, **kwargs):
        kwargs['status_code'] = -1
        return health(*args, **kwargs)

    for probe in cfg['monitor.probes']:
        name = probe['name']
        ptype = probe['type']

        log(f'Executing probe {name}')

        if ptype == 'http':
            try:
                req = requests.get(probe['url'])
            except requests.exceptions.ConnectionError:
                status = failure('Down', extra=f'Server down')
            else:
                http_status = req.status_code
                if http_status == 200:
                    status = success('Up')
                else:
                    status = failure('Down', extra=f'HTTP status {http_status}')

        if ptype == 'tcp':
            try:
                telnetlib.Telnet(probe['host'], port=probe['port'])
            except ConnectionRefusedError:
                status = failure('Down')
            else:
                status = success('Up')

        probes[name] = status

    return probes


def watch_status():
    delay = int(cfg['monitor.interval'])
    while True:
        news_file = os.path.join(os.path.dirname(__file__), 'news.yaml')
        news = yaml.load(open(news_file, 'r'), Loader=yaml.Loader)

        render_status_page({
            'news': news,
            'probes': probe()
        })
        time.sleep(delay)


def render_status_page(status):
    template_file = os.path.join(os.path.dirname(__file__), 'status.html.tmpl')
    template = jinja2.Template(open(template_file, 'r').read())
    rendered = template.render(status)

    with open(cfg['monitor.output'], 'w') as f:
        f.write(rendered)


if __name__ == '__main__':
    watch_status()
