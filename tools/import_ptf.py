"""Load scraped PTF data into skyportal database"""
from datetime import datetime
from glob import glob
import re
import os.path

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

from baselayer.app import load_config
from skyportal.models import (DBSession, init_db, Comment, Group, Photometry,
                              Source, Spectrum, User)
from skyportal.model_util import create_tables

pBase = automap_base()
pengine = create_engine("postgresql://skyportal:@localhost:5432/ptf")
pBase.prepare(pengine, reflect=True)
pBase.metadata.bind = pengine
pBase.metadata.create_all()

pSource = pBase.classes.sources
pPhotometry = pBase.classes.phot
pTelescope = pBase.classes.telescopes
pInstrument = pBase.classes.instruments

psession = Session(pengine)
init_db(**load_config()['database'])
create_tables()


def import_table(ptf_table, skyportal_table, columns=None, column_map={},
                 condition=None, dedupe=[], sql_statement=None):
    df = pd.read_sql(sql_statement if sql_statement is not None else ptf_table,
                     pengine, columns=columns)
    df = df[columns]

    df.rename(columns=column_map, inplace=True)
    if condition:
        df = df[df.apply(condition, axis=1)]
    if 'created_at' not in df:
        df['created_at'] = datetime.now()
    for col in dedupe:
        df.drop_duplicates(subset=[col], inplace=True)
    df.to_sql(skyportal_table, DBSession().bind, index=False, if_exists='append')
    try:
        max_id = DBSession().execute(f"SELECT MAX(id) FROM {skyportal_table};").first()[0]
        DBSession().execute(f"ALTER SEQUENCE {skyportal_table}_id_seq RESTART WITH {max_id + 1};")
    except Exception as e:
        print("Ignored exception:", e)


def normalize_spectrum(spectrum):
    """TODO copied from PTF marshal; would prefer not to do this at plot-time
    so for now I'm just copying the exact logic here.
    """
    inds = np.abs(spectrum.wavelengths - 6400) < 100
    if inds.any():
        spectrum.fluxes /= np.abs(np.median(spectrum.fluxes[inds]))
    else:
        spectrum.fluxes /= np.abs(np.median(spectrum.fluxes))


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('data_dir')
    args = parser.parse_args()


#    """
#    DELETE FROM phot WHERE sourceid NOT IN (SELECT id FROM sources);
#    ALTER TABLE phot ADD CONSTRAINT fk_phot_obj_id FOREIGN KEY (sourceid) REFERENCES sources(id) ON DELETE CASCADE;
#    """

    import_table('users', 'users', ['id', 'username'], dedupe=['username'])

    import_table('telescopes', 'telescopes', ['id', 'name', 'nickname', 'lat',
                                              'lon', 'elevation', 'diameter'])
    import_table('instruments', 'instruments', ['id', 'name', 'type', 'band', 'telid'],
                 {'telid': 'telescope_id'})
    import_table('sources', 'sources', ['name', 'ra', 'dec', 'redshift'],
                 {'name': 'id'})
    import_table('comments', 'comments', ['id', 'user_id', 'text',
                                          'date_added', 'obj_id'],
                 {'date_added': 'created_at'})
    import_table('phot', 'photometry', ['id', 'name', 'instrumentid',
                                        'obsdate', 'filter', 'mag', 'emag',
                                        'limmag'],
                 {'name': 'obj_id', 'instrumentid': 'instrument_id',
                  'obsdate': 'obs_time', 'emag': 'e_mag', 'limmag': 'lim_mag'},
                  sql_statement=psession.query(pPhotometry, pSource.name)
                                        .join(pSource)
                                        .statement)
    spectra_files = glob(f'{args.data_dir}/spectra/*.ascii')

    for f in spectra_files:
        obj_id, obs_date, nickname = os.path.basename(f.strip('.ascii')).split('_')[:3]
        telescope = psession.query(pTelescope).filter(pTelescope.nickname.like(f'{nickname}%')).first()
        instruments = psession.query(pInstrument).filter(pInstrument.telid == telescope.id).all()
        if len(instruments) > 1:
            instruments = [i for i in instruments if i.type != 'phot']
        try:
            spectrum = Spectrum.from_ascii(f, obj_id, instruments[0].id,
                                           datetime.strptime(obs_date, '%Y%m%d'))
            DBSession().add(spectrum)
            DBSession().commit()
        except ValueError:
            print(f"Skipped {f}")

    # TODO can't serve from outside static/
    cutout_files = glob(f'{args.data_dir}/cutouts/*')
    phot_info = DBSession().query(sa.sql.functions.min(Photometry.id),
                                  Photometry.obj_id).group_by(Photometry.obj_id).all()
    phot_map = {obj_id: phot_id for phot_id, obj_id in phot_info}
    for f in cutout_files:
        obj_id, thumb_type = re.split('[\/_\.]', f)[-3:-1]
        DBSession().add(Thumbnail(file_uri=f, type=thumb_type,
                                  photometry_id=phot_map[obj_id]))
        DBSession().commit()

    g = Group(name="Public group", public=True, sources=list(Source.query))
    DBSession().add(g)
    DBSession().commit()
