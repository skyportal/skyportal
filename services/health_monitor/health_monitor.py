from baselayer.app.env import load_env
from baselayer.log import make_log

import requests
import time
import subprocess


env, cfg = load_env()
log = make_log('health')


SECONDS_BETWEEN_CHECKS = cfg['health_monitor.seconds_between_checks']
ALLOWED_DOWNTIME_SECONDS = cfg['health_monitor.allowed_downtime_seconds']
REQUEST_TIMEOUT_SECONDS = cfg['health_monitor.request_timeout_seconds']


def migrated():
    try:
        r = requests.get(
            f'http://localhost:{cfg["ports.migration_manager"]}', timeout=10
        )
        data = r.json()
        return data["migrated"]
    except Exception as e:
        print(f"Exception while retrieving migration status: {e}")
        return False


def backends_down():
    down = set()
    for i in range(cfg['server.processes']):
        port = cfg['ports.app_internal'] + i
        try:
            r = requests.get(
                f'http://localhost:{port}/api/sysinfo', timeout=REQUEST_TIMEOUT_SECONDS
            )
        except:  # noqa: E722
            status_code = 0
        else:
            status_code = r.status_code

        if status_code != 200:
            down.add(i)

    return down


def restart_app(app_nr):
    supervisorctl = [
        'python',
        '-m',
        'supervisor.supervisorctl',
        '-c',
        'baselayer/conf/supervisor/supervisor.conf',
    ]
    cmd = ['restart', f'app:app_{app_nr:02}']
    try:
        subprocess.run(supervisorctl + cmd, check=True)
    except subprocess.CalledProcessError as e:
        log(f'Failure calling supervisorctl; could not restart app {app_nr}')
        log(f'Exception: {e}')


if __name__ == "__main__":
    log(
        f'Monitoring system health [{SECONDS_BETWEEN_CHECKS}s interval, max downtime {ALLOWED_DOWNTIME_SECONDS}s]'
    )

    all_backends = set(range(cfg['server.processes']))
    backends_seen = set()
    downtimes = {}

    while not migrated():
        log('Database not migrated; waiting')
        time.sleep(30)

    while True:
        time.sleep(SECONDS_BETWEEN_CHECKS)

        down = backends_down()

        # Update list of backends that have been seen healthy at least once.
        # We don't start a counter against a backend until it's been seen.
        newly_seen = (all_backends - down) - backends_seen
        backends_seen = backends_seen | newly_seen

        if newly_seen:
            log(f'New healthy app(s) {newly_seen}')

        downtimes = {k: downtimes.get(k, time.time()) for k in (down & backends_seen)}

        for app in list(downtimes):
            downtime = time.time() - downtimes[app]
            if downtime > ALLOWED_DOWNTIME_SECONDS:
                log(f'App {app} unresponsive: restarting')
                restart_app(app)
                # We attemped to restart the app. Now pretend as if it
                # is an entirely new backend that has never been seen healthy.
                backends_seen.remove(app)
                log(f'Waiting for app {app} to return, monitoring {backends_seen}')
                del downtimes[app]
