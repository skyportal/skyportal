from collections import defaultdict
from sqlalchemy import func, literal
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import functions
from sqlalchemy.sql.elements import ColumnClause
from sqlalchemy.sql.selectable import FromClause
from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import (
    DBSession,
    Obj,
    Candidate,
    Annotation,
    GroupAnnotation,
)


# Helper classes/functions below provide a workaround for PostgreSQL functions
# returning multiple columns, unsupported by SA
# See https://stackoverflow.com/questions/33865038/joining-with-set-returning-function-srf-and-access-columns-in-sqlalchemy
# for details
class FunctionColumn(ColumnClause):
    def __init__(self, function, name, type_=None):
        self.function = self.table = function
        self.name = self.key = name
        self.key = self.name
        self.type_ = type_
        self.is_literal = False

    @property
    def _from_objects(self):
        return []

    def _make_proxy(
        self, selectable, name=None, attach=True, name_is_truncatable=False, **kw
    ):
        print('_make_proxy')
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
            self._columns[name] = FunctionColumn(self, name)


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
                      description: |
                        An object in which each key is an annotation origin, and
                        the values are arrays of { key: value_type } objects
        """
        user_accessible_group_ids = [g.id for g in self.current_user.accessible_groups]
        user_accessible_filter_ids = [
            filtr.id
            for g in self.current_user.accessible_groups
            for filtr in g.filters
            if g.filters is not None
        ]

        annotations = jsonb_each_func(Annotation.data)
        q = (
            DBSession()
            .query(Annotation.origin)
            .add_columns(
                annotations.c.key, func.jsonb_typeof(annotations.c.value).label("type")
            )
            .outerjoin(annotations, literal(True))
            .join(Obj)
            .filter(
                Obj.id.in_(
                    DBSession()
                    .query(Candidate.obj_id)
                    .filter(Candidate.filter_id.in_(user_accessible_filter_ids))
                )
            )
            .join(GroupAnnotation)
            .filter(GroupAnnotation.group_id.in_(user_accessible_group_ids))
        )

        results = q.all()
        grouped = defaultdict(list)
        keys_seen = defaultdict(set)
        for annotation in results:
            if annotation.key not in keys_seen[annotation.origin]:
                grouped[annotation.origin].append({annotation.key: annotation.type})

            keys_seen[annotation.origin].add(annotation.key)

        return self.success(data=grouped)
