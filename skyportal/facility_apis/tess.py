from astropy.time import Time, TimeDelta
from astropy.table import Table
import numpy as np
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, scoped_session
from tornado.ioloop import IOLoop

from . import FollowUpAPI
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log


env, cfg = load_env()

TESS_URL = cfg['app.tess_endpoint']
lightcurve_url = f"{TESS_URL}/light_curves/"

log = make_log('facility_apis/tess')


def commit_photometry(lc, request_id, instrument_id, user_id):
    """
    Commits TESS photometry to the database

    Parameters
    ----------
    lc : astropy.table.Table
        Light curve data
    request_id : int
        FollowupRequest SkyPortal ID
    instrument_id : int
        Instrument SkyPortal ID
    user_id : int
        User SkyPortal ID
    """

    from ..models import (
        DBSession,
        FollowupRequest,
        PhotometricSeries,
        User,
    )

    Session = scoped_session(sessionmaker())
    if Session.registry.has():
        session = Session()
    else:
        session = Session(bind=DBSession.session_factory.kw["bind"])

    try:
        request = session.query(FollowupRequest).get(request_id)
        user = session.query(User).get(user_id)

        lc['mjd'] = (
            Time(2457000, format='jd') + TimeDelta(lc['BTJD'], format='jd')
        ).mjd
        lc['ra'] = request.obj.ra
        lc['dec'] = request.obj.dec
        lc['limiting_mag'] = 18.4
        lc['zp'] = 20.5
        lc['filter'] = 'tess'
        lc['magsys'] = 'ab'

        df = lc.to_pandas()
        df.rename(
            columns={
                'e_mag': 'magerr',
                'cts_per_s': 'flux',
                'e_cts_per_s': 'fluxerr',
            },
            inplace=True,
        )

        magerr_none = df['magerr'] == None  # noqa: E711
        df.loc[magerr_none, 'mag'] = None

        isnan = np.isnan(df['magerr'])
        df.loc[isnan, 'mag'] = None
        df.loc[isnan, 'magerr'] = None

        is99 = np.isclose(df['magerr'], 99.9)
        df.loc[is99, 'mag'] = None
        df.loc[is99, 'magerr'] = None

        drop_columns = list(
            set(df.columns.values)
            - {
                'mjd',
                'ra',
                'dec',
                'mag',
                'magerr',
                'flux',
                'fluxerr',
                'zp',
                'limiting_mag',
                'filter',
                'magsys',
            }
        )
        df.drop(
            columns=drop_columns,
            inplace=True,
        )

        data_out = {
            'obj_id': request.obj.id,
            'series_name': 'tesstransients',
            'series_obj_id': request.obj.id,
            'exp_time': 2.0,
            'instrument_id': instrument_id,
            'group_ids': [g.id for g in user.accessible_groups],
        }

        from skyportal.handlers.api.photometric_series import (
            post_photometric_series,
            update_photometric_series,
        )

        if len(df.index) > 0:
            try:
                post_photometric_series(data_out, df, {}, request.requester, session)
                request.status = "Photometry committed to database"
            except Exception:
                ps = session.scalars(
                    sa.select(PhotometricSeries).where(
                        PhotometricSeries.series_obj_id == request.obj.id,
                        PhotometricSeries.obj_id == request.obj.id,
                    )
                ).first()
                if ps is not None:
                    update_photometric_series(
                        ps, data_out, df, {}, request.requester, session
                    )
                    request.status = "Photometry updated in database"
                else:
                    request.status = "No photometry to commit to database"
        else:
            request.status = "No photometry to commit to database"

        session.add(request)
        session.commit()

        flow = Flow()
        flow.push(
            '*',
            "skyportal/REFRESH_SOURCE",
            payload={"obj_key": request.obj.internal_key},
        )

    except Exception as e:
        session.rollback()
        log(f"Unable to commit photometry for {request_id}: {e}")
    finally:
        session.close()
        Session.remove()


class TESSAPI(FollowUpAPI):

    """An interface to TESS photometry."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request, session, **kwargs):

        """Get photometry from TESS API.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import (
            FacilityTransaction,
            Allocation,
            FollowupRequest,
            Instrument,
        )

        instrument = (
            Instrument.query_records_accessible_by(request.requester)
            .join(Allocation)
            .join(FollowupRequest)
            .filter(FollowupRequest.id == request.id)
            .first()
        )

        name = request.obj.tns_name
        if name is None:
            request.status = 'No TNS name'
        else:
            try:
                lc = Table.read(
                    f"{lightcurve_url}/lc_{name}_cleaned",
                    format='ascii',
                    header_start=1,
                )

                if 'BTJD' not in list(lc.columns):
                    request.status = f"TESS alert {name} could not be ingested: {lightcurve_url}/lc_{name}_cleaned"
                else:
                    IOLoop.current().run_in_executor(
                        None,
                        lambda: commit_photometry(
                            lc, request.id, instrument.id, request.requester.id
                        ),
                    )

            except FileNotFoundError:
                request.status = f"TESS alert {name} not found."
            except Exception:
                request.status = f"TESS alert {name} could not be ingested: {lightcurve_url}/lc_{name}_cleaned"

        transaction = FacilityTransaction(
            request=None,
            response=None,
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        session.add(transaction)

        if kwargs.get('refresh_source', False):
            flow = Flow()
            flow.push(
                '*',
                'skyportal/REFRESH_SOURCE',
                payload={'obj_key': request.obj.internal_key},
            )
        if kwargs.get('refresh_requests', False):
            flow = Flow()
            flow.push(
                request.last_modified_by_id,
                'skyportal/REFRESH_FOLLOWUP_REQUESTS',
            )

    @staticmethod
    def delete(request, session, **kwargs):

        """Delete a photometry request from TESS API.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        session.delete(request)

        if kwargs.get('refresh_source', False):
            flow = Flow()
            flow.push(
                '*',
                'skyportal/REFRESH_SOURCE',
                payload={'obj_key': obj_internal_key},
            )
        if kwargs.get('refresh_requests', False):
            flow = Flow()
            flow.push(
                last_modified_by_id,
                'skyportal/REFRESH_FOLLOWUP_REQUESTS',
            )

    form_json_schema = {}
    ui_json_schema = {}
