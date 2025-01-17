import subprocess
import time

import requests

from baselayer.app.env import load_env
from baselayer.log import make_log

env, cfg = load_env()
log = make_log("health")


SECONDS_BETWEEN_CHECKS = cfg["health_monitor.seconds_between_checks"]
ALLOWED_DOWNTIME_SECONDS = cfg["health_monitor.allowed_downtime_seconds"]
ALLOWED_TIMES_DOWN = cfg["health_monitor.allowed_times_down"]
REQUEST_TIMEOUT_SECONDS = cfg["health_monitor.request_timeout_seconds"]
STARTUP_GRACE_SECONDS = cfg["health_monitor.startup_grace_seconds"]


class DownStatus:
    def __init__(self, nr_times=0, timestamp=None):
        self.nr_times = nr_times
        self.timestamp = time.time() if timestamp is None else timestamp

    def increase(self):
        self.nr_times += 1
        return self


def migrated():
    try:
        r = requests.get(
            f"http://localhost:{cfg['ports.migration_manager']}", timeout=30
        )
        data = r.json()
        return data["migrated"]
    except Exception as e:
        print(f"Exception while retrieving migration status: {e}")
        return False


def backends_down():
    down = set()
    for i in range(cfg["server.processes"]):
        port = cfg["ports.app_internal"] + i
        try:
            r = requests.get(
                f"http://localhost:{port}/api/sysinfo", timeout=REQUEST_TIMEOUT_SECONDS
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
        "python",
        "-m",
        "supervisor.supervisorctl",
        "-c",
        "baselayer/conf/supervisor/supervisor.conf",
    ]
    cmd = ["restart", f"app:app_{app_nr:02}"]
    try:
        subprocess.run(supervisorctl + cmd, check=True)
    except subprocess.CalledProcessError as e:
        log(f"Failure calling supervisorctl; could not restart app {app_nr}")
        log(f"Exception: {e}")


if __name__ == "__main__":
    log(
        f"Monitoring system health [{SECONDS_BETWEEN_CHECKS}s interval, max downtime {ALLOWED_DOWNTIME_SECONDS}s, max times down {ALLOWED_TIMES_DOWN}]"
    )

    all_backends = set(range(cfg["server.processes"]))
    backends_seen = set()
    downtimes = {}

    while not migrated():
        log("Database not migrated; waiting")
        time.sleep(30)

    while True:
        time.sleep(SECONDS_BETWEEN_CHECKS)

        down = backends_down()

        # Update list of backends that have been seen healthy at least once.
        # We don't start a counter against a backend until it's been seen.
        up = all_backends - down
        newly_seen = up - backends_seen
        if newly_seen:
            log(f"New healthy app(s) {newly_seen}")

        recovered = set(downtimes) & up
        if recovered:
            log(f"App(s) recovered: {recovered}")

        backends_seen = backends_seen | newly_seen

        downtimes = {
            k: downtimes.get(k, DownStatus()).increase() for k in (down & backends_seen)
        }

        for app in list(downtimes):
            down_status = downtimes[app]
            downtime = time.time() - down_status.timestamp
            times_down = down_status.nr_times
            if downtime > ALLOWED_DOWNTIME_SECONDS:
                message = f"App {app} unresponsive {times_down} times, total of {downtime:.1f}s"
                if times_down >= ALLOWED_TIMES_DOWN:
                    log(f"{message}: restarting")
                    # Give app a few second head start to fire up
                    downtimes[app] = DownStatus(
                        nr_times=0, timestamp=time.time() + STARTUP_GRACE_SECONDS
                    )
                    restart_app(app)
                else:
                    log(message)
