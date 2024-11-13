import ast

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ...base import BaseHandler
from ....utils.offset import get_formatted_standards_list

_, cfg = load_env()


class StandardsHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Get standard stars with specified formatting
        parameters:
        - in: query
          name: facility
          nullable: true
          required: false
          schema:
            type: string
            enum: [Keck, Shane, P200, P200-NGPS]
          description: Which facility to generate the starlist for
        - in: query
          name: standard_type
          required: false
          schema:
            type: string
          description: |
            Origin of the standard stars, defined in config.yaml
        - in: query
          name: dec_filter_range
          nullable: True
          required: false
          schema:
            type: list
          description: |
            lowest and highest dec to return, e.g. "(-10,30)"
        - in: query
          name: ra_filter_range
          required: false
          nullable: True
          schema:
            type: list
          description: |
            lowest and highest ra to return (or wrapped range)
            e.g. "(125,320)" or "(300,10)"
        - in: query
          name: show_first_line
          required: false
          schema:
            type: boolean
          description: |
            In the returned list, include the first formatting line
            if it is otherwise demanded by the format.
        responses:
          200:
            content:
              application/json:
                schema:
                  - $ref: '#/components/schemas/Success'
                  - type: object
                    properties:
                      data:
                        type: object
                        properties:
                          success:
                            type: boolean
                            description: did we get back a starlist as we expect?
                          starlist_info:
                            type: array
                            description: |
                              list of source and offset star information
                            items:
                              type: object
                              properties:
                                str:
                                  type: string
                                  description: single-line starlist format per object
          400:
            content:
              application/json:
                schema: Error
        """
        starlist_type = self.get_query_argument('facility', 'Keck')
        standard_type = self.get_query_argument('standard_type', 'ESO')
        dec_filter_range_str = self.get_query_argument('dec_filter_range', "[-90, 90]")
        ra_filter_range_str = self.get_query_argument('ra_filter_range', "[0, 360]")
        show_first_line = self.get_query_argument('show_first_line', False)

        if standard_type not in cfg["standard_stars"]:
            return self.error(
                f'Invalid `standard_type`. Should be in {list(cfg["standard_stars"].keys())}'
            )

        if starlist_type not in ["Keck", "Shane", "P200", "P200-NGPS"]:
            return self.error(
                'Invalid `starlist_type`. Should be in [Keck, Shane, P200, P200-NGPS]'
            )

        dec_filter_range = ast.literal_eval(dec_filter_range_str)
        if not (
            isinstance(dec_filter_range, (list, tuple)) and len(dec_filter_range) == 2
        ):
            return self.error('Invalid argument for `dec_filter_range`')
        if not (
            isinstance(dec_filter_range[0], (float, int))
            and isinstance(dec_filter_range[1], (float, int))
        ):
            return self.error('Invalid arguments in `dec_filter_range`')
        if not all(map(lambda x: x >= -90 and x <= 90, dec_filter_range)):
            return self.error('Elements out of range in `dec_filter_range`')

        ra_filter_range = ast.literal_eval(ra_filter_range_str)
        if not (
            isinstance(ra_filter_range, (list, tuple)) and len(ra_filter_range) == 2
        ):
            return self.error('Invalid argument for `ra_filter_range`')
        if not (
            isinstance(ra_filter_range[0], (float, int))
            and isinstance(ra_filter_range[1], (float, int))
        ):
            return self.error('Invalid arguments in `ra_filter_range`')

        if not all(map(lambda x: x >= 0 and x <= 360, ra_filter_range)):
            return self.error('Elements out of range in `ra_filter_range`')

        data = get_formatted_standards_list(
            starlist_type=starlist_type,
            standard_type=standard_type,
            dec_filter_range=tuple(dec_filter_range),
            ra_filter_range=tuple(ra_filter_range),
            show_first_line=show_first_line,
        )

        return self.success(data=data)
