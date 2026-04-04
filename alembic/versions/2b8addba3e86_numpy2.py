"""Numpy 2 migration

Revision ID: 2b8addba3e86
Revises: 9a7b5f6aa515
Create Date: 2026-04-04 19:37:59.107180

"""

import sqlalchemy as sa
import sqlalchemy_utils

from alembic import op

# revision identifiers, used by Alembic.
revision = "2b8addba3e86"
down_revision = "9a7b5f6aa515"
branch_labels = None
depends_on = None


def upgrade():
    # Recreate the bandpasses enum with galex::fuv and galex::nuv added
    # after 'tess'. Using full enum recreation to ensure migra compatibility.
    op.execute("ALTER TYPE bandpasses RENAME TO bandpasses__old_version_to_be_dropped")
    op.execute(
        "CREATE TYPE bandpasses AS ENUM ("
        "'bessellux', 'bessellb', 'bessellv', 'bessellr', 'besselli', "
        "'standard::u', 'standard::b', 'standard::v', 'standard::r', 'standard::i', "
        "'desu', 'desg', 'desr', 'desi', 'desz', 'desy', "
        "'sdssu', 'sdssg', 'sdssr', 'sdssi', 'sdssz', "
        "'f435w', 'f475w', 'f555w', 'f606w', 'f625w', 'f775w', 'f850lp', "
        "'nicf110w', 'nicf160w', "
        "'f098m', 'f105w', 'f110w', 'f125w', 'f127m', 'f139m', 'f140w', 'f153m', 'f160w', "
        "'f218w', 'f225w', 'f275w', 'f300x', 'f336w', 'f350lp', 'f390w', "
        "'f689m', 'f763m', 'f845m', 'f438w', "
        "'uvf475w', 'uvf555w', 'uvf606w', 'uvf625w', 'uvf775w', 'uvf814w', 'uvf850lp', "
        "'kepler', "
        "'cspb', 'csphs', 'csphd', 'cspjs', 'cspjd', "
        "'cspv3009', 'cspv3014', 'cspv9844', "
        "'cspys', 'cspyd', 'cspg', 'cspi', 'cspk', 'cspr', 'cspu', "
        "'f070w', 'f090w', 'f115w', 'f150w', 'f200w', 'f277w', 'f356w', 'f444w', "
        "'f140m', 'f162m', 'f182m', 'f210m', 'f250m', 'f300m', 'f335m', 'f360m', "
        "'f410m', 'f430m', 'f460m', 'f480m', "
        "'f560w', 'f770w', 'f1000w', 'f1130w', 'f1280w', 'f1500w', 'f1800w', 'f2100w', 'f2550w', "
        "'f1065c', 'f1140c', 'f1550c', 'f2300c', "
        "'lsstu', 'lsstg', 'lsstr', 'lssti', 'lsstz', 'lssty', "
        "'keplercam::us', 'keplercam::b', 'keplercam::v', 'keplercam::r', 'keplercam::i', "
        "'4shooter2::us', '4shooter2::b', '4shooter2::v', '4shooter2::r', '4shooter2::i', "
        "'f062', 'f087', 'f106', 'f129', 'f158', 'f184', 'f213', 'f146', "
        "'ztfg', 'ztfr', 'ztfi', "
        "'uvot::b', 'uvot::u', 'uvot::uvm2', 'uvot::uvw1', 'uvot::uvw2', 'uvot::v', 'uvot::white', "
        "'ps1::open', 'ps1::g', 'ps1::r', 'ps1::i', 'ps1::z', 'ps1::y', 'ps1::w', "
        "'atlasc', 'atlaso', "
        "'2massj', '2massh', '2massks', "
        "'gaia::gbp', 'gaia::g', 'gaia::grp', 'gaia::grvs', "
        "'tess', "
        "'galex::fuv', 'galex::nuv', "
        "'gotob', 'gotog', 'gotol', 'gotor', "
        "'skymapperu', 'skymapperg', 'skymapperr', 'skymapperi', 'skymapperz', "
        "'ztf::g', 'ztf::r', 'ztf::i', "
        "'megacam6::g', 'megacam6::r', 'megacam6::i', 'megacam6::i2', 'megacam6::z', "
        "'hsc::g', 'hsc::r', 'hsc::r2', 'hsc::i', 'hsc::i2', 'hsc::z', 'hsc::y', "
        "'swiftxrt', 'nicerxti'"
        ")"
    )
    op.execute(
        "ALTER TABLE photometric_series ALTER COLUMN filter TYPE bandpasses "
        "USING filter::text::bandpasses"
    )
    op.execute(
        "ALTER TABLE photometry ALTER COLUMN filter TYPE bandpasses "
        "USING filter::text::bandpasses"
    )
    op.execute(
        "ALTER TABLE instruments ALTER COLUMN filters TYPE bandpasses[] "
        "USING filters::text[]::bandpasses[]"
    )
    op.execute("DROP TYPE bandpasses__old_version_to_be_dropped")


def downgrade():
    pass
