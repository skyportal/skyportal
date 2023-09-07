# Access controls

## Introduction
Astronomical data is often subject to complex data rights policies. As a data platform designed to ingest and serve data from multiple experiments and groups, each potentially with different access policies, SkyPortal must be able to enforce arbitrary logic governing who can see, interact with, and modify data. SkyPortal enforces such policies using a custom row-level security (RLS) framework in the API layer.

RLS allows SkyPortal developers to define policies that restrict, with row- and user-level granularity, which rows of a table (e.g., photometry, spectra, groups, followup requests, data streams, etc.) a user can read, update, create, and delete. SkyPortal uses baselayer's ORM-based framework for RLS within API transactions. With baselayer's RLS framework, SkyPortal developers can

* Be sure that access policies will be consistently enforced when protected records are accessed in an API transaction
* Efficiently filter database queries by RLS accessibility to ensure that API endpoints only return records that users can access
* Take advantage of vectorization to efficiently apply policy checks and filters to bulk record queries
* Define arbitrarily complex, relational, and scalable row-level CRUD access policies on any SkyPortal table
* Use predefined access patterns to restrict access to records by stream access, group membership, user ACLs, and more
* Implement different policies for different types of access on a single type of record

**Note:** Although SkyPortal uses PostgreSQL as the database backend, SkyPortal does not use PostgreSQL's RLS implementation for row-level security.

## RLS Architecture and Design

In SkyPortal, RLS policies are defined on SQLAlchemy mapped classes. Each class has a single policy for each of the create, delete, update, and read access modes. Records are read- and create-public by default, and update- and delete-restricted (i.e., only accessible to users with the "System admin" ACL) by default. Join table classes are also update- and delete-restricted by default, but they can (by default) be created or read by any user that can read both their left and right records. These defaults can be overridden on any mapped class.

When an API handler brings an instance of a mapped class into the session, either by a database query or by creating a new instance within the handler and adding it to the session, the SQLalchemy ORM tracks changes to the instance's state. At the end of a transaction, if the handler calls `verify_and_commit`, the RLS permission checker will introspect the database session and get the sets of records that were read, updated, deleted, or created during the current transaction. It will then iterate through each of these collections and check that every record was accessed in an allowable way. If it encounters any permissions violations during this process, it causes the handler to rollback the transaction and return an HTTP status code of 400 with a message that identifies the specific row where an access policy was violated. If no access policies are violated, then the transaction will finish successfully.

This design ensures that every object pulled into the handler's session during an API transaction has its access policy checked in a consistent way, automatically preventing leaks of sensitive information to the end user. In most cases, the developer only needs to define a policy on a mapped class, then call `verify_and_commit` at the end of an API handler call to ensure that the policy is applied.

## Create a New Policy

Policies are instances of  `UserAccessControl`  defined in baselayer/app/models.py. The only method of `UserAccessControl` that subclasses must provide is `query_accessible_rows`:

```python
class UserAccessControl:

    def query_accessible_rows(self, cls, user_or_token, columns=None):
        """Construct a Query object that, when executed, returns the rows of a
        specified table that are accessible to a specified user or token.

        Parameters
        ----------
        cls: `baselayer.app.models.DeclarativeMeta`
            The mapped class of the target table.
        user_or_token: `baselayer.app.models.User` or `baselayer.app.models.Token`
            The User or Token to check.
        columns: list of sqlalchemy.Column, optional, default None
            The columns to retrieve from the target table. If None, queries
            the mapped class directly and returns mapped instances.

        Returns
        -------
        query: sqlalchemy.Query
            Query for the accessible rows.
        """

        raise NotImplementedError
```

`query_accessible_rows` constructs (but does not execute) a query against the table that `cls` is mapped to. The query returns the rows of the `cls` table that `user_or_token` could access.

To construct a new policy, subclass `UserAccessControl` and override `query_accessible_rows`.

#### Restricted

Baselayer provides a [restricted](https://github.com/cesium-ml/baselayer/blob/main/app/models.py#L579) policy that grants record access only to users or tokens that have the `System admin` ACL. **Restricted records are not restricted to all users.**

### Examples

The following `public` policy will grant record access to any user:

```python

class Public(UserAccessControl):
    """A record accessible to anyone."""

    def query_accessible_rows(self, cls, user_or_token, columns=None):
        if columns is not None:
            return DBSession().query(*columns).select_from(cls)
        return DBSession().query(cls)


public = Public()
```

The following `accessible_to_owner` policy will grant record access to any user that matches the `User` pointed to by the `owner` relationship of `cls`, with access automatically granted to users with the `"System admin"` ACL:

```python
from baselayer.app.models import AccessibleIfUserMatches
accessible_to_owner = AccessibleIfUserMatches('owner')
```

Bitwise operations can be used to compose access policies. The  `accessible_to_owner_or_last_modified_by` policy below grants access to any user that matches the `User` pointed to by the `owner` relationship of `cls` or the `last_modified_by` relationship of `cls`:

```python
from baselayer.app.models import AccessibleIfUserMatches
accessible_to_owner_or_last_modified_by = AccessibleIfUserMatches('owner') | AccessibleIfUserMatches('last_modified_by')
```

Policies can be custom (potentially complex and relational) database queries. This policy allows adding a user to a group only if that user has access to all of the group's streams:

```
from baselayer.app.env import CustomserAccessControl
GroupUser.create = (
    CustomUserAccessControl(
        # Can only add a user to a group if they have all the requisite
        # streams required for entry to the group
        lambda cls, user_or_token: DBSession()
        .query(cls)
        .join(Group)
        .outerjoin(Stream, Group.streams)
        .outerjoin(
            StreamUser,
            sa.and_(
                StreamUser.user_id == cls.user_id,
                StreamUser.stream_id == Stream.id,
            ),
        )
        .group_by(cls.id)
        .having(
            sa.or_(
                sa.func.bool_and(StreamUser.stream_id.isnot(None)),
                sa.func.bool_and(Stream.id.is_(None)),  # group has no streams
            )
        )
    )
)
```

## Binding Policies to Classes

To bind a policy to a class, set the `create`, `read`, `update`, or `delete` attribute of the class to the policy, depending on which access mode you want the policy to apply to:

```python
Spectrum.delete = accessible_by_owner
```

The above will ensure that only the owner of a spectrum (or anyone with the "System admin" ACL) can delete the spectrum.

## Convenience Methods

Instances of `Base` provide convenience methods to (a) check if an instance of a mapped class is accessible to a specified user, (b) retrieve specific records of a mapped class (identified by a primary key), if they are accessible by a specified user, otherwise raise an AccessError (c) retrieve all records of a mapped class accessible to a specified user, and (d) generate a query object that returns records in a table that are accessible to a given user:

(a) Can the `User` `user` read the `Spectrum` `spectrum`?

```python
spectrum.is_accessible_by(user, mode="read")
```

Can the `User` `user` update the `Spectrum` `spectrum`?

```python
spectrum.is_accessible_by(user, mode='update')
```

(b) Retrieve spectra with IDs [1, 3] if they are updatable by the `User` `user`, raising an AccessError if either does not exist:

```python
Spectrum.get_if_accessible_by([1, 3], user, raise_if_none=True, mode="update")
```

(c) Retrieve all photometry that `User` `user` can read

```python
Photometry.get_records_accessible_by(user, mode="read")
```

(d) Construct a query object for all photometry that `User` `user` can delete
 with a signal-to-noise ratio of at least 10:

```python
deletable_phot_query = Photometry.query_records_accessible_by(user, mode="delete")
filtered_deletable_query = deletable_phot_query.filter(Photometry.snr > 10)
```


## Enforcing Permissions in Handlers

Calling `self.verify_and_commit()` within a SkyPortal API handler will trigger the RLS permission checker to introspect the current database session and verify that all of the records it currently is tracking are being accessed in an allowable way.  If it encounters any permissions violations during this process, it causes the handler to rollback the transaction and return an HTTP status code of 400 with a message that identifies the specific row where an access policy was violated. If no access policies are violated, then the current database transaction will be committed.

If `self.verify_and_commit()` is not called in an API handler, the handler will not automatically check for permissions violations. The best practice is to call `self.verify_and_commit()` at the end of a handler's transaction, immediately before `self.success` or `self.error`.

###  Further examples of policies:

 * [Policy requiring that a user be in a comment's groups and able to read the comment's obj to read the comment](https://github.com/skyportal/skyportal/blob/c7ab07bd04d26e9f66938a05b4c70172a9364c82/skyportal/models.py#L1998)
 * [Policy that allows a user to read a classification if the user can read the
  corresponding taxonomy and Obj](https://github.com/skyportal/skyportal/blob/c7ab07bd04d26e9f66938a05b4c70172a9364c82/skyportal/models.py#L2181)
 * [Policy that allows tokens with the "Post from {facility} ACL" to update
  (but not read) requests made with that facility's API](https://github.com/skyportal/skyportal/pull/1793/files#diff-1a72b97ee4bbd072128056c510aed307d63349171ef041ffe2ed256cf1286547R2828)
  * [Policy that allows group admins of a particular group to add a new user
   to the group if and only if the new user has access to all of the group's
    streams](https://github.com/skyportal/skyportal/pull/1793/files#diff-1a72b97ee4bbd072128056c510aed307d63349171ef041ffe2ed256cf1286547R3621)

###  Examples of permissions being checked in an API handler:

 * [Pattern for retrieving a specified record(s) if a user has access, otherwise
  erroring](https://github.com/skyportal/skyportal/blob/c7ab07bd04d26e9f66938a05b4c70172a9364c82/skyportal/handlers/api/comment.py#L51)
 * [Pattern for checking permissions on all the records in a session and
  erroring if any violations are detected](https://github.com/skyportal/skyportal/blob/c7ab07bd04d26e9f66938a05b4c70172a9364c82/skyportal/handlers/api/allocation.py#L71)
 * [Pattern for constructing a query for all records accessible to a user, then filtering that query](https://github.com/skyportal/skyportal/pull/1801/files#diff-0200612f282483e1172207de90a4db4788b3ca5ce55ab5105938d876e11eb2e0R1562)
