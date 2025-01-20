import datetime
import os
from glob import glob

import numpy as np
import yaml

from skyportal.models import Spectrum


def test_spectrum_read_directly_from_file(public_source, lris):
    for filename in glob(f"{os.path.dirname(__file__)}/../data/ZTF*.ascii.head"):
        observed_at = str(datetime.datetime.now())
        obj_id = str(public_source.id)
        instrument_id = lris.id
        spec = Spectrum.from_ascii(
            filename[:-5],
            observed_at=observed_at,
            obj_id=obj_id,
            instrument_id=instrument_id,
        )

        answer = yaml.safe_load(open(filename))

        # check the header serialization
        for key in answer:
            # special keys
            if key not in ["COMMENT", "END", "HISTORY"]:
                if isinstance(spec.altdata[key], dict):
                    value = spec.altdata[key]["value"]
                else:
                    value = spec.altdata[key]
                if isinstance(answer[key], str | int):
                    assert str(value) == str(answer[key])
                elif isinstance(answer[key], datetime.datetime):
                    if isinstance(value, str):
                        assert datetime.datetime.fromisoformat(value) == answer[key]
                    else:
                        assert value == answer[key]
                elif isinstance(answer[key], datetime.date):
                    if isinstance(value, str):
                        assert (
                            datetime.datetime.fromisoformat(value).date() == answer[key]
                        )
                    else:
                        assert value == answer[key]
                elif answer[key] is None:
                    assert value is None
                else:
                    np.testing.assert_allclose(value, answer[key])
