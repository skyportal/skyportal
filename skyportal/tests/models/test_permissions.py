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


def test_user_create_public_group_taxonomy(user, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user, mode="create")
    assert accessible


def test_user_create_public_taxonomy(user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user, mode="create")
    assert accessible


def test_user_read_public_group_taxonomy(user, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user, mode="read")
    assert accessible


def test_user_read_public_taxonomy(user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user, mode="read")
    assert accessible


def test_user_update_public_group_taxonomy(user, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user, mode="update")
    assert not accessible  # must be super admin


def test_user_update_public_taxonomy(user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user, mode="update")
    assert not accessible  # must be super admin


def test_user_delete_public_group_taxonomy(user, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user, mode="delete")
    assert not accessible  # must be group admin


def test_user_delete_public_taxonomy(user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user, mode="delete")
    assert not accessible  # must be super admin


def test_user_group2_create_public_group_taxonomy(user_group2, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user_group2, mode="create")
    assert (
        not accessible
    )  # need read access on taxonomy, which is only visible to group 1


def test_user_group2_create_public_taxonomy(user_group2, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user_group2, mode="create")
    assert accessible


def test_user_group2_read_public_group_taxonomy(user_group2, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user_group2, mode="read")
    assert (
        not accessible
    )  # need read access on taxonomy, which is only visible to group 1


def test_user_group2_read_public_taxonomy(user_group2, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user_group2, mode="read")
    assert not accessible  # need to be in group 1


def test_user_group2_update_public_group_taxonomy(user_group2, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user_group2, mode="update")
    assert (
        not accessible
    )  # user must be in one of public_taxonomy's groups and must be a group admin


def test_user_group2_update_public_taxonomy(user_group2, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be a group admin of one of taxonomy's groups


def test_user_group2_delete_public_group_taxonomy(user_group2, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user_group2, mode="delete")
    assert (
        not accessible
    )  # need read access to taxonomy and must be a group admin of target group


def test_user_group2_delete_public_taxonomy(user_group2, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be sysadmin


def test_super_admin_user_create_public_group_taxonomy(
    super_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_create_public_taxonomy(super_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_read_public_group_taxonomy(
    super_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_read_public_taxonomy(super_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_update_public_group_taxonomy(
    super_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_update_public_taxonomy(super_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_delete_public_group_taxonomy(
    super_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_super_admin_user_delete_public_taxonomy(super_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_group_admin_user_create_public_group_taxonomy(
    group_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_create_public_taxonomy(group_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_read_public_group_taxonomy(
    group_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_read_public_taxonomy(group_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_update_public_group_taxonomy(
    group_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(group_admin_user, mode="update")
    assert accessible


def test_group_admin_user_update_public_taxonomy(group_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(group_admin_user, mode="update")
    assert not accessible  # need sysadmin


def test_group_admin_user_delete_public_group_taxonomy(
    group_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(group_admin_user, mode="delete")
    assert accessible


def test_group_admin_user_delete_public_taxonomy(group_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(group_admin_user, mode="delete")
    assert not accessible  # need sysadmin


def test_user_create_public_comment(user, public_comment):
    accessible = public_comment.is_accessible_by(user, mode="create")
    assert accessible


def test_user_read_public_comment(user, public_comment):
    accessible = public_comment.is_accessible_by(user, mode="read")
    assert accessible


def test_user_update_public_comment(user, public_comment):
    accessible = public_comment.is_accessible_by(user, mode="update")
    assert not accessible  # must be comment author


def test_user_delete_public_comment(user, public_comment):
    accessible = public_comment.is_accessible_by(user, mode="delete")
    assert not accessible  # must be comment author


def test_user_group2_create_public_comment(user_group2, public_comment):
    accessible = public_comment.is_accessible_by(user_group2, mode="create")
    assert accessible


def test_user_group2_read_public_comment(user_group2, public_comment):
    accessible = public_comment.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be a member of the comment's target groups


def test_user_group2_update_public_comment(user_group2, public_comment):
    accessible = public_comment.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be comment author


def test_user_group2_delete_public_comment(user_group2, public_comment):
    accessible = public_comment.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be comment author


def test_super_admin_user_create_public_comment(super_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_read_public_comment(super_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_update_public_comment(super_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_delete_public_comment(super_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_group_admin_user_create_public_comment(group_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_read_public_comment(group_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_update_public_comment(group_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(group_admin_user, mode="update")
    assert not accessible  # must be comment author


def test_group_admin_user_delete_public_comment(group_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(group_admin_user, mode="delete")
    assert not accessible  # must be comment author


def test_user_create_public_groupcomment(user, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user, mode="create")
    assert accessible


def test_user_read_public_groupcomment(user, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user, mode="read")
    assert accessible


def test_user_update_public_groupcomment(user, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user, mode="update")
    assert not accessible  # must be group admin


def test_user_delete_public_groupcomment(user, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user, mode="delete")
    assert not accessible  # must be group admin


def test_user_group2_create_public_groupcomment(user_group2, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user_group2, mode="create")
    assert not accessible  # must be able ot read the comment


def test_user_group2_read_public_groupcomment(user_group2, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be able to read the comment


def test_user_group2_update_public_groupcomment(user_group2, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be able to read the comment and be a group admin


def test_user_group2_delete_public_groupcomment(user_group2, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be able ot read the comment and be a group admin


def test_super_admin_user_create_public_groupcomment(
    super_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_read_public_groupcomment(
    super_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_update_public_groupcomment(
    super_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_delete_public_groupcomment(
    super_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_group_admin_user_create_public_groupcomment(
    group_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_read_public_groupcomment(
    group_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_update_public_groupcomment(
    group_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(group_admin_user, mode="update")
    assert accessible


def test_group_admin_user_delete_public_groupcomment(
    group_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(group_admin_user, mode="delete")
    assert accessible


def test_user_create_public_annotation(user, public_annotation):
    accessible = public_annotation.is_accessible_by(user, mode="create")
    assert accessible


def test_user_read_public_annotation(user, public_annotation):
    accessible = public_annotation.is_accessible_by(user, mode="read")
    assert accessible


def test_user_update_public_annotation(user, public_annotation):
    accessible = public_annotation.is_accessible_by(user, mode="update")
    assert not accessible  # must be annotation author


def test_user_delete_public_annotation(user, public_annotation):
    accessible = public_annotation.is_accessible_by(user, mode="delete")
    assert not accessible  # must be annotation author


def test_user_group2_create_public_annotation(user_group2, public_annotation):
    accessible = public_annotation.is_accessible_by(user_group2, mode="create")
    assert accessible


def test_user_group2_read_public_annotation(user_group2, public_annotation):
    accessible = public_annotation.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be a member of the annotation's target groups


def test_user_group2_update_public_annotation(user_group2, public_annotation):
    accessible = public_annotation.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be annotation author


def test_user_group2_delete_public_annotation(user_group2, public_annotation):
    accessible = public_annotation.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be annotation author


def test_super_admin_user_create_public_annotation(super_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_read_public_annotation(super_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_update_public_annotation(super_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_delete_public_annotation(super_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_group_admin_user_create_public_annotation(group_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_read_public_annotation(group_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_update_public_annotation(group_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(group_admin_user, mode="update")
    assert not accessible  # must be annotation author


def test_group_admin_user_delete_public_annotation(group_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(group_admin_user, mode="delete")
    assert not accessible  # must be annotation author


def test_user_create_public_groupannotation(user, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user, mode="create")
    assert accessible


def test_user_read_public_groupannotation(user, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user, mode="read")
    assert accessible


def test_user_update_public_groupannotation(user, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user, mode="update")
    assert not accessible  # must be group admin


def test_user_delete_public_groupannotation(user, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user, mode="delete")
    assert not accessible  # must be group admin


def test_user_group2_create_public_groupannotation(user_group2, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user_group2, mode="create")
    assert not accessible  # must be able ot read the annotation


def test_user_group2_read_public_groupannotation(user_group2, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be able to read the annotation


def test_user_group2_update_public_groupannotation(user_group2, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be able to read the annotation and be a group admin


def test_user_group2_delete_public_groupannotation(user_group2, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be able ot read the annotation and be a group admin


def test_super_admin_user_create_public_groupannotation(
    super_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible


def test_super_admin_user_read_public_groupannotation(
    super_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_update_public_groupannotation(
    super_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible


def test_super_admin_user_delete_public_groupannotation(
    super_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible


def test_group_admin_user_create_public_groupannotation(
    group_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible


def test_group_admin_user_read_public_groupannotation(
    group_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_update_public_groupannotation(
    group_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible


def test_group_admin_user_delete_public_groupannotation(
    group_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible


def test_user_create_public_classification(user, public_classification):
    accessible = public_classification.is_accessible_by(user, mode="create")
    assert accessible


def test_user_read_public_classification(user, public_classification):
    accessible = public_classification.is_accessible_by(user, mode="read")
    assert accessible


def test_user_update_public_classification(user, public_classification):
    accessible = public_classification.is_accessible_by(user, mode="update")
    assert not accessible  # must be classification author


def test_user_delete_public_classification(user, public_classification):
    accessible = public_classification.is_accessible_by(user, mode="delete")
    assert not accessible  # must be classification author


def test_user_group2_create_public_classification(user_group2, public_classification):
    accessible = public_classification.is_accessible_by(user_group2, mode="create")
    assert not accessible  # need read access to underlying taxonomy


def test_user_group2_read_public_classification(user_group2, public_classification):
    accessible = public_classification.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be a member of the classification's target groups


def test_user_group2_update_public_classification(user_group2, public_classification):
    accessible = public_classification.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be classification author


def test_user_group2_delete_public_classification(user_group2, public_classification):
    accessible = public_classification.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be classification author


def test_super_admin_user_create_public_classification(
    super_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_read_public_classification(
    super_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_update_public_classification(
    super_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_delete_public_classification(
    super_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_group_admin_user_create_public_classification(
    group_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_read_public_classification(
    group_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_update_public_classification(
    group_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(group_admin_user, mode="update")
    assert not accessible  # must be classification author


def test_group_admin_user_delete_public_classification(
    group_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(group_admin_user, mode="delete")
    assert not accessible  # must be classification author


def test_user_create_public_groupclassification(user, public_groupclassification):
    accessible = public_groupclassification.is_accessible_by(user, mode="create")
    assert accessible


def test_user_read_public_groupclassification(user, public_groupclassification):
    accessible = public_groupclassification.is_accessible_by(user, mode="read")
    assert accessible


def test_user_update_public_groupclassification(user, public_groupclassification):
    accessible = public_groupclassification.is_accessible_by(user, mode="update")
    assert not accessible  # must be group admin


def test_user_delete_public_groupclassification(user, public_groupclassification):
    accessible = public_groupclassification.is_accessible_by(user, mode="delete")
    assert not accessible  # must be group admin


def test_user_group2_create_public_groupclassification(
    user_group2, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(user_group2, mode="create")
    assert not accessible  # must be able ot read the classification


def test_user_group2_read_public_groupclassification(
    user_group2, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be able to read the classification


def test_user_group2_update_public_groupclassification(
    user_group2, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(user_group2, mode="update")
    assert (
        not accessible
    )  # must be able to read the classification and be a group admin


def test_user_group2_delete_public_groupclassification(
    user_group2, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(user_group2, mode="delete")
    assert (
        not accessible
    )  # must be able ot read the classification and be a group admin


def test_super_admin_user_create_public_groupclassification(
    super_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible


def test_super_admin_user_read_public_groupclassification(
    super_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        super_admin_user, mode="read"
    )
    assert accessible


def test_super_admin_user_update_public_groupclassification(
    super_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible


def test_super_admin_user_delete_public_groupclassification(
    super_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible


def test_group_admin_user_create_public_groupclassification(
    group_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible


def test_group_admin_user_read_public_groupclassification(
    group_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        group_admin_user, mode="read"
    )
    assert accessible


def test_group_admin_user_update_public_groupclassification(
    group_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible


def test_group_admin_user_delete_public_groupclassification(
    group_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible
