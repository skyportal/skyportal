import gcn

from baselayer.log import make_log
from baselayer.app.models import init_db
from baselayer.app.env import load_env

from skyportal.handlers.api.gcn import post_gcnevent
from skyportal.models import DBSession

env, cfg = load_env()

init_db(**cfg['database'])

notice_types = [
    getattr(gcn.notice_types, notice_type) for notice_type in cfg["gcn_notice_types"]
]


def handle(payload, root):
    notice_type = gcn.get_notice_type(root)
    if notice_type in notice_types:
        user_id = 1
        with DBSession() as session:
            post_gcnevent(payload, user_id, session)


if __name__ == "__main__":
    log = make_log("gcnserver")

    gcn.listen(handler=handle)
