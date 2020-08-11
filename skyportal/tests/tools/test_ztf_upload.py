import pytest
import uuid
from skyportal.model_util import create_token

# failing test on import for some systems
# deprecated 'independent_celestial_slices'
# from tools import ztf_upload_avro

fname = "skyportal/tests/data/541234765015015012.avro"

# this is a stub. Fill it in.
def test_ztf_upload(public_group, user, capsys):

    with capsys.disabled():
        print(user)

    #a = ztf_upload_avro.ZTFAvro(fname, z, clobber=True)

    assert True
