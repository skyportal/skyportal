"""The acknowledgment block must name what a source actually used.

`assemble_text` is the part with judgement in it, and it is pure, so it is
tested directly against the shapes `build_acknowledgment` produces.
"""

from skyportal.utils.acknowledgment import assemble_text

SITE = "This work made use of the Fritz instance of SkyPortal (Coughlin et al. 2023)."


def test_site_only_when_nothing_else_is_known():
    # A source with no photometry, filters or follow-up still cites the instance.
    assert assemble_text(SITE, [], [], []) == SITE


def test_missing_site_does_not_leave_a_leading_space():
    text = assemble_text(
        "", [], [{"instrument": "SEDM", "telescope": "P60", "acknowledgment": None}], []
    )
    assert text == "Data were obtained with SEDM on the P60."


def test_filter_and_broker_are_named():
    text = assemble_text(SITE, [{"filter": "RCF Deep", "broker": "BOOM"}], [], [])
    assert 'selected by the "RCF Deep" filter on the BOOM broker.' in text


def test_multiple_filters_pluralize():
    text = assemble_text(
        SITE,
        [{"filter": "b", "broker": None}, {"filter": "a", "broker": None}],
        [],
        [],
    )
    # Sorted, so the sentence is stable rather than dependent on query order.
    assert '"a", "b" filters.' in text


def test_a_facility_sentence_is_used_verbatim():
    described = "Based on observations obtained with SEDM on the Palomar 60-inch"
    text = assemble_text(
        SITE,
        [],
        [
            {"instrument": "SEDM", "telescope": "P60", "acknowledgment": described},
            {"instrument": "ZTF-Cam", "telescope": "P48", "acknowledgment": None},
        ],
        [],
    )
    # The described facility keeps its own wording; the other is just named.
    assert described + "." in text
    assert "Data were obtained with ZTF-Cam on the P48." in text
    assert "SEDM on the P60" not in text


def test_programs_are_credited():
    text = assemble_text(
        SITE,
        [],
        [],
        [{"proposal_id": "2026A-001", "pi": "Kasliwal", "instrument": "SEDM"}],
    )
    assert "under proposal 2026A-001 (PI: Kasliwal)." in text


def test_a_program_with_only_a_pi_still_reads():
    text = assemble_text(
        SITE, [], [], [{"proposal_id": None, "pi": "Coughlin", "instrument": "X"}]
    )
    assert "Observations were carried out (PI: Coughlin)." in text


def test_sentences_are_terminated_once():
    text = assemble_text(
        "Already punctuated.", [{"filter": "f", "broker": None}], [], []
    )
    assert ".." not in text


def test_selecting_one_filter_drops_the_rest():
    """An object routinely passes many filters; a paper cites the one it used."""
    everything = [
        {"id": 1, "filter": "RCF Deep", "broker": "BOOM"},
        {"id": 2, "filter": "lions-ztf", "broker": "BOOM"},
        {"id": 3, "filter": "nearby_cluster", "broker": "BOOM"},
    ]
    all_text = assemble_text(SITE, everything, [], [])
    assert "lions-ztf" in all_text and "nearby_cluster" in all_text

    one = [f for f in everything if f["id"] == 1]
    text = assemble_text(SITE, one, [], [])
    assert 'selected by the "RCF Deep" filter on the BOOM broker.' in text
    assert "lions-ztf" not in text
    assert "nearby_cluster" not in text
    # One filter must not be described in the plural.
    assert "filters" not in text


def test_deselecting_everything_leaves_the_site_sentence():
    assert assemble_text(SITE, [], [], []) == SITE
