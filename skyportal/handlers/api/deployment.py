import importlib.metadata
import os
import platform
import re
import socket
from datetime import UTC, datetime
from functools import cache
from xmlrpc.client import ServerProxy

import psutil
import sqlalchemy as sa
from skyportal_py_models.system import DeploymentsResponse
from supervisor.xmlrpc import SupervisorTransport
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ... import __version__
from ...models import Deployment
from ...utils.gitlog import load_gitlog
from ..base import BaseHandler

_, cfg = load_env()

STARTED_AT = datetime.now(UTC).replace(tzinfo=None)

MAX_DEPLOYMENTS = 100
MAX_CHANGES = 50
PACKAGES = ["baselayer", "tornado", "sqlalchemy", "psycopg", "astropy", "numpy"]


def short_sha(commit):
    return (commit or {}).get("sha", "")[:7] or None


def with_changes(deployments, gitlog):
    """Attach to each deployment the commits it brought over the previous one."""
    position = {entry["sha"][:7]: index for index, entry in enumerate(gitlog)}
    result = []
    for index, deployment in enumerate(deployments):
        previous = deployments[index + 1] if index + 1 < len(deployments) else None
        start = position.get(short_sha(deployment.commit))
        end = position.get(short_sha(previous.commit)) if previous else None
        changes, n_changes, rollback = None, None, False
        if start is not None and end is not None:
            rollback = start > end
            changes = [] if rollback else gitlog[start:end]
            n_changes = len(changes)
            changes = changes[:MAX_CHANGES]
        result.append(
            {
                "id": deployment.id,
                "version": deployment.version,
                "commit": deployment.commit,
                "created_at": deployment.created_at,
                "changes": changes,
                "n_changes": n_changes,
                "rollback": rollback,
            }
        )
    return result


def service_pid(pid):
    """The pid of the service a zygote launcher stands in for, else `pid`."""
    try:
        with open(f"run/zygote/{pid}.pid") as f:
            return int(f.read())
    except (OSError, ValueError):
        return pid


def proportional_memory(process):
    try:
        return process.memory_full_info().pss
    except (psutil.AccessDenied, AttributeError):
        return process.memory_info().rss


def tree_memory(process, services):
    return proportional_memory(process) + sum(
        tree_memory(child, services)
        for child in process.children()
        if child.pid not in services
    )


def service_memory(pid, services):
    """Memory of a process and its children that are not services, in bytes."""
    try:
        return tree_memory(psutil.Process(pid), services)
    except (psutil.Error, ValueError):
        return None


def supervisor_processes():
    transport = SupervisorTransport("dummy", "dummy", "unix://run/supervisor.sock")
    proxy = ServerProxy("http://127.0.0.1", transport=transport)
    infos = proxy.supervisor.getAllProcessInfo()
    pids = {info["pid"]: service_pid(info["pid"]) for info in infos if info["pid"]}
    services = set(pids.values())
    return [
        {
            "name": info["name"],
            "group": info["group"],
            "state": info["statename"],
            "pid": info["pid"] or None,
            "memory": service_memory(pids[info["pid"]], services)
            if info["pid"]
            else None,
            "started_at": datetime.fromtimestamp(info["start"], UTC).replace(
                tzinfo=None
            )
            if info["start"]
            else None,
        }
        for info in infos
    ]


@cache
def service_programs():
    """Supervisor programs each service directory can define, by service name."""
    services = {}
    for path in cfg["services.paths"]:
        if not os.path.isdir(path):
            continue
        for name in sorted(os.listdir(path)):
            conf = os.path.join(path, name, "supervisor.conf")
            for candidate in (f"{conf}.template", conf):
                if os.path.isfile(candidate):
                    with open(candidate) as f:
                        services[name] = re.findall(
                            r"^\[program:([^\]]+)\]", f.read(), re.M
                        )
                    break
    return services


def service_status(name, processes, supervisor_available):
    disabled = cfg["services.disabled"] or []
    if (disabled == "*" or name in disabled) and name not in (
        cfg["services.enabled"] or []
    ):
        return "disabled"
    # its template only defines a program when the config calls for it
    if supervisor_available and not processes:
        return "not_configured"
    return "enabled"


def services_info(processes):
    by_program = {}
    for process in processes or []:
        by_program.setdefault(process["group"], []).append(process)
    services = []
    for name, programs in service_programs().items():
        service_processes = [p for g in programs for p in by_program.pop(g, [])]
        services.append(
            {
                "name": name,
                "status": service_status(
                    name, service_processes, processes is not None
                ),
                "processes": service_processes,
            }
        )
    for group, group_processes in by_program.items():
        services.append(
            {"name": group, "status": "enabled", "processes": group_processes}
        )
    return services


def host_resources():
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(os.getcwd())
    return {
        "cpu_count": psutil.cpu_count(),
        "load_average": list(os.getloadavg()),
        "memory_total": memory.total,
        "memory_available": memory.available,
        "disk_total": disk.total,
        "disk_free": disk.free,
    }


async def system_info(session):
    packages = {}
    for name in PACKAGES:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass

    loop = IOLoop.current()
    try:
        processes = await loop.run_in_executor(None, supervisor_processes)
    except Exception:
        processes = None

    info = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "packages": packages,
        "supervisor_available": processes is not None,
        "services": services_info(processes),
        "resources": await loop.run_in_executor(None, host_resources),
        "database_name": cfg["database.database"],
        "postgres_version": await session.scalar(sa.text("SHOW server_version")),
        "database_size": await session.scalar(
            sa.text("SELECT pg_size_pretty(pg_database_size(current_database()))")
        ),
        "migration": None,
    }
    try:
        info["migration"] = await session.scalar(
            sa.text("SELECT version_num FROM alembic_version")
        )
    except Exception:
        await session.rollback()
    return info


class DeploymentHandler(BaseHandler):
    @auth_or_token
    async def get(self) -> DeploymentsResponse:
        """
        ---
        summary: Get deployments and instance information
        description: |
          Running version, deployment history with the commits each deployment
          brought, and (for system admins) details on the host, database and
          services.
        tags:
          - system info
        """
        gitlog = load_gitlog()
        async with self.AsyncSession() as session:
            deployments = (
                await session.scalars(
                    sa.select(Deployment)
                    .order_by(Deployment.created_at.desc())
                    .limit(MAX_DEPLOYMENTS + 1)
                )
            ).all()
            deployments = with_changes(deployments, gitlog)[:MAX_DEPLOYMENTS]
            system = (
                await system_info(session)
                if self.current_user.is_system_admin
                else None
            )

        return self.success(
            data={
                "title": cfg["app.title"],
                "version": __version__,
                "commit": gitlog[0] if gitlog else None,
                "started_at": STARTED_AT,
                "deployed_at": deployments[0]["created_at"] if deployments else None,
                "deployments": deployments,
                "system": system,
            }
        )
