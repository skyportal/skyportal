from collections import defaultdict
from sqlalchemy import literal
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import functions
from sqlalchemy.sql.elements import ColumnClause
from sqlalchemy.sql.selectable import FromClause
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import Annotation


# Helper classes/functions below provide a workaround for PostgreSQL functions
# returning multiple columns, unsupported by SA
# See https://stackoverflow.com/questions/33865038/joining-with-set-returning-function-srf-and-access-columns-in-sqlalchemy
# for details
class FunctionColumn(ColumnClause):
    def __init__(self, function, name, type_=None):
        self.function = self.table = function
        self.name = self.key = name
        self.type_ = type_
        self.is_literal = False

    @property
    def _from_objects(self):
        return []

    def _make_proxy(
        self, selectable, name=None, attach=True, name_is_truncatable=False, **kw
    ):
        if self.name == self.function.name:
            name = selectable.name
        else:
            name = self.name

        co = ColumnClause(name, self.type)
        co.key = self.name
        co._proxies = [self]
        if selectable._is_clone_of is not None:
            co._is_clone_of = selectable._is_clone_of.columns.get(co.key)
        co.table = selectable
        co.named_with_table = False
        if attach:
            selectable._columns[co.key] = co
        return co


@compiles(FunctionColumn)
def _compile_function_column(element, compiler, **kw):
    if kw.get('asfrom', False):
        return "(%s).%s" % (
            compiler.process(element.function, **kw),
            compiler.preparer.quote(element.name),
        )
    else:
        return element.name


class ColumnFunction(functions.FunctionElement):
    __visit_name__ = 'function'

    @property
    def columns(self):
        return FromClause.columns.fget(self)

    def _populate_column_collection(self):
        for name in self.column_names:
            # self._columns[name] = FunctionColumn(self, name)
            self.add(FunctionColumn(self, name), key=name)


class jsonb_each_func(ColumnFunction):
    name = 'jsonb_each'
    column_names = ['key', 'value']


@compiles(jsonb_each_func)
def _compile_jsonb_each_func(element, compiler, **kw):
    return compiler.visit_function(element, **kw)


class AnnotationsInfoHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Collects valid annotation origin/key pairs to filter on for scanning
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                            description: |
                                An object in which each key is an annotation origin, and
                                the values are arrays of { key: value_type } objects
        """
        # This query gets the origin/keys present in the accessible annotaions
        # for an Obj, as well as the data type for the values for each key.
        # This information is used to generate the front-end form for selecting
        # filters to apply on the auto-annotations column on the scanning page.
        # For example, if given that an annotation field is numeric we should
        # have min/max fields on the form.
        annotations = jsonb_each_func(
            Annotation.data
        )  # Get each key/value tuple in annotations

        # Objs are read-public, so no need to check that annotations belong to an unreadable obj
        # Instead, just check for annotation group membership
        q = (
            Annotation.query_records_accessible_by(
                self.current_user,
            )
            .outerjoin(annotations, literal(True))
            .distinct()
        )

        # Restructure query results so that records are grouped by origin in a
        # nice, nested dictionary
        results = q.all()
        grouped = defaultdict(list)
        keys_seen = defaultdict(set)
        for annotation in results:
            for key, value in annotation.data.items():
                if key not in keys_seen[annotation.origin]:
                    grouped[annotation.origin].append({key: type(value)})

            keys_seen[annotation.origin].add(key)

        return self.success(data=grouped)
