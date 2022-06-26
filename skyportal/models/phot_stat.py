__all__ = ['PhotStat']

import json
import numpy as np
import sqlalchemy as sa
from sqlalchemy import event

from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

# see this: https://amercader.net/blog/beware-of-json-fields-in-sqlalchemy/
from sqlalchemy.ext.mutable import MutableDict

from datetime import datetime

from baselayer.app.env import load_env
from baselayer.app.models import (
    DBSession,
    Base,
    public,
    restricted,
)

from skyportal.models.photometry import Photometry, PHOT_ZP

_, cfg = load_env()
PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]


class PhotStat(Base):
    """
    Keep track of some photometric statistics
    such as when was this object last detected.
    These correspond to all photometric points,
    regardless of permissioning.
    """

    def __init__(self, obj_id):
        self.obj_id = obj_id

    read = public

    write = update = delete = restricted

    last_update = sa.Column(
        sa.DateTime,
        nullable=True,
        index=True,
        doc='Time when this PhotStat entry underwent an update '
        'using the most recent photometry point or all points '
        'in a full update. ',
    )

    last_full_update = sa.Column(
        sa.DateTime,
        nullable=True,
        index=True,
        doc='Time when this PhotStat entry underwent a full update '
        '(looking at all photometry points of this object). ',
    )

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the PhotStat's Obj.",
    )
    obj = relationship('Obj', back_populates='photstats', doc="The PhotStat's Obj. ")

    num_obs_global = sa.Column(
        sa.Integer,
        nullable=False,
        default=0,
        index=True,
        doc='Number of observations taken of this object in all filters combined. ',
    )

    num_obs_per_filter = sa.Column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        index=True,
        doc='Number of observations taken of this object in each filter. '
        'Will be None if no photometry points have been added to this object. ',
    )

    num_det_global = sa.Column(
        sa.Integer,
        nullable=False,
        default=0,
        index=True,
        doc='Number of detections (measurements above threshold) '
        'of this object, in all filters combined. ',
    )

    num_det_per_filter = sa.Column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        index=True,
        doc='Number of detections (measurements above threshold) '
        'of this object, in each filter. '
        'Will be None if no points are detections. ',
    )

    first_detected_mjd = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='Modified Julian date when object was first detected. '
        'Will be None if no points are detections. ',
    )

    first_detected_mag = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='The apparent magnitude of the first detection. '
        'Will be None if no points are detections. ',
    )

    first_detected_filter = sa.Column(
        sa.String,
        nullable=True,
        index=True,
        doc='Which filter was used when making the first detection. '
        'Will be None if no points are detections. ',
    )

    last_detected_mjd = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='Modified Julian date when object was last detected. '
        'Will be None if no points are detections. ',
    )

    last_detected_mag = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='The apparent magnitude of the last detection. '
        'Will be None if no points are detections. ',
    )

    last_detected_filter = sa.Column(
        sa.String,
        nullable=True,
        index=True,
        doc='Which filter was used when making the last detection. '
        'Will be None if no points are detections. ',
    )

    recent_obs_mjd = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='Latest observation, either detection or limit. '
        'Will be None if no photometry has been added to this object. ',
    )

    predetection_mjds = sa.Column(
        sa.ARRAY(sa.Float),
        nullable=True,
        index=False,
        doc='List of MJDs of times when the Obj position was reported to have been observed without detection, '
        'including only the times before the very first detection. ',
    )

    last_non_detection_mjd = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='Latest non-detection that occurred before any detections. '
        'Will be None if none of the observations are non-detections '
        'or if the first photometry point is a detection. ',
    )

    time_to_non_detection = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='Amount of time (in days), between the first detection '
        'and the last upper limit before that detection. '
        'Will be None if no points are detections. ',
    )

    mean_mag_global = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='Average magnitude across all filters. '
        'Will be None if no points are detections. ',
    )

    mean_mag_per_filter = sa.Column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        index=True,
        doc='Average magnitude in various filters. '
        'The value is saved in a separate key for'
        'each filter in this JSONB. '
        'Will be None if no points are detections. ',
    )

    mean_color = sa.Column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        index=True,
        doc='Average magnitude difference in various filters combinations. '
        'The value is saved in a separate key for each filter combination, '
        'where the keys are named {filter1}-{filter2}. '
        'Will be None if there are no detections in multiple filters. ',
    )

    peak_mag_global = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='Brightest recorded apparent magnitude, in any filter. '
        'Will be None if no points are detections. ',
    )

    peak_mjd_global = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='Modified Julian date of the brightest recorded observation, '
        'in any filter. ',
    )

    peak_mag_per_filter = sa.Column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        index=True,
        doc='Brightest recorded apparent magnitude in each filter. '
        'Will be None if no points are detections. ',
    )

    peak_mjd_per_filter = sa.Column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        index=True,
        doc='Modified Julian date of the brightest recorded observation, '
        'in each filter. ',
    )

    faintest_mag_global = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='Faintest recorded apparent magnitude (not including non-detections), '
        'in any filter. Will be None if no points are detections. ',
    )

    faintest_mag_per_filter = sa.Column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        index=True,
        doc='Faintest recorded apparent magnitude (not including non-detections), '
        'in each filter. ',
    )

    deepest_limit_global = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='Deepest recorded limiting magnitude for non-detections, using any filter. '
        'Will be None if all photometry points are detections. ',
    )

    deepest_limit_per_filter = sa.Column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        index=True,
        doc='Deepest recorded limiting magnitude for non-detections in each filter. '
        'Will be None if all photometry points are detections. ',
    )

    rise_rate = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='Rate of change in magnitude (in magnitudes per day) '
        'measured from the first detection to the peak magnitude. '
        'Peak magnitude is chosen using the same filter as the first detection. '
        'Will be None if no points are detections or if '
        'the first detection is also the peak. ',
    )

    decay_rate = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='Rate of change in magnitude (in magnitudes per day) '
        'measured from the the peak magnitude to the last detection. '
        'Peak magnitude is chosen using the same filter as the last detection. '
        'Will be None if no points are detections or if '
        'the last detection is also the peak. ',
    )

    mag_rms_global = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc='Average variability of the magnitude measurements for all filters. ',
    )

    mag_rms_per_filter = sa.Column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        index=True,
        doc='Average variability of the magnitude, '
        'keyed to the name of each filter. '
        'Will be None if no points are detections. ',
    )

    def add_photometry_point(self, phot):
        """
        Add a new photometry point to the object's list of statistics.
        All stats are updated based on the new point,
        without needing to know any of the previous points
        (only need to know the existing stats).

        Parameters
        ----------
        phot: scalar dict or skypotyal.models.Photometry
            A new photometry point that was added to the object.

        """
        if isinstance(phot, Photometry):
            phot = phot.__dict__
        elif not isinstance(phot, dict):
            raise TypeError('phot must be a dict or Photometry object')

        filt = phot['filter']
        mjd = phot['mjd']
        mag = -2.5 * np.log10(phot['flux']) + PHOT_ZP
        snr = phot['flux'] / phot['fluxerr']
        det = not np.isnan(snr) and snr > PHOT_DETECTION_THRESHOLD

        if not det:  # get limiting magnitude for non-detection
            if (
                'original_user_data' in phot
                and phot['original_user_data'] is not None
                and 'limiting_mag' in phot['original_user_data']
            ):
                user_data = phot['original_user_data']
                if isinstance(user_data, str):
                    user_data = json.loads(user_data)
                lim = user_data['limiting_mag']
            else:
                fluxerr = phot['fluxerr']
                fivesigma = 5 * fluxerr
                lim = -2.5 * np.log10(fivesigma) + PHOT_ZP

        self.num_obs_global += 1
        if filt in self.num_obs_per_filter:
            self.num_obs_per_filter[filt] += 1
        else:
            self.num_obs_per_filter[filt] = 1

        if self.num_obs_global == 1:  # this is the first point
            self.recent_obs_mjd = mjd
            if det:
                self.num_det_global = 1
                self.first_detected_mjd = mjd
                self.first_detected_mag = mag
                self.first_detected_filter = filt
                self.last_detected_mjd = mjd
                self.last_detected_mag = mag
                self.last_detected_filter = filt
                self.time_to_non_detection = None
                self.mean_mag_global = mag
                self.mean_mag_per_filter = {filt: mag}
                self.mean_color = {}
                self.mag_rms_global = 0
                self.mag_rms_per_filter = {filt: 0}
                self.peak_mag_global = mag
                self.peak_mjd_global = mjd
                self.peak_mag_per_filter = {filt: mag}
                self.peak_mjd_per_filter = {filt: mjd}
                self.faintest_mag_global = mag
                self.faintest_mag_per_filter = {filt: mag}
                self.rise_rate = None
                self.decay_rate = None
                self.predetection_mjds = []
            else:
                self.deepest_limit_global = lim
                self.deepest_limit_per_filter = {filt: lim}
                self.predetection_mjds = [mjd]
                self.last_non_detection_mjd = mjd

        else:  # there are existing points
            self.recent_obs_mjd = max(mjd, self.recent_obs_mjd)

            if det:
                if self.first_detected_mjd is None or mjd < self.first_detected_mjd:
                    self.first_detected_mjd = mjd
                    self.first_detected_mag = mag
                    self.first_detected_filter = filt
                if self.last_detected_mjd is None or mjd > self.last_detected_mjd:
                    self.last_detected_mjd = mjd
                    self.last_detected_mag = mag
                    self.last_detected_filter = filt

                # update the RMS based on old RMS and mean:
                if self.mag_rms_global is not None:
                    self.mag_rms_global = self.update_scatter(
                        self.mag_rms_global,
                        self.mean_mag_global,
                        self.num_det_global,
                        mag,
                    )
                else:
                    self.mag_rms_global = 0

                if filt in self.mag_rms_per_filter:
                    self.mag_rms_per_filter[filt] = self.update_scatter(
                        self.mag_rms_per_filter[filt],
                        self.mean_mag_per_filter[filt],
                        self.num_det_per_filter[filt],
                        mag,
                    )
                else:
                    self.mag_rms_per_filter[filt] = 0

                # update the mean magnitudes:
                if self.mean_mag_global is not None:
                    self.mean_mag_global = self.update_average(
                        self.mean_mag_global, self.num_det_global, mag
                    )
                else:
                    self.mean_mag_global = mag

                if filt in self.mean_mag_per_filter:
                    self.mean_mag_per_filter[filt] = self.update_average(
                        self.mean_mag_per_filter[filt],
                        self.num_det_per_filter[filt],
                        mag,
                    )
                else:
                    self.mean_mag_per_filter[filt] = mag

                # update colors as differences of mean magnitudes
                mean_mags = self.mean_mag_per_filter  # short hand
                for k in mean_mags.keys():
                    if k == filt:  # skip this filter
                        continue

                    # save both directions of each magnitude difference
                    self.mean_color[f'{k}-{filt}'] = mean_mags[k] - mean_mags[filt]
                    self.mean_color[f'{filt}-{k}'] = mean_mags[filt] - mean_mags[k]

                # find the brightest magnitude (lowest number)
                if self.peak_mag_global is None or self.peak_mag_global > mag:
                    self.peak_mag_global = mag
                    self.peak_mjd_global = mjd
                if (
                    filt not in self.peak_mag_per_filter
                    or self.peak_mag_per_filter[filt] > mag
                ):
                    self.peak_mag_per_filter[filt] = mag
                    self.peak_mjd_per_filter[filt] = mjd

                # find the faintest (detected) magnitude (highest number)
                self.faintest_mag_global = max(mag, self.faintest_mag_global or -np.inf)
                self.faintest_mag_per_filter[filt] = max(
                    mag, self.faintest_mag_per_filter.get(filt, -np.inf)
                )

                # check if new point removes some predetections
                if (
                    self.last_non_detection_mjd is not None
                    and mjd < self.last_non_detection_mjd
                ):
                    # keep only the predetections that happened before this detection
                    self.predetection_mjds = [
                        m for m in self.predetection_mjds if m < mjd
                    ]
                    if self.predetection_mjds:
                        self.last_non_detection_mjd = max(self.predetection_mjds)
                    else:
                        self.last_non_detection_mjd = None

                # update the rise and decay rates
                if (
                    self.first_detected_filter is not None
                    and self.first_detected_filter in self.peak_mag_per_filter
                ):
                    peak_mag = self.peak_mag_per_filter[self.first_detected_filter]
                    peak_mjd = self.peak_mjd_per_filter[self.first_detected_filter]
                    if peak_mjd > self.first_detected_mjd:
                        self.rise_rate = -(peak_mag - self.first_detected_mag) / (
                            peak_mjd - self.first_detected_mjd
                        )
                    else:
                        self.rise_rate = None

                if (
                    self.last_detected_filter is not None
                    and self.last_detected_filter in self.peak_mag_per_filter
                ):
                    peak_mag = self.peak_mag_per_filter[self.last_detected_filter]
                    peak_mjd = self.peak_mjd_per_filter[self.last_detected_filter]
                    if peak_mjd < self.last_detected_mjd:
                        self.decay_rate = -(peak_mag - self.last_detected_mag) / (
                            peak_mjd - self.last_detected_mjd
                        )
                    else:
                        self.decay_rate = None

                # update the number of detections
                self.num_det_global += 1
                if filt in self.num_det_per_filter:
                    self.num_det_per_filter[filt] += 1
                else:
                    self.num_det_per_filter[filt] = 1

            else:  # non-detection
                # the deepest limiting magnitude for this object:
                self.deepest_limit_global = max(
                    lim, self.deepest_limit_global or -np.inf
                )
                self.deepest_limit_per_filter[filt] = max(
                    lim, self.deepest_limit_per_filter.get(filt, -np.inf)
                )

                # this non detection happened before the first detection (if any)
                if self.first_detected_mjd is None or self.first_detected_mjd > mjd:
                    if self.predetection_mjds is None:
                        self.predetection_mjds = [mjd]
                    else:
                        self.predetection_mjds = self.predetection_mjds + [mjd]
                    self.last_non_detection_mjd = max(self.predetection_mjds)

            # find the time between first detection and last non-detection
            if (
                self.first_detected_mjd is not None
                and self.last_non_detection_mjd is not None
            ):
                self.time_to_non_detection = (
                    self.first_detected_mjd - self.last_non_detection_mjd
                )
            else:
                self.time_to_non_detection = None

        self.last_update = datetime.utcnow()

    def full_update(self, phot_list):
        """
        Update this object's photometric stats
        using the entire set of photometry points.
        This should only be called on objects that
        have not been kept up-to-date when inserting
        new photometry points.

        Parameters
        ----------
        phot_list: 1D array-like of skyportal.models.Photometry
            List of photometry points associated with this object.

        """
        filters = np.array([phot.filter for phot in phot_list])
        mjds = np.array([phot.mjd for phot in phot_list])
        mags = np.array([phot.mag for phot in phot_list])
        dets = np.array(
            [
                phot.flux
                and phot.fluxerr
                and phot.flux / phot.fluxerr > PHOT_DETECTION_THRESHOLD
                for phot in phot_list
            ]
        )
        lims = np.nan * np.ones(len(dets))

        for i, phot in enumerate(phot_list):
            if isinstance(phot, Photometry):
                phot = phot.__dict__
            if not dets[i]:  # get limiting magnitude for non-detection
                if (
                    phot['original_user_data'] is not None
                    and 'limiting_mag' in phot['original_user_data']
                ):
                    lims[i] = phot['original_user_data']['limiting_mag']
                else:
                    fluxerr = phot['fluxerr']
                    fivesigma = 5 * fluxerr
                    if fivesigma > 0:
                        lims[i] = -2.5 * np.log10(fivesigma) + PHOT_ZP
                    else:
                        lims[i] = None

        # reset all scalar properties
        self.num_obs_global = 0
        self.num_det_global = 0
        self.recent_obs_mjd = None
        self.first_detected_mjd = None
        self.first_detected_mag = None
        self.first_detected_filter = None
        self.last_detected_mjd = None
        self.last_detected_mag = None
        self.last_detected_filter = None
        self.mean_mag_global = None
        self.mag_rms_global = None
        self.peak_mag_global = None
        self.peak_mjd_global = None
        self.faintest_mag_global = None
        self.deepest_limit_global = None
        self.last_non_detection_mjd = None
        self.time_to_non_detection = None

        # reset all dictionaries
        self.num_obs_per_filter = {}
        self.num_det_per_filter = {}
        self.mean_mag_per_filter = {}
        self.mag_rms_per_filter = {}
        self.peak_mag_per_filter = {}
        self.peak_mjd_per_filter = {}
        self.faintest_mag_per_filter = {}
        self.deepest_limit_per_filter = {}
        self.mean_color = {}

        # total number of points
        self.num_obs_global = len(phot_list)

        # total number of points in each filter
        for filt in filters:
            self.num_obs_per_filter[filt] = len(filters[filters == filt])

        # if the list includes any photometry points at all!
        if self.num_obs_global:
            self.recent_obs_mjd = max(mjds)

        # if any of the points are detections
        if np.any(dets):
            # good means has detection
            good_mjds = mjds[dets]
            good_mags = mags[dets]
            good_filters = filters[dets]

            # number of detections
            self.num_det_global = len(good_mjds)

            # index of first detection (among detections)
            idx = np.argmin(good_mjds)
            self.first_detected_mjd = good_mjds[idx]
            self.first_detected_mag = good_mags[idx]
            self.first_detected_filter = good_filters[idx]

            # index of last detection (among detections)
            idx = np.argmax(good_mjds)
            self.last_detected_mjd = good_mjds[idx]
            self.last_detected_mag = good_mags[idx]
            self.last_detected_filter = good_filters[idx]

            # other statistics
            self.mean_mag_global = np.nanmean(good_mags)
            self.mag_rms_global = np.nanstd(good_mags)
            self.peak_mag_global = min(good_mags)
            self.peak_mjd_global = good_mjds[np.argmin(good_mags)]
            self.faintest_mag_global = max(good_mags)

            # stats for detections for each filter
            for filt in set(good_filters):
                filt_mjds = good_mjds[good_filters == filt]
                filt_mags = good_mags[good_filters == filt]

                if len(filt_mjds):
                    self.num_det_per_filter[filt] = len(filt_mjds)
                    self.mean_mag_per_filter[filt] = np.nanmean(filt_mags)
                    self.mag_rms_per_filter[filt] = np.nanstd(filt_mags)
                    self.peak_mag_per_filter[filt] = min(filt_mags)
                    self.peak_mjd_per_filter[filt] = filt_mjds[np.argmin(filt_mags)]
                    self.faintest_mag_per_filter[filt] = max(filt_mags)

            # find all the color terms
            mean_mags = self.mean_mag_per_filter
            for f1 in set(good_filters):
                for f2 in set(good_filters):
                    if f1 != f2:
                        self.mean_color[f'{f1}-{f2}'] = mean_mags[f1] - mean_mags[f2]

            # update the rise and decay rates
            if (
                self.first_detected_filter is not None
                and self.first_detected_filter in self.peak_mag_per_filter
            ):
                peak_mag = self.peak_mag_per_filter[self.first_detected_filter]
                peak_mjd = self.peak_mjd_per_filter[self.first_detected_filter]
                if peak_mjd > self.first_detected_mjd:
                    self.rise_rate = -(peak_mag - self.first_detected_mag) / (
                        peak_mjd - self.first_detected_mjd
                    )
                else:
                    self.rise_rate = None

            if (
                self.last_detected_filter is not None
                and self.last_detected_filter in self.peak_mag_per_filter
            ):
                peak_mag = self.peak_mag_per_filter[self.last_detected_filter]
                peak_mjd = self.peak_mjd_per_filter[self.last_detected_filter]
                if peak_mjd < self.last_detected_mjd:
                    self.decay_rate = -(peak_mag - self.last_detected_mag) / (
                        peak_mjd - self.last_detected_mjd
                    )
                else:
                    self.decay_rate = None

        # if any are non-detections
        if np.any(dets == 0):
            lim_mags = lims[dets == 0]
            lim_mjds = mjds[dets == 0]
            lim_filters = filters[dets == 0]
            # find the deepest limit
            self.deepest_limit_global = max(lim_mags)
            if self.first_detected_mjd:
                self.predetection_mjds = list(
                    lim_mjds[lim_mjds < self.first_detected_mjd]
                )
            else:
                self.predetection_mjds = list(lim_mjds)

            if self.predetection_mjds:
                self.last_non_detection_mjd = max(self.predetection_mjds)
                if self.first_detected_mjd:
                    self.time_to_non_detection = (
                        self.first_detected_mjd - self.last_non_detection_mjd
                    )

            # stats for non-detections for each filter
            for filt in set(lim_filters):
                filt_mags = lim_mags[lim_filters == filt]
                if len(filt_mags):
                    self.deepest_limit_per_filter[filt] = max(filt_mags)

        self.last_update = datetime.utcnow()
        self.last_full_update = datetime.utcnow()

    @staticmethod
    def update_average(current, number, new):
        """
        Calculate the new average given the current average,
        the number of points used to calculate that average,
        and the new value to be added.
        """
        return (number * current + new) / (number + 1)

    @staticmethod
    def update_scatter(current_scatter, current_mean, number, new):
        """
        Calculate the new scatter (RMS) given the current scatter,
        the current average,
        the number of points used to calculate the average/scatter,
        and the new value to be added.
        """
        var = current_scatter**2

        new_var = (
            number / (number + 1) * (var + ((current_mean - new) ** 2) / (number + 1))
        )

        return np.sqrt(new_var)


@event.listens_for(Photometry, 'after_insert')
def insert_into_phot_stat(mapper, connection, target):

    # Create or update PhotStat object
    @event.listens_for(DBSession(), "before_flush", once=True)
    def receive_after_flush(session, context, instances):
        obj_id = target.obj_id
        phot_stat = session.scalars(
            sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
        ).first()
        if phot_stat is None:
            all_phot = session.scalars(
                sa.select(Photometry).where(Photometry.obj_id == obj_id)
            ).all()
            phot_stat = PhotStat(obj_id=obj_id)
            phot_stat.full_update(all_phot)
            session.add(phot_stat)

        else:
            phot_stat.add_photometry_point(target)
            session.add(phot_stat)
