"""

make db_clear
make db_init
PYTHONPATH=$PYTHONPATH:"." python skyportal/initial_setup.py \
      --adminuser=joshbloom@berkeley.edu

"""
import datetime
import os
import io
import gzip
from pathlib import Path
import shutil
import numpy as np
import pandas as pd
import copy
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import concurrent
import itertools

import matplotlib
matplotlib.use('Agg')
import aplpy

from baselayer.app.env import load_env
from baselayer.app.model_util import status, create_tables, drop_tables
from social_tornado.models import TornadoStorage
from skyportal.models import (init_db, Base, DBSession, ACL, Comment,
                              Instrument, Group, GroupUser, Photometry, Role,
                              Source, Spectrum, Telescope, Thumbnail, User,
                              Token)

from avro.datafile import DataFileReader, DataFileWriter
from avro.io import DatumReader, DatumWriter
import fastavro
import astropy.units as u
from astropy.io import fits
from astropy.time import Time
from astropy.coordinates import SkyCoord
from astroquery.simbad import Simbad
from astroquery.vizier import Vizier

Simbad.TIMEOUT = 5
customSimbad = Simbad()
customSimbad.add_votable_fields('otype', 'sp', 'pm', "v*")
customGaia = Vizier(columns=["*", "+_r"], catalog="I/345/gaia2")

class ZTFAvro():

    def __init__(self, fname, ztfpack, only_pure=True, verbose=True,
                 clobber=True):

        self.fname = fname
        self.ztfpack = ztfpack
        self.verbose = verbose
        self.only_pure = only_pure
        self.clobber = clobber

        if not os.path.exists(self.fname):
            print(f"Cannot find file {fname}")
        else:
            if verbose: print(f"found {fname}")

        #self._parse_packets()
        self.save_packets()

    def _parse_packets(self):
        for packet in self._open_avro():
            do_process = True
            if self.only_pure and not self._is_alert_pure(packet):
                do_process = False

            print(do_process)
            print(packet)
            dflc = self._make_dataframe(packet)
            print(dflc.head())
            print(dflc.columns)
            print(self._is_transient(dflc))
            print(dflc[["jd", "magpsf", "sigmapsf", "fid", "diffmaglim"]])
            for i, cutout in enumerate(['Science','Template','Difference']):
                stamp = packet['cutout{}'.format(cutout)]['stampData']
                f = open(f"ttt{cutout}.fits.gz","wb")
                f.write(stamp)
                f.close()

    def save_packets(self):

        for packet in self._open_avro():
            print(packet["objectId"])
            do_process = True
            if self.only_pure and not self._is_alert_pure(packet):
                do_process = False

            if not do_process:
                print(f"{self.fname}: not pure. Skipping")
                continue

            s = Source.query.filter(Source.id == packet["objectId"]).first()
            if s:
                print("Found an existing source with id = " + packet["objectId"])
                source_is_varstar = s.varstar in [True]
                if not self.clobber and s.origin == f"{os.path.basename(self.fname)}":
                    print(f"already added this source with this avro packet {os.path.basename(self.fname)}")
                    continue

            # make a dataframe and save the source/phot
            dflc = self._make_dataframe(packet)

            source_info = {'id': packet["objectId"],
                           'ra': packet["candidate"]["ra"],
                           'dec': packet["candidate"]["dec"],
                           'ra_dis': packet["candidate"]["ra"],
                           'dec_dis': packet["candidate"]["dec"],
                           'dist_nearest_source': packet["candidate"].get("distnr"),
                           'mag_nearest_source': packet["candidate"].get("magnr"),
                           'e_mag_nearest_source': packet["candidate"].get("sigmagnr"),
                           'sgmag1': packet["candidate"].get("sgmag1"),
                           'srmag1': packet["candidate"].get("srmag1"),
                           'simag1': packet["candidate"].get("simag1"),
                           'objectidps1': packet["candidate"].get("objectidps1"),
                           'sgscore1': packet["candidate"].get("sgscore1"),
                           'distpsnr1': packet["candidate"].get("distpsnr1"),
                           'score': packet['candidate']['rb']
                           }

            if s is None:
                s = Source(**source_info,
                           origin=f"{os.path.basename(self.fname)}",
                           groups=[self.ztfpack.g])
                source_is_varstar = False
            else:
                print("Found an existing source with id = " + packet["objectId"])

            # let's see if we have already
            comments = Comment.query.filter(Comment.source_id == packet["objectId"]) \
                                    .filter(Comment.origin == f"{os.path.basename(self.fname)}")

            skip = False
            if self.clobber:
                if comments.count() > 0:
                    print("removing preexisting comments from this packet")
                    comments.delete()
                    DBSession().commit()
            else:
                if comments.count() > 0:
                    skip = True

            if not skip:
                s.comments = [Comment(text=comment, source_id=packet["objectId"],
                              user=self.ztfpack.group_admin_user,
                              origin=f"{os.path.basename(self.fname)}")
                              for comment in ["Added by ztf_upload_avro", \
                                              f"filename = {os.path.basename(self.fname)}"]]

            photdata = []
            varstarness = []
            for j, row in dflc.iterrows():
                rj = row.to_dict()
                if ((packet["candidate"].get("sgscore1", 1.0) or 1.0) > 0.5) and \
                   ((packet["candidate"].get("distpsnr1", 10) or 10) < 1.0) or \
                    (rj.get("isdiffpos", 'f') not in ["1", "t"] and \
                     not pd.isnull(rj.get('magpsf'))):
                    varstarness.append(True)

                else:
                    varstarness.append(False)

                phot = {"mag": rj.pop('magpsf'), "e_mag": rj.pop("sigmapsf"),
                        "lim_mag": rj.pop('diffmaglim'),
                        "filter": str(rj.pop('fid')),
                        "score": rj.pop("rb"), "candid": rj.pop("candid"),
                        "isdiffpos": rj.pop("isdiffpos") in ["1", "t"],
                        'dist_nearest_source': rj.pop("distnr"),
                        'mag_nearest_source': rj.pop("magnr"),
                        'e_mag_nearest_source': rj.pop("sigmagnr")
                        }
                t = Time(rj.pop("jd"), format="jd")
                phot.update({"observed_at": t.iso, "mjd": t.mjd,
                             "time_format": "iso",
                             "time_scale": "utc"})

                # calculate the variable star mag
                sign = 1.0 if phot["isdiffpos"] else -1.0
                mref = phot["mag_nearest_source"]
                mref_err = phot["e_mag_nearest_source"]
                mdiff = phot["mag"]
                mdiff_err = phot["e_mag"]

                # Three options here:
                #   diff is detected in positive (ref source got brighter)
                #   diff is detected in the negative (ref source got fainter)
                #   diff is undetected in the neg/pos (ref similar source)
                try:
                    if not pd.isnull(mdiff):
                        total_mag = -2.5*np.log10(10**(-0.4*mref) +
                                                  sign*10**(-0.4*mdiff))
                        tmp_total_mag_errs = (-2.5*np.log10(10**(-0.4*mref) +
                                              sign*10**(-0.4*(mdiff + mdiff_err))) \
                                              - total_mag,
                                              -2.5*np.log10(10**(-0.4*mref) +
                                              sign*10**(-0.4*(mdiff - mdiff_err))) \
                                              - total_mag)
                        # add errors in quadature -- geometric mean of diff err
                        # and ref err
                        total_mag_err = np.sqrt(-1.0*tmp_total_mag_errs[0] *
                                                tmp_total_mag_errs[1] +
                                                mref_err**2)
                    else:
                        # undetected source
                        mref = packet["candidate"].get("magnr")
                        mref_err = packet["candidate"].get("sigmagnr")
                        # 5 sigma
                        diff_err = (-2.5*np.log10(10**(-0.4*mref) +
                                    sign*10**(-0.4*phot["lim_mag"])) - mref)/5

                        total_mag = mref
                        total_mag_err = np.sqrt(mref_err**2 + diff_err**2)
                except:
                    print("Error in varstar calc")
                    print(mdiff, mref, sign, mdiff_err, packet["candidate"].get("magnr"), packet["candidate"].get("sigmagnr"))

                    total_mag = 99
                    total_mag_err = 0

                phot.update({"var_mag": total_mag, "var_e_mag": total_mag_err})

                # just keep all the remaining non-nan values for this epoch
                altdata = dict()
                for k in rj:
                    if not pd.isnull(rj[k]): altdata.update({k: rj[k]})

                phot.update({"altdata": altdata})
                photdata.append(copy.copy(phot))



            photometry = Photometry.query.filter(Photometry.source_id == packet["objectId"]) \
                                         .filter(Photometry.origin == f"{os.path.basename(self.fname)}")

            skip = False
            if self.clobber:
                if photometry.count() > 0:
                    print("removing preexisting photometry from this packet")
                    photometry.delete()
                    DBSession().commit()
            else:
                if photometry.count() > 0:
                    print("Existing photometry from this packet. Skipping addition of more.")
                    skip = True

            if not skip:
                s.photometry = [Photometry(instrument=self.ztfpack.i1,
                                source_id=packet["objectId"],
                                origin=f"{os.path.basename(self.fname)}", **row)
                                for j, row in enumerate(photdata)]
            s.spectra = []
            source_is_varstar = source_is_varstar or any(varstarness)
            s.varstar = source_is_varstar
            s.transient = self._is_transient(dflc)

            DBSession().add(s)
            try:
                DBSession().commit()
            except:
                pass

            for ttype, ztftype in [('new', 'Science'), ('ref', 'Template'), ('sub', 'Difference')]:
                fname = f'{packet["candid"]}_{ttype}.png'
                gzname = f'{packet["candid"]}_{ttype}.fits.gz'

                t = Thumbnail(type=ttype, photometry_id=s.photometry[0].id,
                              file_uri=f'static/thumbnails/{packet["objectId"]}/{fname}',
                              origin=f"{os.path.basename(self.fname)}",
                              public_url=f'/static/thumbnails/{packet["objectId"]}/{fname}')
                tgz = Thumbnail(type=ttype + "_gz", photometry_id=s.photometry[0].id,
                              file_uri=f'static/thumbnails/{packet["objectId"]}/{gzname}',
                              origin=f"{os.path.basename(self.fname)}",
                              public_url=f'/static/thumbnails/{packet["objectId"]}/{gzname}')
                DBSession().add(t)
                stamp = packet['cutout{}'.format(ztftype)]['stampData']

                if (not os.path.exists(self.ztfpack.basedir/f'static/thumbnails/{packet["objectId"]}/{fname}') or \
                    not os.path.exists(self.ztfpack.basedir/f'static/thumbnails/{packet["objectId"]}/{gzname}')) and \
                    not self.clobber:
                    with gzip.open(io.BytesIO(stamp), 'rb') as f:
                        gz = open(f"/tmp/{gzname}", "wb")
                        gz.write(f.read())
                        gz.close()
                        f.seek(0)
                        with fits.open(io.BytesIO(f.read())) as hdul:
                            hdul[0].data = np.flip(hdul[0].data, axis=0)
                            ffig = aplpy.FITSFigure(hdul[0])
                            ffig.show_grayscale(stretch='arcsinh', invert=True) #ztftype != 'Difference')
                            ffig.save(f"/tmp/{fname}")
                    if not os.path.exists(self.ztfpack.basedir/f'static/thumbnails/{packet["objectId"]}'):
                        os.makedirs(self.ztfpack.basedir/f'static/thumbnails/{packet["objectId"]}')
                    shutil.copy(f"/tmp/{fname}", self.ztfpack.basedir/f'static/thumbnails/{packet["objectId"]}/{fname}')
                    shutil.copy(f"/tmp/{gzname}", self.ztfpack.basedir/f'static/thumbnails/{packet["objectId"]}/{gzname}')

            try:
                s.add_linked_thumbnails()
            except:
                print("Not linking thumbnails...not on the 'net?")

            # grab the photometry for this source and update relevant quanities

            # ra, dec update
            dat = pd.read_sql(DBSession()
                              .query(Photometry)
                              .filter(Photometry.source_id == packet["objectId"])
                              .filter(Photometry.mag < 30)
                              .statement, DBSession().bind)
            if not s.varstar:
                infos = [(x["altdata"]["ra"], x["altdata"]["dec"],
                      x["mag"], x["e_mag"], x["score"], x["filter"]) for i, x in dat.iterrows()]
            else:
                infos = [(x["altdata"]["ra"], x["altdata"]["dec"],
                      x["var_mag"], x["var_e_mag"], x["score"], x["filter"]) for i, x in dat.iterrows()]

            ndet = len(dat[~pd.isnull(dat["mag"])])
            s.detect_photometry_count =ndet
            s.last_detected = np.max(dat[~pd.isnull(dat["mag"])]["observed_at"])

            calc_source_data = dict()
            new_ra = np.average([x[0] for x in infos], weights=[1./x[3] for x in infos])
            new_dec = np.average([x[1] for x in infos], weights=[1./x[3] for x in infos])
            ra_err = np.std([x[0] for x in infos])
            dec_err = np.std([x[1] for x in infos])

            calc_source_data.update({"min_score": np.nanmin([x[4] for x in infos])})
            calc_source_data.update({"max_score": np.nanmax([x[4] for x in infos])})

            filts = list(set([x[-1] for x in infos]))
            for f in filts:
                ii = [x for x in infos if x[-1] == f]
                rez = np.average([x[2] for x in ii], weights=[1/x[3] for x in ii])
                if pd.isnull(rez):
                    rez = None
                calc_source_data.update({f: {"max_delta":
                                             np.nanmax([x[2] for x in ii]) -
                                             np.nanmin([x[2] for x in ii]),
                                             "mag_avg": rez
                                             }
                                         }
                                        )

            s = Source.query.get(packet["objectId"])

            altdata = dict()
            for k in calc_source_data:
                if not pd.isnull(calc_source_data[k]): altdata.update({k: calc_source_data[k]})

            s.altdata = altdata
            s.ra = new_ra
            s.dec = new_dec
            s.ra_err = ra_err
            s.dec_err = dec_err

            c1 = SkyCoord(s.ra_dis * u.deg, s.dec_dis * u.deg, frame='fk5')
            c2 = SkyCoord(new_ra * u.deg, new_dec * u.deg, frame='fk5')
            sep = c1.separation(c2)
            s.offset = sep.arcsecond

            ## catalog search
            result_table = customSimbad.query_region(SkyCoord(f"{s.ra_dis}d {s.dec_dis}d", frame='icrs'), radius='0d0m3s')
            if result_table:
                try:
                    s.simbad_class = result_table["OTYPE"][0].decode("utf-8", "ignore")

                    altdata = dict()
                    rj = result_table.to_pandas().dropna(axis='columns').iloc[0].to_json()
                    s.simbad_info = rj
                except:
                    pass

            if s.simbad_class:
                comments = [Comment(text=comment, source_id=packet["objectId"],
                              user=self.ztfpack.group_admin_user, ctype="classification",
                              origin=f"{os.path.basename(self.fname)}")
                              for comment in [f"Simbad class = {s.simbad_class}"]]

            result_table = customGaia.query_region(SkyCoord(ra=s.ra_dis, dec=s.dec_dis,
                                       unit=(u.deg, u.deg),
                                       frame='icrs'),
                                       width="3s",
                                       catalog=["I/345/gaia2"])
            if result_table:
                try:
                    rj = result_table.pop().to_pandas().dropna(axis='columns').iloc[0].to_json()
                    s.gaia_info = rj
                except:
                    pass

            DBSession().commit()
            print("added")

    def _open_avro(self):
        with open(self.fname, 'rb') as f:
            freader = fastavro.reader(f)
            # in principle there can be multiple packets per file
            for packet in freader:
                yield packet

    def _make_dataframe(self, packet):
        dfc = pd.DataFrame(packet['candidate'], index=[0])
        df_prv = pd.DataFrame(packet['prv_candidates'])
        dflc = pd.concat([dfc, df_prv], ignore_index=True)
        # we'll attach some metadata--not this may not be preserved after all operations
        # https://stackoverflow.com/questions/14688306/adding-meta-information-metadata-to-pandas-dataframe
        dflc.objectId = packet['objectId']
        dflc.candid = packet['candid']
        return dflc

    def _is_transient(self, dflc):

        candidate = dflc.loc[0]

        is_positive_sub = candidate['isdiffpos'] == 't'

        if (candidate['distpsnr1'] is None) or (candidate['distpsnr1'] > 1.5):
            no_pointsource_counterpart = True
        else:
            if candidate['sgscore1'] < 0.5:
                no_pointsource_counterpart = True
            else:
                no_pointsource_counterpart = False

        where_detected = (dflc['isdiffpos'] == 't') # nondetections will be None
        if np.sum(where_detected) >= 2:
            detection_times = dflc.loc[where_detected,'jd'].values
            dt = np.diff(detection_times)
            not_moving = np.max(dt) >= (30*u.minute).to(u.day).value
        else:
            not_moving = False

        no_ssobject = (candidate['ssdistnr'] is None) or (candidate['ssdistnr'] < 0) or (candidate['ssdistnr'] > 5)
        return is_positive_sub and no_pointsource_counterpart and not_moving and no_ssobject

    def _is_alert_pure(self, packet):
        pure = True
        pure &= packet['candidate']['rb'] >= 0.65
        pure &= packet['candidate']['nbad'] == 0
        pure &= packet['candidate']['fwhm'] <= 5
        pure &= packet['candidate']['elong'] <= 12
        pure &= np.abs(packet['candidate']['magdiff']) <= 0.1
        return pure


class ZTFPack():

    def __init__(self, username, groupname="Public ZTF",
                 create_user=True, create_group=True,
                 create_instrument=True, create_telescope=True):

        """
        username
        create_user=True,
        create_group=True,
        create_instrument=True,
        create_telescope=True
        """

        self._connect()
        self.username = username

        self.g = Group.query.filter(Group.name == groupname).first()
        if not self.g:
            self.g = Group(name=groupname)

        super_admin_user = User.query.filter(User.username == self.username).first()
        if not super_admin_user:
            super_admin_user = User(username=self.username,
                                    role_ids=['Super admin'])
            DBSession().add(GroupUser(group=self.g, user=super_admin_user, admin=True))
            uu = super_admin_user
            DBSession().add(TornadoStorage.user.create_social_auth(uu, uu.username,
                            'google-oauth2'))
            DBSession().add(super_admin_user)

        group_admin_user = User.query.filter(User.username == 'groupadmin@cesium-ml.org').first()
        if not group_admin_user:
            group_admin_user = User(username='groupadmin@cesium-ml.org',
                                    role_ids=['Group admin'])

            DBSession().add(GroupUser(group=self.g, user=group_admin_user, admin=True))
            uu = group_admin_user
            DBSession().add(TornadoStorage.user.create_social_auth(uu, uu.username,
                            'google-oauth2'))
            DBSession().add(group_admin_user)

        full_user = User.query.filter(User.username == 'fulluser@cesium-ml.org').first()
        if not full_user:
            full_user = User(username='fulluser@cesium-ml.org',
                             role_ids=['Full user'], groups=[self.g])
            uu = full_user
            DBSession().add(TornadoStorage.user.create_social_auth(uu, uu.username,
                            'google-oauth2'))
            DBSession().add_all([full_user])

        DBSession().commit()

        self.t1 = Telescope.query.filter(Telescope.name == 'Palomar 48inch').first()
        if not self.t1:
            self.t1 = Telescope(name='Palomar 48inch', nickname='P48',
                                lat=33.3633675, lon=-116.8361345, elevation=1870,
                                diameter=1.2)
            if create_telescope:
                DBSession().add(self.t1)
        self.i1 = Instrument.query.filter(Instrument.name == 'ZTF Camera').first()
        if not self.i1:
            self.i1 = Instrument(telescope=self.t1, name='ZTF Camera', type='phot',
                                 band='optical')
            if create_instrument:
                DBSession().add(self.i1)

        self.super_admin_user = super_admin_user
        self.group_admin_user = group_admin_user

        DBSession().commit()

    def _connect(self):
        env, cfg = load_env()
        self.basedir = Path(os.path.dirname(__file__))/'..'
        (self.basedir/'static/thumbnails').mkdir(parents=True, exist_ok=True)

        with status(f"Connecting to database {cfg['database']['database']}"):
            init_db(**cfg['database'])


class LoadPTF:

    def __init__(self, avro_dir=None, nproc=mp.cpu_count(), maxfiles=10,
                 username="profjsb@gmail.com", groupname="Public ZTF", clobber=True):

        self.maxfiles = maxfiles
        self.avro_dir = Path(avro_dir)
        self.nproc = min(nproc, maxfiles)
        self.clobber = clobber

        self.ztfpacks = [ZTFPack(username) for _ in range(1)]

    def _worker(self, fname, zpack, clobber=True):
        a = ZTFAvro(fname, zpack, clobber=clobber)
        return fname

    def runp(self):

        self.i = 0
        with ProcessPoolExecutor(max_workers=self.nproc) as executor:
            avro_files = list(self.avro_dir.glob("*.avro"))
            if self.maxfiles is not None and not isinstance(self.maxfiles, str):
                avro_files = avro_files[:self.maxfiles]
                print(f"running on {len(avro_files)} files")


            rez = {os.path.basename(avro):
                   executor.submit(self._worker, avro, connection, clobber=self.clobber)
                   for avro, connection
                   in zip(avro_files, itertools.cycle(self.ztfpacks))}

            for future in concurrent.futures.as_completed(rez):
                print(rez[future].result())

    def run(self):

        self.i = 0

        avro_files = list(self.avro_dir.glob("*.avro"))
        print(f"Number of files: {len(avro_files)}")

        if self.maxfiles is not None and not isinstance(self.maxfiles, str):
            avro_files = avro_files[:self.maxfiles]
            print(f"running on {len(avro_files)} files")

        rez = []
        for avro, connection in zip(avro_files, itertools.cycle(self.ztfpacks)):
            rez.append(self._worker(avro, connection, clobber=self.clobber))

        for r in rez:
                print(r)


z = ZTFPack("profjsb@gmail.com")
#a = ZTFAvro("tools/ZTF/data/ztf_public_20180809/585156990315015007.avro", z, clobber=True)
##a = ZTFAvro("tools/ZTF/data/ztf_public_20180809/585153593515015006.avro", z, clobber=True)

l = LoadPTF(avro_dir="tools/ZTF/data/ztf_public_20180809", maxfiles=100000, clobber=True)
l.run()
