from baselayer.app.access import permissions
from baselayer.app.env import load_env
from baselayer.log import make_log
import arrow
from astropy.time import Time

import base64
import io
import matplotlib
import matplotlib.pyplot as plt
import pysedm
import tempfile

from ..base import BaseHandler
from ...models import Instrument

_, cfg = load_env()

log = make_log('spectrum_analysis')


class SpectrumAnalysisHandler(BaseHandler):
    @permissions(["Upload data"])
    async def post(self, obj_id):
        """
        ---
        description: Submit a new spectrum for analysis
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        data = self.get_json()
        instrument_id = data.get('instrument_id')
        if instrument_id is None:
            return self.error(message=f'Missing instrument {instrument_id}')
        instrument = Instrument.get_if_accessible_by(
            instrument_id, self.current_user, raise_if_none=True, mode="read"
        )

        centroid_x = data.get("centroid_x", None)
        centroid_y = data.get("centroid_y", None)
        spaxel_buffer = data.get("spaxel_buffer", None)

        print(centroid_x, centroid_y, spaxel_buffer)

        if instrument is None:
            return self.error(message=f'Found no instrument with id {instrument_id}')

        file_data = data.get("image_data")
        if file_data is None:
            return self.error(message='Missing image data')

        fluxcal_data = data.get("fluxcal_data", None)

        obstime = data.get("obstime")
        obstime = Time(arrow.get(obstime.strip()).datetime)

        file_data = file_data.split('base64,')
        file_name = file_data[0].split('name=')[1].split(';')[0]
        # if image name contains (.fz) then it is a compressed file
        if file_name.endswith('.fz'):
            suffix = '.fits.fz'
        else:
            suffix = '.fits'
        prefix = file_name.split(".")[0]

        with tempfile.NamedTemporaryFile(
            prefix=prefix, suffix=suffix, mode="wb", delete=True
        ) as f:
            file_data = base64.b64decode(file_data[-1])
            f.write(file_data)
            f.flush()

            cube = pysedm.get_sedmcube(f.name)

            centroid_data = {}
            if (centroid_x is not None) and (centroid_y is not None):
                centroid_data['centroid'] = (centroid_x, centroid_y)
            else:
                centroid_data['centroid'] = 'max'

            if spaxel_buffer is not None:
                centroid_data['spaxelbuffer'] = spaxel_buffer
            cube.extract_pointsource(**centroid_data)

            if fluxcal_data is not None:
                file_data = fluxcal_data.split('base64,')
                file_name = file_data[0].split('name=')[1].split(';')[0]
                # if image name contains (.fz) then it is a compressed file
                if file_name.endswith('.fz'):
                    suffix = '.fits.fz'
                else:
                    suffix = '.fits'
                prefix = file_name.split(".")[0]

                with tempfile.NamedTemporaryFile(
                    prefix=prefix, suffix=suffix, mode="wb", delete=True
                ) as g:
                    file_data = base64.b64decode(file_data[-1])
                    g.write(file_data)
                    g.flush()

                    spectrum = cube.extractstar.get_fluxcalibrated_spectrum(
                        fluxcalfile=g.name
                    )
            else:
                spectrum = cube.extractstar.get_fluxcalibrated_spectrum(nofluxcal=True)

            print(spectrum)

            matplotlib.use("Agg")
            figsize = (10, 8)
            output_format = 'pdf'
            filename = 'reduction.pdf'

            fig = plt.figure(figsize=figsize, constrained_layout=False)
            cube.extractstar.show_mla(savefile=filename)
            plt.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format=output_format)
            plt.close(fig)
            buf.seek(0)

            await self.send_file(buf, filename, output_type=output_format)
