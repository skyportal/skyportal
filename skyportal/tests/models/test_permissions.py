def test_user_create_public_group(user, public_group):
    accessible = public_group.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_groupuser(user, public_groupuser):
    accessible = public_groupuser.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_stream(user, public_stream):
    accessible = public_stream.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_groupstream(user, public_groupstream):
    accessible = public_groupstream.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_streamuser(user, public_streamuser):
    accessible = public_streamuser.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_filter(user, public_filter):
    accessible = public_filter.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_candidate_object(user, public_candidate_object):
    accessible = public_candidate_object.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_source_object(user, public_source_object):
    accessible = public_source_object.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_keck1_telescope(user, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_sedm(user, sedm):
    accessible = sedm.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_group_sedm_allocation(user, public_group_sedm_allocation):
    accessible = public_group_sedm_allocation.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_group_taxonomy(user, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_taxonomy(user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_comment(user, public_comment):
    accessible = public_comment.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_groupcomment(user, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_annotation(user, public_annotation):
    accessible = public_annotation.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_groupannotation(user, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_classification(user, public_classification):
    accessible = public_classification.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_groupclassification(user, public_groupclassification):
    accessible = public_groupclassification.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_source_photometry_point(
    user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_source_spectrum(user, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_source_groupphotometry(user, public_source_groupphotometry):
    accessible = public_source_groupphotometry.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_source_groupspectrum(user, public_source_groupspectrum):
    accessible = public_source_groupspectrum.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_source_followuprequest(user, public_source_followuprequest):
    accessible = public_source_followuprequest.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_source_followup_request_target_group(
    user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user, mode="create"
    )
    assert accessible == accessible


def test_user_create_public_thumbnail(user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_red_transients_run(user, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_problematic_assignment(user, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_invitation(user, invitation):
    accessible = invitation.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_user_notification(user, user_notification):
    accessible = user_notification.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_gcn(user, gcn):
    accessible = gcn.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_create_public_comment_on_gcn(user, public_comment_on_gcn):
    accessible = public_comment_on_gcn.is_accessible_by(user, mode="create")
    assert accessible == accessible


def test_user_read_public_group(user, public_group):
    accessible = public_group.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_groupuser(user, public_groupuser):
    accessible = public_groupuser.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_stream(user, public_stream):
    accessible = public_stream.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_groupstream(user, public_groupstream):
    accessible = public_groupstream.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_streamuser(user, public_streamuser):
    accessible = public_streamuser.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_filter(user, public_filter):
    accessible = public_filter.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_candidate_object(user, public_candidate_object):
    accessible = public_candidate_object.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_source_object(user, public_source_object):
    accessible = public_source_object.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_keck1_telescope(user, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_sedm(user, sedm):
    accessible = sedm.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_group_sedm_allocation(user, public_group_sedm_allocation):
    accessible = public_group_sedm_allocation.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_group_taxonomy(user, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_taxonomy(user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_comment(user, public_comment):
    accessible = public_comment.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_groupcomment(user, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_annotation(user, public_annotation):
    accessible = public_annotation.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_groupannotation(user, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_classification(user, public_classification):
    accessible = public_classification.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_groupclassification(user, public_groupclassification):
    accessible = public_groupclassification.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_source_photometry_point(user, public_source_photometry_point):
    accessible = public_source_photometry_point.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_source_spectrum(user, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_source_groupphotometry(user, public_source_groupphotometry):
    accessible = public_source_groupphotometry.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_source_groupspectrum(user, public_source_groupspectrum):
    accessible = public_source_groupspectrum.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_source_followuprequest(user, public_source_followuprequest):
    accessible = public_source_followuprequest.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_source_followup_request_target_group(
    user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user, mode="read"
    )
    assert accessible == accessible


def test_user_read_public_thumbnail(user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_red_transients_run(user, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_problematic_assignment(user, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_invitation(user, invitation):
    accessible = invitation.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_user_notification(user, user_notification):
    accessible = user_notification.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_gcn(user, gcn):
    accessible = gcn.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_read_public_comment_on_gcn(user, public_comment_on_gcn):
    accessible = public_comment_on_gcn.is_accessible_by(user, mode="read")
    assert accessible == accessible


def test_user_update_public_group(user, public_group):
    accessible = public_group.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_groupuser(user, public_groupuser):
    accessible = public_groupuser.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_stream(user, public_stream):
    accessible = public_stream.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_groupstream(user, public_groupstream):
    accessible = public_groupstream.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_streamuser(user, public_streamuser):
    accessible = public_streamuser.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_filter(user, public_filter):
    accessible = public_filter.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_candidate_object(user, public_candidate_object):
    accessible = public_candidate_object.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_source_object(user, public_source_object):
    accessible = public_source_object.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_keck1_telescope(user, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_sedm(user, sedm):
    accessible = sedm.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_group_sedm_allocation(user, public_group_sedm_allocation):
    accessible = public_group_sedm_allocation.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_group_taxonomy(user, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_taxonomy(user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_comment(user, public_comment):
    accessible = public_comment.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_groupcomment(user, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_annotation(user, public_annotation):
    accessible = public_annotation.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_groupannotation(user, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_classification(user, public_classification):
    accessible = public_classification.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_groupclassification(user, public_groupclassification):
    accessible = public_groupclassification.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_source_photometry_point(
    user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_source_spectrum(user, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_source_groupphotometry(user, public_source_groupphotometry):
    accessible = public_source_groupphotometry.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_source_groupspectrum(user, public_source_groupspectrum):
    accessible = public_source_groupspectrum.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_source_followuprequest(user, public_source_followuprequest):
    accessible = public_source_followuprequest.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_source_followup_request_target_group(
    user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user, mode="update"
    )
    assert accessible == accessible


def test_user_update_public_thumbnail(user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_red_transients_run(user, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_problematic_assignment(user, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_invitation(user, invitation):
    accessible = invitation.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_user_notification(user, user_notification):
    accessible = user_notification.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_gcn(user, gcn):
    accessible = gcn.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_update_public_comment_on_gcn(user, public_comment_on_gcn):
    accessible = public_comment_on_gcn.is_accessible_by(user, mode="update")
    assert accessible == accessible


def test_user_delete_public_group(user, public_group):
    accessible = public_group.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_groupuser(user, public_groupuser):
    accessible = public_groupuser.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_stream(user, public_stream):
    accessible = public_stream.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_groupstream(user, public_groupstream):
    accessible = public_groupstream.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_streamuser(user, public_streamuser):
    accessible = public_streamuser.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_filter(user, public_filter):
    accessible = public_filter.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_candidate_object(user, public_candidate_object):
    accessible = public_candidate_object.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_source_object(user, public_source_object):
    accessible = public_source_object.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_keck1_telescope(user, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_sedm(user, sedm):
    accessible = sedm.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_group_sedm_allocation(user, public_group_sedm_allocation):
    accessible = public_group_sedm_allocation.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_group_taxonomy(user, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_taxonomy(user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_comment(user, public_comment):
    accessible = public_comment.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_groupcomment(user, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_annotation(user, public_annotation):
    accessible = public_annotation.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_groupannotation(user, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_classification(user, public_classification):
    accessible = public_classification.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_groupclassification(user, public_groupclassification):
    accessible = public_groupclassification.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_source_photometry_point(
    user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_source_spectrum(user, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_source_groupphotometry(user, public_source_groupphotometry):
    accessible = public_source_groupphotometry.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_source_groupspectrum(user, public_source_groupspectrum):
    accessible = public_source_groupspectrum.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_source_followuprequest(user, public_source_followuprequest):
    accessible = public_source_followuprequest.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_source_followup_request_target_group(
    user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user, mode="delete"
    )
    assert accessible == accessible


def test_user_delete_public_thumbnail(user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_red_transients_run(user, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_problematic_assignment(user, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_invitation(user, invitation):
    accessible = invitation.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_user_notification(user, user_notification):
    accessible = user_notification.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_gcn(user, gcn):
    accessible = gcn.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_delete_public_comment_on_gcn(user, public_comment_on_gcn):
    accessible = public_comment_on_gcn.is_accessible_by(user, mode="delete")
    assert accessible == accessible


def test_user_group2_create_public_group(user_group2, public_group):
    accessible = public_group.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_groupuser(user_group2, public_groupuser):
    accessible = public_groupuser.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_stream(user_group2, public_stream):
    accessible = public_stream.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_groupstream(user_group2, public_groupstream):
    accessible = public_groupstream.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_streamuser(user_group2, public_streamuser):
    accessible = public_streamuser.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_filter(user_group2, public_filter):
    accessible = public_filter.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_candidate_object(
    user_group2, public_candidate_object
):
    accessible = public_candidate_object.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_source_object(user_group2, public_source_object):
    accessible = public_source_object.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_keck1_telescope(user_group2, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_sedm(user_group2, sedm):
    accessible = sedm.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_group_sedm_allocation(
    user_group2, public_group_sedm_allocation
):
    accessible = public_group_sedm_allocation.is_accessible_by(
        user_group2, mode="create"
    )
    assert accessible == accessible


def test_user_group2_create_public_group_taxonomy(user_group2, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_taxonomy(user_group2, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_comment(user_group2, public_comment):
    accessible = public_comment.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_groupcomment(user_group2, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_annotation(user_group2, public_annotation):
    accessible = public_annotation.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_groupannotation(user_group2, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_classification(user_group2, public_classification):
    accessible = public_classification.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_groupclassification(
    user_group2, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_source_photometry_point(
    user_group2, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        user_group2, mode="create"
    )
    assert accessible == accessible


def test_user_group2_create_public_source_spectrum(user_group2, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_source_groupphotometry(
    user_group2, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        user_group2, mode="create"
    )
    assert accessible == accessible


def test_user_group2_create_public_source_groupspectrum(
    user_group2, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        user_group2, mode="create"
    )
    assert accessible == accessible


def test_user_group2_create_public_source_followuprequest(
    user_group2, public_source_followuprequest
):
    accessible = public_source_followuprequest.is_accessible_by(
        user_group2, mode="create"
    )
    assert accessible == accessible


def test_user_group2_create_public_source_followup_request_target_group(
    user_group2, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user_group2, mode="create"
    )
    assert accessible == accessible


def test_user_group2_create_public_thumbnail(user_group2, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_red_transients_run(user_group2, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_problematic_assignment(user_group2, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_invitation(user_group2, invitation):
    accessible = invitation.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_user_notification(user_group2, user_notification):
    accessible = user_notification.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_gcn(user_group2, gcn):
    accessible = gcn.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_create_public_comment_on_gcn(user_group2, public_comment_on_gcn):
    accessible = public_comment_on_gcn.is_accessible_by(user_group2, mode="create")
    assert accessible == accessible


def test_user_group2_read_public_group(user_group2, public_group):
    accessible = public_group.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_groupuser(user_group2, public_groupuser):
    accessible = public_groupuser.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_stream(user_group2, public_stream):
    accessible = public_stream.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_groupstream(user_group2, public_groupstream):
    accessible = public_groupstream.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_streamuser(user_group2, public_streamuser):
    accessible = public_streamuser.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_filter(user_group2, public_filter):
    accessible = public_filter.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_candidate_object(user_group2, public_candidate_object):
    accessible = public_candidate_object.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_source_object(user_group2, public_source_object):
    accessible = public_source_object.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_keck1_telescope(user_group2, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_sedm(user_group2, sedm):
    accessible = sedm.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_group_sedm_allocation(
    user_group2, public_group_sedm_allocation
):
    accessible = public_group_sedm_allocation.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_group_taxonomy(user_group2, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_taxonomy(user_group2, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_comment(user_group2, public_comment):
    accessible = public_comment.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_groupcomment(user_group2, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_annotation(user_group2, public_annotation):
    accessible = public_annotation.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_groupannotation(user_group2, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_classification(user_group2, public_classification):
    accessible = public_classification.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_groupclassification(
    user_group2, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_source_photometry_point(
    user_group2, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        user_group2, mode="read"
    )
    assert accessible == accessible


def test_user_group2_read_public_source_spectrum(user_group2, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_source_groupphotometry(
    user_group2, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        user_group2, mode="read"
    )
    assert accessible == accessible


def test_user_group2_read_public_source_groupspectrum(
    user_group2, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_source_followuprequest(
    user_group2, public_source_followuprequest
):
    accessible = public_source_followuprequest.is_accessible_by(
        user_group2, mode="read"
    )
    assert accessible == accessible


def test_user_group2_read_public_source_followup_request_target_group(
    user_group2, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user_group2, mode="read"
    )
    assert accessible == accessible


def test_user_group2_read_public_thumbnail(user_group2, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_red_transients_run(user_group2, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_problematic_assignment(user_group2, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_invitation(user_group2, invitation):
    accessible = invitation.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_user_notification(user_group2, user_notification):
    accessible = user_notification.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_gcn(user_group2, gcn):
    accessible = gcn.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_read_public_comment_on_gcn(user_group2, public_comment_on_gcn):
    accessible = public_comment_on_gcn.is_accessible_by(user_group2, mode="read")
    assert accessible == accessible


def test_user_group2_update_public_group(user_group2, public_group):
    accessible = public_group.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_groupuser(user_group2, public_groupuser):
    accessible = public_groupuser.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_stream(user_group2, public_stream):
    accessible = public_stream.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_groupstream(user_group2, public_groupstream):
    accessible = public_groupstream.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_streamuser(user_group2, public_streamuser):
    accessible = public_streamuser.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_filter(user_group2, public_filter):
    accessible = public_filter.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_candidate_object(
    user_group2, public_candidate_object
):
    accessible = public_candidate_object.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_source_object(user_group2, public_source_object):
    accessible = public_source_object.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_keck1_telescope(user_group2, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_sedm(user_group2, sedm):
    accessible = sedm.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_group_sedm_allocation(
    user_group2, public_group_sedm_allocation
):
    accessible = public_group_sedm_allocation.is_accessible_by(
        user_group2, mode="update"
    )
    assert accessible == accessible


def test_user_group2_update_public_group_taxonomy(user_group2, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_taxonomy(user_group2, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_comment(user_group2, public_comment):
    accessible = public_comment.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_groupcomment(user_group2, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_annotation(user_group2, public_annotation):
    accessible = public_annotation.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_groupannotation(user_group2, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_classification(user_group2, public_classification):
    accessible = public_classification.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_groupclassification(
    user_group2, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_source_photometry_point(
    user_group2, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        user_group2, mode="update"
    )
    assert accessible == accessible


def test_user_group2_update_public_source_spectrum(user_group2, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_source_groupphotometry(
    user_group2, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        user_group2, mode="update"
    )
    assert accessible == accessible


def test_user_group2_update_public_source_groupspectrum(
    user_group2, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        user_group2, mode="update"
    )
    assert accessible == accessible


def test_user_group2_update_public_source_followuprequest(
    user_group2, public_source_followuprequest
):
    accessible = public_source_followuprequest.is_accessible_by(
        user_group2, mode="update"
    )
    assert accessible == accessible


def test_user_group2_update_public_source_followup_request_target_group(
    user_group2, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user_group2, mode="update"
    )
    assert accessible == accessible


def test_user_group2_update_public_thumbnail(user_group2, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_red_transients_run(user_group2, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_problematic_assignment(user_group2, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_invitation(user_group2, invitation):
    accessible = invitation.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_user_notification(user_group2, user_notification):
    accessible = user_notification.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_gcn(user_group2, gcn):
    accessible = gcn.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_update_public_comment_on_gcn(user_group2, public_comment_on_gcn):
    accessible = public_comment_on_gcn.is_accessible_by(user_group2, mode="update")
    assert accessible == accessible


def test_user_group2_delete_public_group(user_group2, public_group):
    accessible = public_group.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_groupuser(user_group2, public_groupuser):
    accessible = public_groupuser.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_stream(user_group2, public_stream):
    accessible = public_stream.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_groupstream(user_group2, public_groupstream):
    accessible = public_groupstream.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_streamuser(user_group2, public_streamuser):
    accessible = public_streamuser.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_filter(user_group2, public_filter):
    accessible = public_filter.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_candidate_object(
    user_group2, public_candidate_object
):
    accessible = public_candidate_object.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_source_object(user_group2, public_source_object):
    accessible = public_source_object.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_keck1_telescope(user_group2, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_sedm(user_group2, sedm):
    accessible = sedm.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_group_sedm_allocation(
    user_group2, public_group_sedm_allocation
):
    accessible = public_group_sedm_allocation.is_accessible_by(
        user_group2, mode="delete"
    )
    assert accessible == accessible


def test_user_group2_delete_public_group_taxonomy(user_group2, public_group_taxonomy):
    accessible = public_group_taxonomy.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_taxonomy(user_group2, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_comment(user_group2, public_comment):
    accessible = public_comment.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_groupcomment(user_group2, public_groupcomment):
    accessible = public_groupcomment.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_annotation(user_group2, public_annotation):
    accessible = public_annotation.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_groupannotation(user_group2, public_groupannotation):
    accessible = public_groupannotation.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_classification(user_group2, public_classification):
    accessible = public_classification.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_groupclassification(
    user_group2, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_source_photometry_point(
    user_group2, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        user_group2, mode="delete"
    )
    assert accessible == accessible


def test_user_group2_delete_public_source_spectrum(user_group2, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_source_groupphotometry(
    user_group2, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        user_group2, mode="delete"
    )
    assert accessible == accessible


def test_user_group2_delete_public_source_groupspectrum(
    user_group2, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        user_group2, mode="delete"
    )
    assert accessible == accessible


def test_user_group2_delete_public_source_followuprequest(
    user_group2, public_source_followuprequest
):
    accessible = public_source_followuprequest.is_accessible_by(
        user_group2, mode="delete"
    )
    assert accessible == accessible


def test_user_group2_delete_public_source_followup_request_target_group(
    user_group2, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user_group2, mode="delete"
    )
    assert accessible == accessible


def test_user_group2_delete_public_thumbnail(user_group2, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_red_transients_run(user_group2, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_problematic_assignment(user_group2, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_invitation(user_group2, invitation):
    accessible = invitation.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_user_notification(user_group2, user_notification):
    accessible = user_notification.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_gcn(user_group2, gcn):
    accessible = gcn.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_user_group2_delete_public_comment_on_gcn(user_group2, public_comment_on_gcn):
    accessible = public_comment_on_gcn.is_accessible_by(user_group2, mode="delete")
    assert accessible == accessible


def test_super_admin_user_create_public_group(super_admin_user, public_group):
    accessible = public_group.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_public_groupuser(super_admin_user, public_groupuser):
    accessible = public_groupuser.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_public_stream(super_admin_user, public_stream):
    accessible = public_stream.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_public_groupstream(
    super_admin_user, public_groupstream
):
    accessible = public_groupstream.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_public_streamuser(super_admin_user, public_streamuser):
    accessible = public_streamuser.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_public_filter(super_admin_user, public_filter):
    accessible = public_filter.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_public_candidate_object(
    super_admin_user, public_candidate_object
):
    accessible = public_candidate_object.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible == accessible


def test_super_admin_user_create_public_source_object(
    super_admin_user, public_source_object
):
    accessible = public_source_object.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_keck1_telescope(super_admin_user, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_sedm(super_admin_user, sedm):
    accessible = sedm.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_public_group_sedm_allocation(
    super_admin_user, public_group_sedm_allocation
):
    accessible = public_group_sedm_allocation.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible == accessible


def test_super_admin_user_create_public_group_taxonomy(
    super_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_public_taxonomy(super_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_public_comment(super_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_public_groupcomment(
    super_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_public_annotation(super_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_public_groupannotation(
    super_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible == accessible


def test_super_admin_user_create_public_classification(
    super_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_public_groupclassification(
    super_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible == accessible


def test_super_admin_user_create_public_source_photometry_point(
    super_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible == accessible


def test_super_admin_user_create_public_source_spectrum(
    super_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible == accessible


def test_super_admin_user_create_public_source_groupphotometry(
    super_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible == accessible


def test_super_admin_user_create_public_source_groupspectrum(
    super_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible == accessible


def test_super_admin_user_create_public_source_followuprequest(
    super_admin_user, public_source_followuprequest
):
    accessible = public_source_followuprequest.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible == accessible


def test_super_admin_user_create_public_source_followup_request_target_group(
    super_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible == accessible


def test_super_admin_user_create_public_thumbnail(super_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_red_transients_run(
    super_admin_user, red_transients_run
):
    accessible = red_transients_run.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_problematic_assignment(
    super_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible == accessible


def test_super_admin_user_create_invitation(super_admin_user, invitation):
    accessible = invitation.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_user_notification(super_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_gcn(super_admin_user, gcn):
    accessible = gcn.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_create_public_comment_on_gcn(
    super_admin_user, public_comment_on_gcn
):
    accessible = public_comment_on_gcn.is_accessible_by(super_admin_user, mode="create")
    assert accessible == accessible


def test_super_admin_user_read_public_group(super_admin_user, public_group):
    accessible = public_group.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_groupuser(super_admin_user, public_groupuser):
    accessible = public_groupuser.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_stream(super_admin_user, public_stream):
    accessible = public_stream.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_groupstream(super_admin_user, public_groupstream):
    accessible = public_groupstream.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_streamuser(super_admin_user, public_streamuser):
    accessible = public_streamuser.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_filter(super_admin_user, public_filter):
    accessible = public_filter.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_candidate_object(
    super_admin_user, public_candidate_object
):
    accessible = public_candidate_object.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_source_object(
    super_admin_user, public_source_object
):
    accessible = public_source_object.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_keck1_telescope(super_admin_user, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_sedm(super_admin_user, sedm):
    accessible = sedm.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_group_sedm_allocation(
    super_admin_user, public_group_sedm_allocation
):
    accessible = public_group_sedm_allocation.is_accessible_by(
        super_admin_user, mode="read"
    )
    assert accessible == accessible


def test_super_admin_user_read_public_group_taxonomy(
    super_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_taxonomy(super_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_comment(super_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_groupcomment(
    super_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_annotation(super_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_groupannotation(
    super_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_classification(
    super_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_groupclassification(
    super_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        super_admin_user, mode="read"
    )
    assert accessible == accessible


def test_super_admin_user_read_public_source_photometry_point(
    super_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        super_admin_user, mode="read"
    )
    assert accessible == accessible


def test_super_admin_user_read_public_source_spectrum(
    super_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_source_groupphotometry(
    super_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        super_admin_user, mode="read"
    )
    assert accessible == accessible


def test_super_admin_user_read_public_source_groupspectrum(
    super_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        super_admin_user, mode="read"
    )
    assert accessible == accessible


def test_super_admin_user_read_public_source_followuprequest(
    super_admin_user, public_source_followuprequest
):
    accessible = public_source_followuprequest.is_accessible_by(
        super_admin_user, mode="read"
    )
    assert accessible == accessible


def test_super_admin_user_read_public_source_followup_request_target_group(
    super_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        super_admin_user, mode="read"
    )
    assert accessible == accessible


def test_super_admin_user_read_public_thumbnail(super_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_red_transients_run(super_admin_user, red_transients_run):
    accessible = red_transients_run.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_problematic_assignment(
    super_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_invitation(super_admin_user, invitation):
    accessible = invitation.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_user_notification(super_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_gcn(super_admin_user, gcn):
    accessible = gcn.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_read_public_comment_on_gcn(
    super_admin_user, public_comment_on_gcn
):
    accessible = public_comment_on_gcn.is_accessible_by(super_admin_user, mode="read")
    assert accessible == accessible


def test_super_admin_user_update_public_group(super_admin_user, public_group):
    accessible = public_group.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_public_groupuser(super_admin_user, public_groupuser):
    accessible = public_groupuser.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_public_stream(super_admin_user, public_stream):
    accessible = public_stream.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_public_groupstream(
    super_admin_user, public_groupstream
):
    accessible = public_groupstream.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_public_streamuser(super_admin_user, public_streamuser):
    accessible = public_streamuser.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_public_filter(super_admin_user, public_filter):
    accessible = public_filter.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_public_candidate_object(
    super_admin_user, public_candidate_object
):
    accessible = public_candidate_object.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible == accessible


def test_super_admin_user_update_public_source_object(
    super_admin_user, public_source_object
):
    accessible = public_source_object.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_keck1_telescope(super_admin_user, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_sedm(super_admin_user, sedm):
    accessible = sedm.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_public_group_sedm_allocation(
    super_admin_user, public_group_sedm_allocation
):
    accessible = public_group_sedm_allocation.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible == accessible


def test_super_admin_user_update_public_group_taxonomy(
    super_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_public_taxonomy(super_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_public_comment(super_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_public_groupcomment(
    super_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_public_annotation(super_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_public_groupannotation(
    super_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible == accessible


def test_super_admin_user_update_public_classification(
    super_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_public_groupclassification(
    super_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible == accessible


def test_super_admin_user_update_public_source_photometry_point(
    super_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible == accessible


def test_super_admin_user_update_public_source_spectrum(
    super_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible == accessible


def test_super_admin_user_update_public_source_groupphotometry(
    super_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible == accessible


def test_super_admin_user_update_public_source_groupspectrum(
    super_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible == accessible


def test_super_admin_user_update_public_source_followuprequest(
    super_admin_user, public_source_followuprequest
):
    accessible = public_source_followuprequest.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible == accessible


def test_super_admin_user_update_public_source_followup_request_target_group(
    super_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible == accessible


def test_super_admin_user_update_public_thumbnail(super_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_red_transients_run(
    super_admin_user, red_transients_run
):
    accessible = red_transients_run.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_problematic_assignment(
    super_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible == accessible


def test_super_admin_user_update_invitation(super_admin_user, invitation):
    accessible = invitation.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_user_notification(super_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_gcn(super_admin_user, gcn):
    accessible = gcn.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_update_public_comment_on_gcn(
    super_admin_user, public_comment_on_gcn
):
    accessible = public_comment_on_gcn.is_accessible_by(super_admin_user, mode="update")
    assert accessible == accessible


def test_super_admin_user_delete_public_group(super_admin_user, public_group):
    accessible = public_group.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_public_groupuser(super_admin_user, public_groupuser):
    accessible = public_groupuser.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_public_stream(super_admin_user, public_stream):
    accessible = public_stream.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_public_groupstream(
    super_admin_user, public_groupstream
):
    accessible = public_groupstream.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_public_streamuser(super_admin_user, public_streamuser):
    accessible = public_streamuser.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_public_filter(super_admin_user, public_filter):
    accessible = public_filter.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_public_candidate_object(
    super_admin_user, public_candidate_object
):
    accessible = public_candidate_object.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_super_admin_user_delete_public_source_object(
    super_admin_user, public_source_object
):
    accessible = public_source_object.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_keck1_telescope(super_admin_user, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_sedm(super_admin_user, sedm):
    accessible = sedm.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_public_group_sedm_allocation(
    super_admin_user, public_group_sedm_allocation
):
    accessible = public_group_sedm_allocation.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_super_admin_user_delete_public_group_taxonomy(
    super_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_public_taxonomy(super_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_public_comment(super_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_public_groupcomment(
    super_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_public_annotation(super_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_public_groupannotation(
    super_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_super_admin_user_delete_public_classification(
    super_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_public_groupclassification(
    super_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_super_admin_user_delete_public_source_photometry_point(
    super_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_super_admin_user_delete_public_source_spectrum(
    super_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_super_admin_user_delete_public_source_groupphotometry(
    super_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_super_admin_user_delete_public_source_groupspectrum(
    super_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_super_admin_user_delete_public_source_followuprequest(
    super_admin_user, public_source_followuprequest
):
    accessible = public_source_followuprequest.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_super_admin_user_delete_public_source_followup_request_target_group(
    super_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_super_admin_user_delete_public_thumbnail(super_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_red_transients_run(
    super_admin_user, red_transients_run
):
    accessible = red_transients_run.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_problematic_assignment(
    super_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_super_admin_user_delete_invitation(super_admin_user, invitation):
    accessible = invitation.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_user_notification(super_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_gcn(super_admin_user, gcn):
    accessible = gcn.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_super_admin_user_delete_public_comment_on_gcn(
    super_admin_user, public_comment_on_gcn
):
    accessible = public_comment_on_gcn.is_accessible_by(super_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_create_public_group(group_admin_user, public_group):
    accessible = public_group.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_public_groupuser(group_admin_user, public_groupuser):
    accessible = public_groupuser.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_public_stream(group_admin_user, public_stream):
    accessible = public_stream.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_public_groupstream(
    group_admin_user, public_groupstream
):
    accessible = public_groupstream.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_public_streamuser(group_admin_user, public_streamuser):
    accessible = public_streamuser.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_public_filter(group_admin_user, public_filter):
    accessible = public_filter.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_public_candidate_object(
    group_admin_user, public_candidate_object
):
    accessible = public_candidate_object.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible == accessible


def test_group_admin_user_create_public_source_object(
    group_admin_user, public_source_object
):
    accessible = public_source_object.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_keck1_telescope(group_admin_user, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_sedm(group_admin_user, sedm):
    accessible = sedm.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_public_group_sedm_allocation(
    group_admin_user, public_group_sedm_allocation
):
    accessible = public_group_sedm_allocation.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible == accessible


def test_group_admin_user_create_public_group_taxonomy(
    group_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_public_taxonomy(group_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_public_comment(group_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_public_groupcomment(
    group_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_public_annotation(group_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_public_groupannotation(
    group_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible == accessible


def test_group_admin_user_create_public_classification(
    group_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_public_groupclassification(
    group_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible == accessible


def test_group_admin_user_create_public_source_photometry_point(
    group_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible == accessible


def test_group_admin_user_create_public_source_spectrum(
    group_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible == accessible


def test_group_admin_user_create_public_source_groupphotometry(
    group_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible == accessible


def test_group_admin_user_create_public_source_groupspectrum(
    group_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible == accessible


def test_group_admin_user_create_public_source_followuprequest(
    group_admin_user, public_source_followuprequest
):
    accessible = public_source_followuprequest.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible == accessible


def test_group_admin_user_create_public_source_followup_request_target_group(
    group_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible == accessible


def test_group_admin_user_create_public_thumbnail(group_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_red_transients_run(
    group_admin_user, red_transients_run
):
    accessible = red_transients_run.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_problematic_assignment(
    group_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible == accessible


def test_group_admin_user_create_invitation(group_admin_user, invitation):
    accessible = invitation.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_user_notification(group_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_gcn(group_admin_user, gcn):
    accessible = gcn.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_create_public_comment_on_gcn(
    group_admin_user, public_comment_on_gcn
):
    accessible = public_comment_on_gcn.is_accessible_by(group_admin_user, mode="create")
    assert accessible == accessible


def test_group_admin_user_read_public_group(group_admin_user, public_group):
    accessible = public_group.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_groupuser(group_admin_user, public_groupuser):
    accessible = public_groupuser.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_stream(group_admin_user, public_stream):
    accessible = public_stream.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_groupstream(group_admin_user, public_groupstream):
    accessible = public_groupstream.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_streamuser(group_admin_user, public_streamuser):
    accessible = public_streamuser.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_filter(group_admin_user, public_filter):
    accessible = public_filter.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_candidate_object(
    group_admin_user, public_candidate_object
):
    accessible = public_candidate_object.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_source_object(
    group_admin_user, public_source_object
):
    accessible = public_source_object.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_keck1_telescope(group_admin_user, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_sedm(group_admin_user, sedm):
    accessible = sedm.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_group_sedm_allocation(
    group_admin_user, public_group_sedm_allocation
):
    accessible = public_group_sedm_allocation.is_accessible_by(
        group_admin_user, mode="read"
    )
    assert accessible == accessible


def test_group_admin_user_read_public_group_taxonomy(
    group_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_taxonomy(group_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_comment(group_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_groupcomment(
    group_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_annotation(group_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_groupannotation(
    group_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_classification(
    group_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_groupclassification(
    group_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        group_admin_user, mode="read"
    )
    assert accessible == accessible


def test_group_admin_user_read_public_source_photometry_point(
    group_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        group_admin_user, mode="read"
    )
    assert accessible == accessible


def test_group_admin_user_read_public_source_spectrum(
    group_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_source_groupphotometry(
    group_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        group_admin_user, mode="read"
    )
    assert accessible == accessible


def test_group_admin_user_read_public_source_groupspectrum(
    group_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        group_admin_user, mode="read"
    )
    assert accessible == accessible


def test_group_admin_user_read_public_source_followuprequest(
    group_admin_user, public_source_followuprequest
):
    accessible = public_source_followuprequest.is_accessible_by(
        group_admin_user, mode="read"
    )
    assert accessible == accessible


def test_group_admin_user_read_public_source_followup_request_target_group(
    group_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        group_admin_user, mode="read"
    )
    assert accessible == accessible


def test_group_admin_user_read_public_thumbnail(group_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_red_transients_run(group_admin_user, red_transients_run):
    accessible = red_transients_run.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_problematic_assignment(
    group_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_invitation(group_admin_user, invitation):
    accessible = invitation.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_user_notification(group_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_gcn(group_admin_user, gcn):
    accessible = gcn.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_read_public_comment_on_gcn(
    group_admin_user, public_comment_on_gcn
):
    accessible = public_comment_on_gcn.is_accessible_by(group_admin_user, mode="read")
    assert accessible == accessible


def test_group_admin_user_update_public_group(group_admin_user, public_group):
    accessible = public_group.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_public_groupuser(group_admin_user, public_groupuser):
    accessible = public_groupuser.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_public_stream(group_admin_user, public_stream):
    accessible = public_stream.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_public_groupstream(
    group_admin_user, public_groupstream
):
    accessible = public_groupstream.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_public_streamuser(group_admin_user, public_streamuser):
    accessible = public_streamuser.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_public_filter(group_admin_user, public_filter):
    accessible = public_filter.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_public_candidate_object(
    group_admin_user, public_candidate_object
):
    accessible = public_candidate_object.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible == accessible


def test_group_admin_user_update_public_source_object(
    group_admin_user, public_source_object
):
    accessible = public_source_object.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_keck1_telescope(group_admin_user, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_sedm(group_admin_user, sedm):
    accessible = sedm.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_public_group_sedm_allocation(
    group_admin_user, public_group_sedm_allocation
):
    accessible = public_group_sedm_allocation.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible == accessible


def test_group_admin_user_update_public_group_taxonomy(
    group_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_public_taxonomy(group_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_public_comment(group_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_public_groupcomment(
    group_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_public_annotation(group_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_public_groupannotation(
    group_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible == accessible


def test_group_admin_user_update_public_classification(
    group_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_public_groupclassification(
    group_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible == accessible


def test_group_admin_user_update_public_source_photometry_point(
    group_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible == accessible


def test_group_admin_user_update_public_source_spectrum(
    group_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible == accessible


def test_group_admin_user_update_public_source_groupphotometry(
    group_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible == accessible


def test_group_admin_user_update_public_source_groupspectrum(
    group_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible == accessible


def test_group_admin_user_update_public_source_followuprequest(
    group_admin_user, public_source_followuprequest
):
    accessible = public_source_followuprequest.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible == accessible


def test_group_admin_user_update_public_source_followup_request_target_group(
    group_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible == accessible


def test_group_admin_user_update_public_thumbnail(group_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_red_transients_run(
    group_admin_user, red_transients_run
):
    accessible = red_transients_run.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_problematic_assignment(
    group_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible == accessible


def test_group_admin_user_update_invitation(group_admin_user, invitation):
    accessible = invitation.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_user_notification(group_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_gcn(group_admin_user, gcn):
    accessible = gcn.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_update_public_comment_on_gcn(
    group_admin_user, public_comment_on_gcn
):
    accessible = public_comment_on_gcn.is_accessible_by(group_admin_user, mode="update")
    assert accessible == accessible


def test_group_admin_user_delete_public_group(group_admin_user, public_group):
    accessible = public_group.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_public_groupuser(group_admin_user, public_groupuser):
    accessible = public_groupuser.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_public_stream(group_admin_user, public_stream):
    accessible = public_stream.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_public_groupstream(
    group_admin_user, public_groupstream
):
    accessible = public_groupstream.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_public_streamuser(group_admin_user, public_streamuser):
    accessible = public_streamuser.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_public_filter(group_admin_user, public_filter):
    accessible = public_filter.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_public_candidate_object(
    group_admin_user, public_candidate_object
):
    accessible = public_candidate_object.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_group_admin_user_delete_public_source_object(
    group_admin_user, public_source_object
):
    accessible = public_source_object.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_keck1_telescope(group_admin_user, keck1_telescope):
    accessible = keck1_telescope.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_sedm(group_admin_user, sedm):
    accessible = sedm.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_public_group_sedm_allocation(
    group_admin_user, public_group_sedm_allocation
):
    accessible = public_group_sedm_allocation.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_group_admin_user_delete_public_group_taxonomy(
    group_admin_user, public_group_taxonomy
):
    accessible = public_group_taxonomy.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_public_taxonomy(group_admin_user, public_taxonomy):
    accessible = public_taxonomy.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_public_comment(group_admin_user, public_comment):
    accessible = public_comment.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_public_groupcomment(
    group_admin_user, public_groupcomment
):
    accessible = public_groupcomment.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_public_annotation(group_admin_user, public_annotation):
    accessible = public_annotation.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_public_groupannotation(
    group_admin_user, public_groupannotation
):
    accessible = public_groupannotation.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_group_admin_user_delete_public_classification(
    group_admin_user, public_classification
):
    accessible = public_classification.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_public_groupclassification(
    group_admin_user, public_groupclassification
):
    accessible = public_groupclassification.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_group_admin_user_delete_public_source_photometry_point(
    group_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_group_admin_user_delete_public_source_spectrum(
    group_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_group_admin_user_delete_public_source_groupphotometry(
    group_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_group_admin_user_delete_public_source_groupspectrum(
    group_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_group_admin_user_delete_public_source_followuprequest(
    group_admin_user, public_source_followuprequest
):
    accessible = public_source_followuprequest.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_group_admin_user_delete_public_source_followup_request_target_group(
    group_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_group_admin_user_delete_public_thumbnail(group_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_red_transients_run(
    group_admin_user, red_transients_run
):
    accessible = red_transients_run.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_problematic_assignment(
    group_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible == accessible


def test_group_admin_user_delete_invitation(group_admin_user, invitation):
    accessible = invitation.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_user_notification(group_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_gcn(group_admin_user, gcn):
    accessible = gcn.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible


def test_group_admin_user_delete_public_comment_on_gcn(
    group_admin_user, public_comment_on_gcn
):
    accessible = public_comment_on_gcn.is_accessible_by(group_admin_user, mode="delete")
    assert accessible == accessible
