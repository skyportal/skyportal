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


def test_user_create_public_source_photometry_point(
    user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(user, mode="create")
    assert accessible


def test_user_create_public_source_groupphotometry(user, public_source_groupphotometry):
    accessible = public_source_groupphotometry.is_accessible_by(user, mode="create")
    assert accessible


def test_user_read_public_source_photometry_point(user, public_source_photometry_point):
    accessible = public_source_photometry_point.is_accessible_by(user, mode="read")
    assert accessible


def test_user_read_public_source_groupphotometry(user, public_source_groupphotometry):
    accessible = public_source_groupphotometry.is_accessible_by(user, mode="read")
    assert accessible


def test_user_update_public_source_photometry_point(
    user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(user, mode="update")
    assert not accessible  # only owner can update


def test_user_update_public_source_groupphotometry(user, public_source_groupphotometry):
    accessible = public_source_groupphotometry.is_accessible_by(user, mode="update")
    assert not accessible  # only accessible by group admin


def test_user_delete_public_source_photometry_point(
    user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(user, mode="delete")
    assert not accessible  # only accessible by owner


def test_user_delete_public_source_groupphotometry(user, public_source_groupphotometry):
    accessible = public_source_groupphotometry.is_accessible_by(user, mode="delete")
    assert not accessible  # only accessible by group admin


def test_user_group2_create_public_source_photometry_point(
    user_group2, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        user_group2, mode="create"
    )
    assert accessible


def test_user_group2_create_public_source_groupphotometry(
    user_group2, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        user_group2, mode="create"
    )
    assert not accessible  # need read access to the underlying photometry


def test_user_group2_read_public_source_photometry_point(
    user_group2, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        user_group2, mode="read"
    )
    assert not accessible  # must be a member of one of the photometry's groups


def test_user_group2_read_public_source_groupphotometry(
    user_group2, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        user_group2, mode="read"
    )
    assert not accessible  # must be a member of one of the photometry's groups


def test_user_group2_update_public_source_photometry_point(
    user_group2, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        user_group2, mode="update"
    )
    assert not accessible  # must be photometry owner


def test_user_group2_update_public_source_groupphotometry(
    user_group2, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        user_group2, mode="update"
    )
    assert not accessible  # must be group admin


def test_user_group2_delete_public_source_photometry_point(
    user_group2, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        user_group2, mode="delete"
    )
    assert not accessible  # must be photometry owner


def test_user_group2_delete_public_source_groupphotometry(
    user_group2, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        user_group2, mode="delete"
    )
    assert not accessible  # must be group admin


def test_super_admin_user_create_public_source_photometry_point(
    super_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        super_admin_user, mode="create"
    )

    assert accessible


def test_super_admin_user_create_public_source_groupphotometry(
    super_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible


def test_super_admin_user_read_public_source_photometry_point(
    super_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        super_admin_user, mode="read"
    )
    assert accessible


def test_super_admin_user_read_public_source_groupphotometry(
    super_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        super_admin_user, mode="read"
    )

    assert accessible


def test_super_admin_user_update_public_source_photometry_point(
    super_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible


def test_super_admin_user_update_public_source_groupphotometry(
    super_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        super_admin_user, mode="update"
    )

    assert accessible


def test_super_admin_user_delete_public_source_photometry_point(
    super_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible


def test_super_admin_user_delete_public_source_groupphotometry(
    super_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        super_admin_user, mode="delete"
    )

    assert accessible


def test_group_admin_user_create_public_source_photometry_point(
    group_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible


def test_group_admin_user_create_public_source_groupphotometry(
    group_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible


def test_group_admin_user_read_public_source_photometry_point(
    group_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        group_admin_user, mode="read"
    )
    assert accessible


def test_group_admin_user_read_public_source_groupphotometry(
    group_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        group_admin_user, mode="read"
    )
    assert accessible


def test_group_admin_user_update_public_source_photometry_point(
    group_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert not accessible  # must be photometry owner


def test_group_admin_user_update_public_source_groupphotometry(
    group_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible


def test_group_admin_user_delete_public_source_photometry_point(
    group_admin_user, public_source_photometry_point
):
    accessible = public_source_photometry_point.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert not accessible  # must be photometry owner


def test_group_admin_user_delete_public_source_groupphotometry(
    group_admin_user, public_source_groupphotometry
):
    accessible = public_source_groupphotometry.is_accessible_by(
        group_admin_user, mode="delete"
    )

    assert accessible


def test_user_create_public_source_spectrum(user, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user, mode="create")
    assert accessible


def test_user_create_public_source_groupspectrum(user, public_source_groupspectrum):
    accessible = public_source_groupspectrum.is_accessible_by(user, mode="create")
    assert accessible


def test_user_read_public_source_spectrum(user, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user, mode="read")
    assert accessible


def test_user_read_public_source_groupspectrum(user, public_source_groupspectrum):
    accessible = public_source_groupspectrum.is_accessible_by(user, mode="read")
    assert accessible


def test_user_update_public_source_spectrum(user, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user, mode="update")
    assert not accessible  # only owner can update


def test_user_update_public_source_groupspectrum(user, public_source_groupspectrum):
    accessible = public_source_groupspectrum.is_accessible_by(user, mode="update")
    assert not accessible  # only accessible by group admin


def test_user_delete_public_source_spectrum(user, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user, mode="delete")
    assert not accessible  # only accessible by owner


def test_user_delete_public_source_groupspectrum(user, public_source_groupspectrum):
    accessible = public_source_groupspectrum.is_accessible_by(user, mode="delete")
    assert not accessible  # only accessible by group admin


def test_user_group2_create_public_source_spectrum(user_group2, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user_group2, mode="create")
    assert accessible


def test_user_group2_create_public_source_groupspectrum(
    user_group2, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        user_group2, mode="create"
    )
    assert not accessible  # need read access to the underlying spectrum


def test_user_group2_read_public_source_spectrum(user_group2, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be a member of one of the spectrum's groups


def test_user_group2_read_public_source_groupspectrum(
    user_group2, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be a member of one of the spectrum's groups


def test_user_group2_update_public_source_spectrum(user_group2, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be spectrum owner


def test_user_group2_update_public_source_groupspectrum(
    user_group2, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        user_group2, mode="update"
    )
    assert not accessible  # must be group admin


def test_user_group2_delete_public_source_spectrum(user_group2, public_source_spectrum):
    accessible = public_source_spectrum.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be spectrum owner


def test_user_group2_delete_public_source_groupspectrum(
    user_group2, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        user_group2, mode="delete"
    )
    assert not accessible  # must be group admin


def test_super_admin_user_create_public_source_spectrum(
    super_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(
        super_admin_user, mode="create"
    )

    assert accessible


def test_super_admin_user_create_public_source_groupspectrum(
    super_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible


def test_super_admin_user_read_public_source_spectrum(
    super_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_read_public_source_groupspectrum(
    super_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        super_admin_user, mode="read"
    )

    assert accessible


def test_super_admin_user_update_public_source_spectrum(
    super_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible


def test_super_admin_user_update_public_source_groupspectrum(
    super_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        super_admin_user, mode="update"
    )

    assert accessible


def test_super_admin_user_delete_public_source_spectrum(
    super_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible


def test_super_admin_user_delete_public_source_groupspectrum(
    super_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        super_admin_user, mode="delete"
    )

    assert accessible


def test_group_admin_user_create_public_source_spectrum(
    group_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible


def test_group_admin_user_create_public_source_groupspectrum(
    group_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible


def test_group_admin_user_read_public_source_spectrum(
    group_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_read_public_source_groupspectrum(
    group_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        group_admin_user, mode="read"
    )
    assert accessible


def test_group_admin_user_update_public_source_spectrum(
    group_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert not accessible  # must be spectrum owner


def test_group_admin_user_update_public_source_groupspectrum(
    group_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible


def test_group_admin_user_delete_public_source_spectrum(
    group_admin_user, public_source_spectrum
):
    accessible = public_source_spectrum.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert not accessible  # must be spectrum owner


def test_group_admin_user_delete_public_source_groupspectrum(
    group_admin_user, public_source_groupspectrum
):
    accessible = public_source_groupspectrum.is_accessible_by(
        group_admin_user, mode="delete"
    )

    assert accessible


def test_user_create_public_source_followup_request(
    user, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(user, mode="create")
    assert accessible


def test_user_create_public_source_followup_request_target_group(
    user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user, mode="create"
    )
    assert accessible


def test_user_read_public_source_followup_request(user, public_source_followup_request):
    accessible = public_source_followup_request.is_accessible_by(user, mode="read")
    assert accessible


def test_user_read_public_source_followup_request_target_group(
    user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user, mode="read"
    )
    assert accessible


def test_user_update_public_source_followup_request(
    user, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(user, mode="update")
    assert accessible


def test_user_update_public_source_followup_request_target_group(
    user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user, mode="update"
    )
    assert (
        accessible
        # since this is the user that authored the request, otherwise false
    )


def test_user_delete_public_source_followup_request(
    user, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(user, mode="delete")
    assert accessible


def test_user_delete_public_source_followup_request_target_group(
    user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user, mode="delete"
    )

    assert accessible


def test_user_group2_create_public_source_followup_request(
    user_group2, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(
        user_group2, mode="create"
    )
    assert not accessible  # need access to the allocation


def test_user_group2_create_public_source_followup_request_target_group(
    user_group2, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user_group2, mode="create"
    )
    assert not accessible  # need read access to target group


def test_user_group2_read_public_source_followup_request(
    user_group2, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(
        user_group2, mode="read"
    )
    assert not accessible  # not in the allocation's group


def test_user_group2_read_public_source_followup_request_target_group(
    user_group2, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user_group2, mode="read"
    )
    assert not accessible  # need to be able to read the followup request


def test_user_group2_update_public_source_followup_request(
    user_group2, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(
        user_group2, mode="update"
    )
    assert not accessible  # must be in allocation group


def test_user_group2_update_public_source_followup_request_target_group(
    user_group2, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user_group2, mode="update"
    )
    assert not accessible  # must be followup request requester


def test_user_group2_delete_public_source_followup_request(
    user_group2, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(
        user_group2, mode="delete"
    )
    assert not accessible  # must be in allocation group


def test_user_group2_delete_public_source_followup_request_target_group(
    user_group2, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        user_group2, mode="delete"
    )
    assert not accessible  # must be followup request requester


def test_super_admin_user_create_public_source_followup_request(
    super_admin_user, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible


def test_super_admin_user_create_public_source_followup_request_target_group(
    super_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible


def test_super_admin_user_read_public_source_followup_request(
    super_admin_user, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(
        super_admin_user, mode="read"
    )
    assert accessible


def test_super_admin_user_read_public_source_followup_request_target_group(
    super_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        super_admin_user, mode="read"
    )
    assert accessible


def test_super_admin_user_update_public_source_followup_request(
    super_admin_user, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible


def test_super_admin_user_update_public_source_followup_request_target_group(
    super_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible


def test_super_admin_user_delete_public_source_followup_request(
    super_admin_user, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible


def test_super_admin_user_delete_public_source_followup_request_target_group(
    super_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible


def test_group_admin_user_create_public_source_followup_request(
    group_admin_user, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible


def test_group_admin_user_create_public_source_followup_request_target_group(
    group_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert not accessible  # must be followup request requester


def test_group_admin_user_read_public_source_followup_request(
    group_admin_user, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(
        group_admin_user, mode="read"
    )
    assert accessible


def test_group_admin_user_read_public_source_followup_request_target_group(
    group_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        group_admin_user, mode="read"
    )
    assert accessible


def test_group_admin_user_update_public_source_followup_request(
    group_admin_user, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible


def test_group_admin_user_update_public_source_followup_request_target_group(
    group_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert not accessible  # must be requester


def test_group_admin_user_delete_public_source_followup_request(
    group_admin_user, public_source_followup_request
):
    accessible = public_source_followup_request.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible


def test_group_admin_user_delete_public_source_followup_request_target_group(
    group_admin_user, public_source_followup_request_target_group
):
    accessible = public_source_followup_request_target_group.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert not accessible  # must be requester


def test_user_create_public_thumbnail(user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user, mode="create")
    assert accessible


def test_user_read_public_thumbnail(user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user, mode="read")
    assert accessible


def test_user_update_public_thumbnail(user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user, mode="update")
    assert not accessible  # restricted


def test_user_delete_public_thumbnail(user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user, mode="delete")
    assert not accessible  # restricted


def test_user_group2_create_public_thumbnail(user_group2, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user_group2, mode="create")
    assert accessible


def test_user_group2_read_public_thumbnail(user_group2, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user_group2, mode="read")
    assert accessible


def test_user_group2_update_public_thumbnail(user_group2, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user_group2, mode="update")
    assert not accessible  # restricted


def test_user_group2_delete_public_thumbnail(user_group2, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(user_group2, mode="delete")
    assert not accessible


def test_super_admin_user_create_public_thumbnail(super_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_read_public_thumbnail(super_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_update_public_thumbnail(super_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_delete_public_thumbnail(super_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_group_admin_user_create_public_thumbnail(group_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_read_public_thumbnail(group_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_update_public_thumbnail(group_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(group_admin_user, mode="update")
    assert not accessible  # need sysadmin


def test_group_admin_user_delete_public_thumbnail(group_admin_user, public_thumbnail):
    accessible = public_thumbnail.is_accessible_by(group_admin_user, mode="delete")
    assert not accessible  # need sysadmin


def test_user_create_red_transients_run(user, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user, mode="create")
    assert accessible


def test_user_read_red_transients_run(user, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user, mode="read")
    assert accessible


def test_user_update_red_transients_run(user, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user, mode="update")
    assert accessible


def test_user_delete_red_transients_run(user, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user, mode="delete")
    assert accessible


def test_user_group2_create_red_transients_run(user_group2, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user_group2, mode="create")
    assert accessible


def test_user_group2_read_red_transients_run(user_group2, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user_group2, mode="read")
    assert accessible


def test_user_group2_update_red_transients_run(user_group2, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be owner


def test_user_group2_delete_red_transients_run(user_group2, red_transients_run):
    accessible = red_transients_run.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be owner


def test_super_admin_user_create_red_transients_run(
    super_admin_user, red_transients_run
):
    accessible = red_transients_run.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_read_red_transients_run(super_admin_user, red_transients_run):
    accessible = red_transients_run.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_update_red_transients_run(
    super_admin_user, red_transients_run
):
    accessible = red_transients_run.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_delete_red_transients_run(
    super_admin_user, red_transients_run
):
    accessible = red_transients_run.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_group_admin_user_create_red_transients_run(
    group_admin_user, red_transients_run
):
    accessible = red_transients_run.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_read_red_transients_run(group_admin_user, red_transients_run):
    accessible = red_transients_run.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_update_red_transients_run(
    group_admin_user, red_transients_run
):
    accessible = red_transients_run.is_accessible_by(group_admin_user, mode="update")
    assert not accessible  # must be owner


def test_group_admin_user_delete_red_transients_run(
    group_admin_user, red_transients_run
):
    accessible = red_transients_run.is_accessible_by(group_admin_user, mode="delete")
    assert not accessible  # must be owner


def test_user_create_problematic_assignment(user, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user, mode="create")
    assert accessible


def test_user_read_problematic_assignment(user, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user, mode="read")
    assert accessible


def test_user_update_problematic_assignment(user, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user, mode="update")
    assert accessible


def test_user_delete_problematic_assignment(user, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user, mode="delete")
    assert accessible


def test_user_group2_create_problematic_assignment(user_group2, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user_group2, mode="create")
    assert accessible


def test_user_group2_read_problematic_assignment(user_group2, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user_group2, mode="read")
    assert accessible


def test_user_group2_update_problematic_assignment(user_group2, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user_group2, mode="update")
    assert accessible


def test_user_group2_delete_problematic_assignment(user_group2, problematic_assignment):
    accessible = problematic_assignment.is_accessible_by(user_group2, mode="delete")
    assert accessible


def test_super_admin_user_create_problematic_assignment(
    super_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(
        super_admin_user, mode="create"
    )
    assert accessible


def test_super_admin_user_read_problematic_assignment(
    super_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_update_problematic_assignment(
    super_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(
        super_admin_user, mode="update"
    )
    assert accessible


def test_super_admin_user_delete_problematic_assignment(
    super_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(
        super_admin_user, mode="delete"
    )
    assert accessible


def test_group_admin_user_create_problematic_assignment(
    group_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(
        group_admin_user, mode="create"
    )
    assert accessible


def test_group_admin_user_read_problematic_assignment(
    group_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(group_admin_user, mode="read")
    assert accessible


def test_group_admin_user_update_problematic_assignment(
    group_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(
        group_admin_user, mode="update"
    )
    assert accessible


def test_group_admin_user_delete_problematic_assignment(
    group_admin_user, problematic_assignment
):
    accessible = problematic_assignment.is_accessible_by(
        group_admin_user, mode="delete"
    )
    assert accessible


# These tests are commented out because they require email / twilio clients
# to be set up, which is not done by default.
"""
def test_user_create_invitation(user, invitation):
    accessible = invitation.is_accessible_by(user, mode="create")
    assert accessible
def test_user_read_invitation(user, invitation):
    accessible = invitation.is_accessible_by(user, mode="read")
    assert accessible
def test_user_update_invitation(user, invitation):
    accessible = invitation.is_accessible_by(user, mode="update")
    assert accessible
def test_user_delete_invitation(user, invitation):
    accessible = invitation.is_accessible_by(user, mode="delete")
    assert accessible
def test_user_group2_create_invitation(user_group2, invitation):
    accessible = invitation.is_accessible_by(user_group2, mode="create")
    assert accessible
def test_user_group2_read_invitation(user_group2, invitation):
    accessible = invitation.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be the inviter
def test_user_group2_update_invitation(user_group2, invitation):
    accessible = invitation.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be the inviter
def test_user_group2_delete_invitation(user_group2, invitation):
    accessible = invitation.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be the inviter
def test_super_admin_user_create_invitation(super_admin_user, invitation):
    accessible = invitation.is_accessible_by(super_admin_user, mode="create")
    assert accessible
def test_super_admin_user_read_invitation(super_admin_user, invitation):
    accessible = invitation.is_accessible_by(super_admin_user, mode="read")
    assert accessible
def test_super_admin_user_update_invitation(super_admin_user, invitation):
    accessible = invitation.is_accessible_by(super_admin_user, mode="update")
    assert accessible
def test_super_admin_user_delete_invitation(super_admin_user, invitation):
    accessible = invitation.is_accessible_by(super_admin_user, mode="delete")
    assert accessible

def test_group_admin_user_create_invitation(group_admin_user, invitation):
    accessible = invitation.is_accessible_by(group_admin_user, mode="create")
    assert accessible
def test_group_admin_user_read_invitation(group_admin_user, invitation):
    accessible = invitation.is_accessible_by(group_admin_user, mode="read")
    assert not accessible  # must be the inviter
def test_group_admin_user_update_invitation(group_admin_user, invitation):
    accessible = invitation.is_accessible_by(group_admin_user, mode="update")
    assert not accessible  # must be the inviter
def test_group_admin_user_delete_invitation(group_admin_user, invitation):
    accessible = invitation.is_accessible_by(group_admin_user, mode="delete")
    assert not accessible  # must be the inviter


def test_user_create_public_source_notification(user, public_source_notification):
    accessible = public_source_notification.is_accessible_by(user, mode="create")
    assert accessible
def test_user_read_public_source_notification(user, public_source_notification):
    accessible = public_source_notification.is_accessible_by(user, mode="read")
    assert accessible
def test_user_update_public_source_notification(user, public_source_notification):
    accessible = public_source_notification.is_accessible_by(user, mode="update")
    assert not accessible  # must be sender
def test_user_delete_public_source_notification(user, public_source_notification):
    accessible = public_source_notification.is_accessible_by(user, mode="delete")
    assert not accessible  # must be sender
def test_user_group2_create_public_source_notification(user_group2, public_source_notification):
    accessible = public_source_notification.is_accessible_by(user_group2, mode="create")
    assert not accessible  # must be member of all target groups
def test_user_group2_read_public_source_notification(user_group2, public_source_notification):
    accessible = public_source_notification.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be a member of at least one target group
def test_user_group2_update_public_source_notification(user_group2, public_source_notification):
    accessible = public_source_notification.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be notification sender
def test_user_group2_delete_public_source_notification(user_group2, public_source_notification):
    accessible = public_source_notification.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be notification sender
def test_super_admin_user_create_public_source_notification(super_admin_user, public_source_notification):
    accessible = public_source_notification.is_accessible_by(super_admin_user, mode="create")
    assert accessible
def test_super_admin_user_read_public_source_notification(super_admin_user, public_source_notification):
    accessible = public_source_notification.is_accessible_by(super_admin_user, mode="read")
    assert accessible
def test_super_admin_user_update_public_source_notification(super_admin_user, public_source_notification):
    accessible = public_source_notification.is_accessible_by(super_admin_user, mode="update")
    assert accessible
def test_super_admin_user_delete_public_source_notification(super_admin_user, public_source_notification):
    accessible = public_source_notification.is_accessible_by(super_admin_user, mode="delete")
    assert accessible
def test_group_admin_user_create_public_source_notification(group_admin_user, public_source_notification):
    accessible = public_source_notification.is_accessible_by(group_admin_user, mode="create")
    assert accessible
def test_group_admin_user_read_public_source_notification(group_admin_user, public_source_notification):
    accessible = public_source_notification.is_accessible_by(group_admin_user, mode="read")
    assert accessible
def test_group_admin_user_update_public_source_notification(group_admin_user, public_source_notification):
    accessible = public_source_notification.is_accessible_by(group_admin_user, mode="update")
    assert accessible  # must be notification sender
def test_group_admin_user_delete_public_source_notification(group_admin_user, public_source_notification):
    accessible = public_source_notification.is_accessible_by(group_admin_user, mode="delete")
    assert accessible  # must be notification sender
"""


def test_user_create_user_notification(user, user_notification):
    accessible = user_notification.is_accessible_by(user, mode="create")
    assert accessible


def test_user_read_user_notification(user, user_notification):
    accessible = user_notification.is_accessible_by(user, mode="read")
    assert accessible


def test_user_update_user_notification(user, user_notification):
    accessible = user_notification.is_accessible_by(user, mode="update")
    assert accessible


def test_user_delete_user_notification(user, user_notification):
    accessible = user_notification.is_accessible_by(user, mode="delete")
    assert accessible


def test_user_group2_create_user_notification(user_group2, user_notification):
    accessible = user_notification.is_accessible_by(user_group2, mode="create")
    assert accessible


def test_user_group2_read_user_notification(user_group2, user_notification):
    accessible = user_notification.is_accessible_by(user_group2, mode="read")
    assert not accessible  # must be target user


def test_user_group2_update_user_notification(user_group2, user_notification):
    accessible = user_notification.is_accessible_by(user_group2, mode="update")
    assert not accessible  # must be target user


def test_user_group2_delete_user_notification(user_group2, user_notification):
    accessible = user_notification.is_accessible_by(user_group2, mode="delete")
    assert not accessible  # must be target user


def test_super_admin_user_create_user_notification(super_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(super_admin_user, mode="create")
    assert accessible


def test_super_admin_user_read_user_notification(super_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(super_admin_user, mode="read")
    assert accessible


def test_super_admin_user_update_user_notification(super_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(super_admin_user, mode="update")
    assert accessible


def test_super_admin_user_delete_user_notification(super_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(super_admin_user, mode="delete")
    assert accessible


def test_group_admin_user_create_user_notification(group_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(group_admin_user, mode="create")
    assert accessible


def test_group_admin_user_read_user_notification(group_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(group_admin_user, mode="read")
    assert not accessible  # must be target user


def test_group_admin_user_update_user_notification(group_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(group_admin_user, mode="update")
    assert not accessible  # must be target user


def test_group_admin_user_delete_user_notification(group_admin_user, user_notification):
    accessible = user_notification.is_accessible_by(group_admin_user, mode="delete")
    assert not accessible  # must be target user
