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

ALL_BACKENDS = set(range(cfg["server.processes"]))


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
            f"http://{cfg['hosts.migration_manager']}:{cfg['ports.migration_manager']}",
            timeout=30,
        )
        return r.json()["migrated"]
    except Exception:
        log("Migration manager not answering; assuming the database is not ready")
        return False


def backend_is_up(app_nr):
    try:
        r = requests.get(
            f"http://localhost:{cfg['ports.app_internal'] + app_nr}/api/sysinfo",
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except Exception:
        return False
    return r.status_code == 200


def backends_down():
    return {app_nr for app_nr in ALL_BACKENDS if not backend_is_up(app_nr)}


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
        log(f"Could not restart app {app_nr}, supervisorctl failed: {e}")


if __name__ == "__main__":
    log(
        f"Monitoring system health [{SECONDS_BETWEEN_CHECKS}s interval, max downtime {ALLOWED_DOWNTIME_SECONDS}s, max times down {ALLOWED_TIMES_DOWN}]"
    )

    backends_seen = set()
    downtimes = {}

    while not migrated():
        log("Database not migrated; waiting")
        time.sleep(30)

    while True:
        time.sleep(SECONDS_BETWEEN_CHECKS)

        down = backends_down()

        # Downtime is only counted against a backend once it has been seen healthy.
        up = ALL_BACKENDS - down
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
