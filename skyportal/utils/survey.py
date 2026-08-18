import re

OBJECT_ID_PATTERNS = {
    "ZTF": r"ZTF\d{2}[a-z]{7}$",  # ZTF + 2 digits + 7 lowercase characters
    "DECAM": r"[ACT]20\d{6}\d{7}[pm]\d{6}$",  # A or C or T + 20 + 6 digits + 7 digits + p or m + 6 digits
    "LSST": r"LSST-P-DO-\d+$",  # LSST-P-DO- + diaObjectId (int64)
}


def survey_from_object_id(object_id, surveys=None):
    """Survey an object id belongs to, from its shape ("ZTF18abcdefg" -> ZTF, a
    raw numeric diaObjectId -> LSST), or ``None`` when it says nothing (or names
    a survey outside ``surveys``).
    """
    object_id = str(object_id or "").strip()
    if not object_id:
        return None
    survey = next(
        (s for s, regex in OBJECT_ID_PATTERNS.items() if re.match(regex, object_id)),
        "LSST" if object_id.isdigit() else None,
    )
    if surveys is not None and survey not in surveys:
        return None
    return survey
