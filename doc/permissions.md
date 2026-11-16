# Access controls

## Introduction

Astronomical data is often subject to complex data rights policies. As a data platform designed to ingest and serve data from multiple experiments and groups, each potentially with different access policies, SkyPortal must be able to enforce arbitrary logic governing who can see, interact with, and modify data.

SkyPortal enforces these policies in the API layer with baselayer's row-level security framework. The [baselayer documentation](https://cesium-ml.org/baselayer/access_control.html) explains how policies are written, bound to tables, and checked when a handler commits its session. This page covers what is specific to SkyPortal.

## Group and Stream Policies

SkyPortal defines policies based on group membership and stream access in `skyportal/models/group.py`, for example:

- `accessible_by_groups_members`: the user is a member of one of the record's groups.
- `accessible_by_streams_members`: the user has access to one of the record's streams.
- `accessible_by_group_admins`: the user is an admin of the record's group.

Policies can be custom (potentially complex and relational) database queries. This policy allows a group admin to add a user to a group only if that user has access to all of the group's streams:

```python
def group_create_logic(cls, user_or_token):
    return (
        sa.select(cls)
        .join(Group)
        .outerjoin(Stream, Group.streams)
        .outerjoin(
            StreamUser,
            sa.and_(
                StreamUser.user_id == cls.user_id,
                StreamUser.stream_id == Stream.id,
            ),
        )
        .where(Group.single_user_group.is_(False))
        .group_by(cls.id)
        .having(
            sa.or_(
                sa.func.bool_and(StreamUser.stream_id.isnot(None)),
                sa.func.bool_and(Stream.id.is_(None)),  # group has no streams
            )
        )
    )


GroupUser.create = (
    GroupUser.read
    & accessible_by_group_admins
    & CustomUserAccessControl(group_create_logic)
)
```

## PhotometricSeries Permissions

PhotometricSeries records follow a similar access control pattern to Photometry,
with additional support for group-based and stream-based access:

### Read Access

A user can **read** a PhotometricSeries if:

- The user is a member of one of the series' groups, OR
- The user is a member of one of the series' associated streams, OR
- The user is the owner of the series

### Update and Delete Access

A user can **update** or **delete** a PhotometricSeries if:

- The user is the owner of the series, OR
- The user is a system administrator, OR
- The user has the "Manage photometry" permission AND is a member of one of the series' groups

### Example Permission Checks

```python
# Retrieve all photometric series a user can read
readable_series = PhotometricSeries.get_records_accessible_by(user, mode="read")

# Check if a user can delete a specific series
deletable_series = session.scalars(
    PhotometricSeries.select(user, mode="delete").where(
        PhotometricSeries.id == series_id
    )
).first()

if deletable_series is None:
    return self.error("You do not have permission to delete this photometric series")
```

### Group and Stream Management

When uploading a PhotometricSeries:

- Specify `group_ids` to grant access to specific groups
- Specify `stream_ids` to associate the series with data streams
- Omitting `group_ids` means only the owner (via their single-user group) has access
- Use `group_ids: "all"` to share with all public groups

When updating a PhotometricSeries:

- Use a PATCH request to modify the `group_ids` and `stream_ids`
- This updates which groups and streams have access to the series

## Further Examples

### Policies:

- [Policy requiring that a user be in a comment's groups and able to read the comment's obj to read the comment](https://github.com/skyportal/skyportal/blob/c7ab07bd04d26e9f66938a05b4c70172a9364c82/skyportal/models.py#L1998)
- [Policy that allows a user to read a classification if the user can read the
  corresponding taxonomy and Obj](https://github.com/skyportal/skyportal/blob/c7ab07bd04d26e9f66938a05b4c70172a9364c82/skyportal/models.py#L2181)
- [Policy that allows tokens with the "Post from {facility} ACL" to update
  (but not read) requests made with that facility's API](https://github.com/skyportal/skyportal/pull/1793/files#diff-1a72b97ee4bbd072128056c510aed307d63349171ef041ffe2ed256cf1286547R2828)
- [Policy that allows group admins of a particular group to add a new user
  to the group if and only if the new user has access to all of the group's
  streams](https://github.com/skyportal/skyportal/pull/1793/files#diff-1a72b97ee4bbd072128056c510aed307d63349171ef041ffe2ed256cf1286547R3621)

### Examples of permissions being checked in an API handler:

- [Pattern for retrieving a specified record(s) if a user has access, otherwise
  erroring](https://github.com/skyportal/skyportal/blob/c7ab07bd04d26e9f66938a05b4c70172a9364c82/skyportal/handlers/api/comment.py#L51)
- [Pattern for checking permissions on all the records in a session and
  erroring if any violations are detected](https://github.com/skyportal/skyportal/blob/c7ab07bd04d26e9f66938a05b4c70172a9364c82/skyportal/handlers/api/allocation.py#L71)
- [Pattern for constructing a query for all records accessible to a user, then filtering that query](https://github.com/skyportal/skyportal/pull/1801/files#diff-0200612f282483e1172207de90a4db4788b3ca5ce55ab5105938d876e11eb2e0R1562)
