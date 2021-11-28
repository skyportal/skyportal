import requests
from sqlalchemy.orm.exc import NoResultFound
from baselayer.app.access import auth_or_token
from ..base import BaseHandler

from ...models import (
    DBSession,
    LightcurveFit,
    Obj,
    Photometry,
)


class LightcurveFitHandler(BaseHandler):
    """
    ---
    description: |
        get the color and absolute magnitude of a source
        based on cross-matches to some catalog (default is GAIA).
    parameters:
    - in: path
        name: obj_id
        required: true
        schema:
          type: string
        description: ID of the object to retrieve photometry for
      - in: query
        name: model_name
        required: false
        schema:
          type: string
        description: |
          The name of the model type to be fit.
      - in: query
        name: gptype
        required: false
        schema:
          type: string
        description: |
          The type of interpolator to use for the model (if allowed).

    responses:
      200:
        content:
          application/json:
            schema:
              allOf:
                  - $ref: '#/components/schemas/Success'
                  - type: array
                    items:
                      type: object
                      properties:
                          origin:
                            type: string
                          color:
                            type: float
                          abs_mag:
                            type: float

      400:
        content:
        application/json:
          schema: Error

    """

    @auth_or_token
    def post(self, obj_id):
        obj = Obj.query.get(obj_id)
        if obj is None:
            return self.error('Invalid object id.')

        model_name = self.get_query_argument('model_name', 'Bu2019lm')
        gptype = self.get_query_argument('gptype', 'tensorflow')

        photometry = (
            Photometry.query_records_accessible_by(self.current_user)
            .filter(Photometry.obj_id == obj_id)
            .all()
        )
        phot_data = []
        for phot in photometry:
            if phot.mag is not None:
                phot_data.append(
                    [
                        phot.iso.format('YYYY-MM-DDTHH:mm:ss'),
                        phot.filter.replace("ztf", ""),
                        str(phot.mag),
                        str(phot.e_mag),
                    ]
                )

        username = "admin"
        password = "admin"
        email = "admin@gmail.com"

        data2 = {'username': username, 'password': password, 'email': email}

        r = requests.post("http://0.0.0.0:4001/api/auth", json=data2)

        credentials = r.json()['data']
        jwt_token = credentials["token"].encode()

        headers = {"Authorization": jwt_token}

        data = {
            'model_name': model_name,
            'cand_name': obj_id,
            'nmma_data': phot_data,
            'gptype': gptype,
        }

        try:
            lcfit = LightcurveFit.query.filter_by(
                model_name=model_name, object_id=obj_id
            ).one()
        except NoResultFound:
            r = requests.get("http://0.0.0.0:4001/api/fit", json=data, headers=headers)
            if not r.status_code == 200:
                r = requests.post(
                    "http://0.0.0.0:4001/api/fit", json=data, headers=headers
                )

                lcfit = LightcurveFit(object_id=obj_id, model_name=model_name)
                lcfit.status = lcfit.Status.WORKING
            else:
                lcfit = LightcurveFit(
                    object_id=obj_id,
                    model_name=model_name,
                    posterior_samples=r.json()["data"]["posterior_samples"],
                    bestfit_lightcurve=r.json()["data"]["bestfit_lightcurve"],
                    log_bayes_factor=r.json()["data"]["log_bayes_factor"],
                    status=LightcurveFit.Status.READY,
                )
            DBSession().add(lcfit)

        self.verify_and_commit()

        return self.success()

    @auth_or_token
    def get(self, obj_id):
        obj = Obj.query.get(obj_id)
        if obj is None:
            return self.error('Invalid object id.')

        data = self.get_json()
        model_name = data['model_name']

        lcfit = LightcurveFit.query.filter_by(
            model_name=model_name, object_id=obj_id
        ).one()

        return self.success(data=lcfit)
