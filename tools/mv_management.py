import arrow

from skyportal.models import DBSession, MatView


def drop_old_matviews(days=7):
    threshold = arrow.now().shift(days=(-1 * days))
    # q = DBSession().execute(
    #     "SELECT oid::regclass::text FROM pg_class WHERE relkind = 'm'")
    mvs = list(MatView.query.filter(MatView.last_used <= threshold))
    mv_names = [mv.id for mv in mvs]
    if len(mv_names) == 0:
        return
    sql_str = 'DROP MATERIALIZED VIEW ' + ', '.join(mv_names)
    DBSession().execute(sql_str)
    for mv in mvs:
        DBSession().delete(mv)
    DBSession().commit()


def refresh_all_matviews():
    mvs = list(MatView.query)
    for mv in mvs:
        DBSession().execute(f'REFRESH MATERIALIZED VIEW {mv.id}')
        mv.last_refreshed = arrow.now()
        DBSession().commit()
