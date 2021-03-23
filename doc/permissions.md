# Access controls

## Introduction
Astronomical data is often subject to complex data rights policies. As a data platform designed to ingest and serve data from multiple experiments and groups simultaneously, SkyPortal must be able to enforce complex policies governing who can see, interact with, and modify what. SkyPortal  enforces such policies using a custom row-level security (RLS) framework in the API layer.

RLS allows SkyPortal developers to define policies that restrict, with row- and user / token-level granularity, which rows of a table (e.g., photometry, spectra, groups, followup requests, data streams, etc.) a user can read, update, create, and delete. SkyPortal uses baselayer's ORM-based framework for RLS within API transactions. With baselayer's RLS framework, SkyPortal developers can

* Rest assured that access policies will be automatically and consistently enforced whenever a protected record is accessed in an API transaction
* Efficiently filter database queries by RLS accessibility to ensure that API endpoints only return records that users can access
* Take advantage of vectorization to efficiently apply policy checks and filters to bulk queries of records
* Define arbitrarily complex, relational, and scalable row-level CRUD access policies on any SkyPortal table
* Use predefined access patterns to restrict access to records by stream access, group membership, user ACLs, and more
* Implement different policies for different types of access on a single type of record

**Note:** Although SkyPortal uses PostgreSQL as the database backend, SkyPortal does not use PostgrteSQL's RLS implementation for row level security.

## RLS Architecture and Design

In SkyPortal, RLS policies are defined on SQLAlchemy mapped classes. Each class has a single policy for each of the create, delete, update, and read access modes. Records are read- and create-public by default, and update- and delete-restricted (i.e., only accessible to users with the "System admin" ACL) by default. Join table classes are also update- and delete-restricted by default, but they can (by default) be created or read by any user that can read both their left and right records. These defaults can be overridden on any mapped class.

When an API handler brings an instance of a mapped class into the session, either by a database query or by creating a new instance within the handler and adding it to the session, the SQLalchemy ORM tracks changes to the intsance's state. At the end of a transaction, if the handler calls either `verify_permissions` or `finalize_transaction`, the RLS permission checker will introspect the database session and get the sets of records that were read, updated, deleted, or created during the current transaction. It will then iterate through each of these collections and check that every record was accessed in an allowable way. If it encounters any permissions violations during this process, it causes the handler to rollback the transaction and return an HTTP status code of 400 with a message that identifies the specific row where an access policy was violated. If no access policies are violated, then the transaction will finish successfully.

This design ensures that every object pulled into the handler's session during an API transaction has its access policy checked in a consistent way, automatically preventing leaks of sensitive information to the end user. In most cases, the developer only needs to define a policy on a mapped class, then call `verify_permissions` at the end of an API handler call to ensure that the policy is applied.

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

Policies can be custom (potentially complex and relational) database queries. This policy only allows access to a record if :

```

```

## Binding Policies to Classes

To bind a policy to a class, set the `create`, `read`, `update`, or `delete` attribute of the class to the policy, depending on which access mode you want the policy to apply to:

```python
Spectrum.delete = accessible_by_owner
```

The above will ensure that only the owner of a spectrum (or anyone with the "System admin" ACL) can delete the spectrum.

### Convenience Methods

Instances of `Base` provide convenience methods to (a) check if an instance of a mapped class is accessible to a specified user, (b) retrieve all records of a mapped class accessible to a specified user, and (c) generate a query object that returns records in a table that are accessible to a given user:

```python

    def is_accessible_by(self, user_or_token, mode="read"):
        """Check if a User or Token has a specified type of access to this
        database record.

        Parameters
        ----------
        user_or_token: `baselayer.app.models.User` or `baselayer.app.models.Token`
            The User or Token to check.
        mode: string
            Type of access to check.
        Returns
        -------
        accessible: bool
            Whether the User or Token has the specified type of access to
            the record.
        """

```
