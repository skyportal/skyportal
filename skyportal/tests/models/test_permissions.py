def test_user_create_public_group(  # noqa
    user, public_group,
):

    accessible = public_group.is_accessible_by(user, mode="create")
    assert accessible


def test_user_create_public_groupuser(
    user, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(user, mode="create")
    assert not accessible  # needs GroupAdmin


def test_user_create_public_stream(
    user, public_stream,
):

    accessible = public_stream.is_accessible_by(user, mode="create")
    assert not accessible  # needs system admin


def test_user_create_public_groupstream(
    user, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(user, mode="create")
    assert not accessible  # needs system admin


def test_user_create_public_streamuser(
    user, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(user, mode="create")
    assert not accessible  # needs system admin


def test_user_create_public_filter(
    user, public_filter,
):

    accessible = public_filter.is_accessible_by(user, mode="create")
    assert accessible


def test_user_create_public_candidate_object(
    user, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(user, mode="create")
    assert accessible


def test_user_create_public_source_object(
    user, public_source_object,
):

    accessible = public_source_object.is_accessible_by(user, mode="create")
    assert accessible


def test_user_create_keck1_telescope(
    user, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(user, mode="create")
    assert accessible


def test_user_create_sedm(
    user, sedm,
):

    accessible = sedm.is_accessible_by(user, mode="create")
    assert accessible


def test_user_create_public_group_sedm_allocation(
    user, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(user, mode="create")
    assert accessible


def test_user_read_public_group(
    user, public_group,
):

    accessible = public_group.is_accessible_by(user, mode="read")
    assert accessible


def test_user_read_public_groupuser(
    user, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(user, mode="read")
    assert accessible


def test_user_read_public_stream(
    user, public_stream,
):

    accessible = public_stream.is_accessible_by(user, mode="read")
    assert accessible


def test_user_read_public_groupstream(
    user, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(user, mode="read")
    assert accessible


def test_user_read_public_streamuser(
    user, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(user, mode="read")
    assert accessible


def test_user_read_public_filter(
    user, public_filter,
):

    accessible = public_filter.is_accessible_by(user, mode="read")
    assert accessible


def test_user_read_public_candidate_object(
    user, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(user, mode="read")
    assert accessible


def test_user_read_public_source_object(
    user, public_source_object,
):

    accessible = public_source_object.is_accessible_by(user, mode="read")
    assert accessible


def test_user_read_keck1_telescope(
    user, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(user, mode="read")
    assert accessible


def test_user_read_sedm(
    user, sedm,
):

    accessible = sedm.is_accessible_by(user, mode="read")
    assert accessible


def test_user_read_public_group_sedm_allocation(
    user, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(user, mode="read")
    assert accessible


def test_user_update_public_group(
    user, public_group,
):

    accessible = public_group.is_accessible_by(user, mode="update")
    assert not accessible  # needs groupadmin


def test_user_update_public_groupuser(
    user, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(user, mode="update")
    assert not accessible  # needs groupadmin


def test_user_update_public_stream(
    user, public_stream,
):

    accessible = public_stream.is_accessible_by(user, mode="update")
    assert not accessible  # needs systemadmin


def test_user_update_public_groupstream(
    user, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(user, mode="update")
    assert not accessible  # needs systemadmin


def test_user_update_public_streamuser(
    user, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(user, mode="update")
    assert not accessible  # needs systemadmin


def test_user_update_public_filter(
    user, public_filter,
):

    accessible = public_filter.is_accessible_by(user, mode="update")
    assert accessible


def test_user_update_public_candidate_object(
    user, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(user, mode="update")
    assert accessible


def test_user_update_public_source_object(
    user, public_source_object,
):

    accessible = public_source_object.is_accessible_by(user, mode="update")
    assert accessible


def test_user_update_keck1_telescope(
    user, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(user, mode="update")
    assert not accessible  # needs system admin


def test_user_update_sedm(
    user, sedm,
):

    accessible = sedm.is_accessible_by(user, mode="update")
    assert not accessible  # needs system admin


def test_user_update_public_group_sedm_allocation(
    user, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(user, mode="update")
    assert accessible


def test_user_delete_public_group(
    user, public_group,
):

    accessible = public_group.is_accessible_by(user, mode="delete")
    assert not accessible  # needs group admin


def test_user_delete_public_groupuser(
    user, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(user, mode="delete")
    assert not accessible  # needs group admin


def test_user_delete_public_stream(
    user, public_stream,
):

    accessible = public_stream.is_accessible_by(user, mode="delete")
    assert not accessible  # needs system admin


def test_user_delete_public_groupstream(
    user, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(user, mode="delete")
    assert not accessible  # needs system admin


def test_user_delete_public_streamuser(
    user, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(user, mode="delete")
    assert not accessible  # needs system admin


def test_user_delete_public_filter(
    user, public_filter,
):

    accessible = public_filter.is_accessible_by(user, mode="delete")
    assert accessible  # any group member can delete a group filter for now


def test_user_delete_public_candidate_object(
    user, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(user, mode="delete")
    assert accessible


def test_user_delete_public_source_object(
    user, public_source_object,
):

    accessible = public_source_object.is_accessible_by(user, mode="delete")
    assert accessible


def test_user_delete_keck1_telescope(
    user, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(user, mode="delete")
    assert not accessible  # needs sysadmin


def test_user_delete_sedm(
    user, sedm,
):

    accessible = sedm.is_accessible_by(user, mode="delete")
    assert not accessible  # needs sysadmin


def test_user_delete_public_group_sedm_allocation(
    user, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(user, mode="delete")
    assert accessible


def test_user_group2_create_public_group(
    user_group2, public_group,
):

    accessible = public_group.is_accessible_by(user_group2, mode="create")
    assert accessible


def test_user_group2_create_public_groupuser(
    user_group2, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(user_group2, mode="create")
    assert not accessible  # must be in the group and be a group admin


def test_user_group2_create_public_stream(
    user_group2, public_stream,
):

    accessible = public_stream.is_accessible_by(user_group2, mode="create")
    assert not accessible  # needs sys admin


def test_user_group2_create_public_groupstream(
    user_group2, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(user_group2, mode="create")
    assert not accessible  # needs sys admin


def test_user_group2_create_public_streamuser(
    user_group2, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(user_group2, mode="create")
    assert not accessible  # needs system admin


def test_user_group2_create_public_filter(
    user_group2, public_filter,
):

    accessible = public_filter.is_accessible_by(user_group2, mode="create")
    assert not accessible  # must be in the filter's group


def test_user_group2_create_public_candidate_object(
    user_group2, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(user_group2, mode="create")
    assert not accessible  # must be in the filter's group


def test_user_group2_create_public_source_object(
    user_group2, public_source_object,
):

    accessible = public_source_object.is_accessible_by(user_group2, mode="create")
    assert not accessible  # must be in the source's group


def test_user_group2_create_keck1_telescope(
    user_group2, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(user_group2, mode="create")
    assert accessible


def test_user_group2_create_sedm(
    user_group2, sedm,
):

    accessible = sedm.is_accessible_by(user_group2, mode="create")
    assert accessible


def test_user_group2_create_public_group_sedm_allocation(
    user_group2, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(
        user_group2, mode="create"
    )
    assert not accessible  # must be in the allocation's group


def test_user_group2_read_public_group(
    user_group2, public_group,
):

    accessible = public_group.is_accessible_by(user_group2, mode="read")
    assert accessible


def test_user_group2_read_public_groupuser(
    user_group2, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(user_group2, mode="read")
    assert accessible


def test_user_group2_read_public_stream(
    user_group2, public_stream,
):

    accessible = public_stream.is_accessible_by(user_group2, mode="read")
    assert accessible


def test_user_group2_read_public_groupstream(
    user_group2, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(user_group2, mode="read")
    assert accessible


def test_user_group2_read_public_streamuser(
    user_group2, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(user_group2, mode="read")
    assert accessible == public_streamuser.user.is_accessible_by(
        user_group2, mode="read"
    ) and public_streamuser.stream.is_accessible_by(user_group2, mode="read")


def test_user_group2_read_public_filter(
    user_group2, public_filter,
):

    accessible = public_filter.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be a member of the group


def test_user_group2_read_public_candidate_object(
    user_group2, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be a member of the filter's group


def test_user_group2_read_public_source_object(
    user_group2, public_source_object,
):

    accessible = public_source_object.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be a member of the source's group


def test_user_group2_read_keck1_telescope(
    user_group2, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(user_group2, mode="read")
    assert accessible


def test_user_group2_read_sedm(
    user_group2, sedm,
):

    accessible = sedm.is_accessible_by(user_group2, mode="read")
    assert accessible


def test_user_group2_read_public_group_sedm_allocation(
    user_group2, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be a member of the allocation's group


def test_user_group2_update_public_group(
    user_group2, public_group,
):

    accessible = public_group.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be an admin of the group


def test_user_group2_update_public_groupuser(
    user_group2, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be an admin of the group


def test_user_group2_update_public_stream(
    user_group2, public_stream,
):

    accessible = public_stream.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be a system admin


def test_user_group2_update_public_groupstream(
    user_group2, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be a system admin


def test_user_group2_update_public_streamuser(
    user_group2, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be a system admin


def test_user_group2_update_public_filter(
    user_group2, public_filter,
):

    accessible = public_filter.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be an admin of the filter's group


def test_user_group2_update_public_candidate_object(
    user_group2, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be a member of the candidate's filter's group


def test_user_group2_update_public_source_object(
    user_group2, public_source_object,
):

    accessible = public_source_object.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be a member of the source's group


def test_user_group2_update_keck1_telescope(
    user_group2, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be system admin


def test_user_group2_update_sedm(
    user_group2, sedm,
):

    accessible = sedm.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be system admin


def test_user_group2_update_public_group_sedm_allocation(
    user_group2, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(
        user_group2, mode="update"
    )
    assert not accessible  # must be a member of the group


def test_user_group2_delete_public_group(
    user_group2, public_group,
):

    accessible = public_group.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be a group admin


def test_user_group2_delete_public_groupuser(
    user_group2, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be a group admin of the target group


def test_user_group2_delete_public_stream(
    user_group2, public_stream,
):

    accessible = public_stream.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be a system admin


def test_user_group2_delete_public_groupstream(
    user_group2, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be a system admin


def test_user_group2_delete_public_streamuser(
    user_group2, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be a system admin


def test_user_group2_delete_public_filter(
    user_group2, public_filter,
):

    accessible = public_filter.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be a group member of target group


def test_user_group2_delete_public_candidate_object(
    user_group2, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be a member of target group


def test_user_group2_delete_public_source_object(
    user_group2, public_source_object,
):

    accessible = public_source_object.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be a member of target group


def test_user_group2_delete_keck1_telescope(
    user_group2, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be a system admin


def test_user_group2_delete_sedm(
    user_group2, sedm,
):

    accessible = sedm.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be a system admin


def test_user_group2_delete_public_group_sedm_allocation(
    user_group2, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(
        user_group2, mode="delete"
    )
    assert not accessible  # must be a member of target group


def test_super_admin_user_create_public_group(
    super_admin_user, public_group,
):

    accessible = public_group.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_create_public_groupuser(
    super_admin_user, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_create_public_stream(
    super_admin_user, public_stream,
):

    accessible = public_stream.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_create_public_groupstream(
    super_admin_user, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_create_public_streamuser(
    super_admin_user, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_create_public_filter(
    super_admin_user, public_filter,
):

    accessible = public_filter.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_create_public_candidate_object(
    super_admin_user, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible


def test_super_admin_user_create_public_source_object(
    super_admin_user, public_source_object,
):

    accessible = public_source_object.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_create_keck1_telescope(
    super_admin_user, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_create_sedm(
    super_admin_user, sedm,
):

    accessible = sedm.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_create_public_group_sedm_allocation(
    super_admin_user, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible


def test_super_admin_user_read_public_group(
    super_admin_user, public_group,
):

    accessible = public_group.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_read_public_groupuser(
    super_admin_user, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_read_public_stream(
    super_admin_user, public_stream,
):

    accessible = public_stream.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_read_public_groupstream(
    super_admin_user, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_read_public_streamuser(
    super_admin_user, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_read_public_filter(
    super_admin_user, public_filter,
):

    accessible = public_filter.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_read_public_candidate_object(
    super_admin_user, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_read_public_source_object(
    super_admin_user, public_source_object,
):

    accessible = public_source_object.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_read_keck1_telescope(
    super_admin_user, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_read_sedm(
    super_admin_user, sedm,
):

    accessible = sedm.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_read_public_group_sedm_allocation(
    super_admin_user, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(
        super_admin_user, mode="read"
    )
    assert accessible


def test_super_admin_user_update_public_group(
    super_admin_user, public_group,
):

    accessible = public_group.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_update_public_groupuser(
    super_admin_user, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_update_public_stream(
    super_admin_user, public_stream,
):

    accessible = public_stream.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_update_public_groupstream(
    super_admin_user, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_update_public_streamuser(
    super_admin_user, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_update_public_filter(
    super_admin_user, public_filter,
):

    accessible = public_filter.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_update_public_candidate_object(
    super_admin_user, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible


def test_super_admin_user_update_public_source_object(
    super_admin_user, public_source_object,
):

    accessible = public_source_object.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_update_keck1_telescope(
    super_admin_user, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_update_sedm(
    super_admin_user, sedm,
):

    accessible = sedm.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_update_public_group_sedm_allocation(
    super_admin_user, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible


def test_super_admin_user_delete_public_group(
    super_admin_user, public_group,
):

    accessible = public_group.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_super_admin_user_delete_public_groupuser(
    super_admin_user, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_super_admin_user_delete_public_stream(
    super_admin_user, public_stream,
):

    accessible = public_stream.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_super_admin_user_delete_public_groupstream(
    super_admin_user, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_super_admin_user_delete_public_streamuser(
    super_admin_user, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_super_admin_user_delete_public_filter(
    super_admin_user, public_filter,
):

    accessible = public_filter.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_super_admin_user_delete_public_candidate_object(
    super_admin_user, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible


def test_super_admin_user_delete_public_source_object(
    super_admin_user, public_source_object,
):

    accessible = public_source_object.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_super_admin_user_delete_keck1_telescope(
    super_admin_user, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_super_admin_user_delete_sedm(
    super_admin_user, sedm,
):

    accessible = sedm.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_super_admin_user_delete_public_group_sedm_allocation(
    super_admin_user, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible


def test_group_admin_user_create_public_group(
    group_admin_user, public_group,
):

    accessible = public_group.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_create_public_groupuser(
    group_admin_user, public_groupuser,
):
    accessible = public_groupuser.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_create_public_stream(
    group_admin_user, public_stream,
):

    accessible = public_stream.is_accessible_by(group_admin_user, mode="create")
    assert not accessible  # must be system admin


def test_group_admin_user_create_public_groupstream(
    group_admin_user, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_create_public_streamuser(
    group_admin_user, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(group_admin_user, mode="create")
    assert not accessible  # must be system admin


def test_group_admin_user_create_public_filter(
    group_admin_user, public_filter,
):

    accessible = public_filter.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_create_public_candidate_object(
    group_admin_user, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible


def test_group_admin_user_create_public_source_object(
    group_admin_user, public_source_object,
):

    accessible = public_source_object.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_create_keck1_telescope(
    group_admin_user, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_create_sedm(
    group_admin_user, sedm,
):

    accessible = sedm.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_create_public_group_sedm_allocation(
    group_admin_user, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible


def test_group_admin_user_read_public_group(
    group_admin_user, public_group,
):

    accessible = public_group.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_read_public_groupuser(
    group_admin_user, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_read_public_stream(
    group_admin_user, public_stream,
):

    accessible = public_stream.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_read_public_groupstream(
    group_admin_user, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_read_public_streamuser(
    group_admin_user, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_read_public_filter(
    group_admin_user, public_filter,
):

    accessible = public_filter.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_read_public_candidate_object(
    group_admin_user, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_read_public_source_object(
    group_admin_user, public_source_object,
):

    accessible = public_source_object.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_read_keck1_telescope(
    group_admin_user, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_read_sedm(
    group_admin_user, sedm,
):

    accessible = sedm.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_read_public_group_sedm_allocation(
    group_admin_user, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(
        group_admin_user, mode="read"
    )
    assert accessible


def test_group_admin_user_update_public_group(
    group_admin_user, public_group,
):

    accessible = public_group.is_accessible_by(group_admin_user, mode="update")
    assert accessible


def test_group_admin_user_update_public_groupuser(
    group_admin_user, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(group_admin_user, mode="update")
    assert accessible


def test_group_admin_user_update_public_stream(
    group_admin_user, public_stream,
):

    accessible = public_stream.is_accessible_by(group_admin_user, mode="update")
    assert not accessible  # needs system admin


def test_group_admin_user_update_public_groupstream(
    group_admin_user, public_groupstream,
):
    import pdb

    pdb.set_trace()
    accessible = public_groupstream.is_accessible_by(group_admin_user, mode="update")
    assert accessible


def test_group_admin_user_update_public_streamuser(
    group_admin_user, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(group_admin_user, mode="update")
    assert not accessible  # needs system admin


def test_group_admin_user_update_public_filter(
    group_admin_user, public_filter,
):

    accessible = public_filter.is_accessible_by(group_admin_user, mode="update")
    assert accessible


def test_group_admin_user_update_public_candidate_object(
    group_admin_user, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible


def test_group_admin_user_update_public_source_object(
    group_admin_user, public_source_object,
):

    accessible = public_source_object.is_accessible_by(group_admin_user, mode="update")
    assert accessible


def test_group_admin_user_update_keck1_telescope(
    group_admin_user, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(group_admin_user, mode="update")
    assert not accessible  # system admin


def test_group_admin_user_update_sedm(
    group_admin_user, sedm,
):

    accessible = sedm.is_accessible_by(group_admin_user, mode="update")
    assert not accessible  # sysadmin


def test_group_admin_user_update_public_group_sedm_allocation(
    group_admin_user, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible


def test_group_admin_user_delete_public_group(
    group_admin_user, public_group,
):

    accessible = public_group.is_accessible_by(group_admin_user, mode="delete")
    assert accessible


def test_group_admin_user_delete_public_groupuser(
    group_admin_user, public_groupuser,
):

    accessible = public_groupuser.is_accessible_by(group_admin_user, mode="delete")
    assert accessible


def test_group_admin_user_delete_public_stream(
    group_admin_user, public_stream,
):

    accessible = public_stream.is_accessible_by(group_admin_user, mode="delete")
    assert not accessible  # sys admin


def test_group_admin_user_delete_public_groupstream(
    group_admin_user, public_groupstream,
):

    accessible = public_groupstream.is_accessible_by(group_admin_user, mode="delete")
    assert accessible


def test_group_admin_user_delete_public_streamuser(
    group_admin_user, public_streamuser,
):

    accessible = public_streamuser.is_accessible_by(group_admin_user, mode="delete")
    assert not accessible  # sysadmin


def test_group_admin_user_delete_public_filter(
    group_admin_user, public_filter,
):

    accessible = public_filter.is_accessible_by(group_admin_user, mode="delete")
    assert accessible


def test_group_admin_user_delete_public_candidate_object(
    group_admin_user, public_candidate_object,
):

    accessible = public_candidate_object.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible


def test_group_admin_user_delete_public_source_object(
    group_admin_user, public_source_object,
):

    accessible = public_source_object.is_accessible_by(group_admin_user, mode="delete")
    assert accessible


def test_group_admin_user_delete_keck1_telescope(
    group_admin_user, keck1_telescope,
):

    accessible = keck1_telescope.is_accessible_by(group_admin_user, mode="delete")
    assert not accessible  # sysadmin


def test_group_admin_user_delete_sedm(
    group_admin_user, sedm,
):

    accessible = sedm.is_accessible_by(group_admin_user, mode="delete")
    assert not accessible  # sysadmin


def test_group_admin_user_delete_public_group_sedm_allocation(
    group_admin_user, public_group_sedm_allocation,
):

    accessible = public_group_sedm_allocation.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible
