import ast

from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....utils.offset import get_formatted_standards_list


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
            enum: [Keck, Shane, P200]
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
            lowested and highest dec to return
        - in: query
          name: ra_filter_range
          required: false
          nullable: True
          schema:
            type: list
          description: |
            lowested and highest dec to return (or wrapped range)
        - in: query
          name: show_first_line
          required: false
          schema:
            type: boolean
          description: |
            return the first line of if demanded by the format
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

        dec_filter_range = ast.literal_eval(dec_filter_range_str)
        if not (
            isinstance(dec_filter_range, (list, tuple)) and len(dec_filter_range) == 2
        ):
            return self.error('Invalid argument for `dec_filter_range`')

        ra_filter_range = ast.literal_eval(ra_filter_range_str)
        if not (
            isinstance(ra_filter_range, (list, tuple)) and len(ra_filter_range) == 2
        ):
            return self.error('Invalid argument for `ra_filter_range`')

        data = get_formatted_standards_list(
            starlist_type=starlist_type,
            standard_type=standard_type,
            dec_filter_range=tuple(dec_filter_range),
            ra_filter_range=tuple(ra_filter_range),
            show_first_line=show_first_line,
        )

        return self.success(data=data)
