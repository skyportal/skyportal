import re

import requests

ADS_SEARCH = "https://api.adsabs.harvard.edu/v1/search/query"
ARXIV_ID = re.compile(r"arxiv:((?:\d{4}\.\d{4,5}|[a-z.-]+/\d{7}))(?:v\d+)?", re.I)


def paper_corner_enabled(cfg):
    return bool(cfg.get("paper_corner.ads_token"))


def search_ads(designation, token):
    words = re.findall(r"[^\W_]+", designation)
    if not words:
        return []
    phrases = [designation]
    names = [words]
    if tns := re.fullmatch(r"(AT|SN)[\s-]*(\d{4}[a-z]+)", designation, re.I):
        prefix, stem = tns.groups()
        # TNS may reclassify an AT as an SN after papers have used its AT name.
        names = [[prefix, stem], ["SN" if prefix.upper() == "AT" else "AT", stem]]
    for name in names:
        phrases.extend((" ".join(name), "".join(name)))
    phrases = dict.fromkeys(phrases)
    quoted = [phrase.replace("\\", "\\\\").replace('"', '\\"') for phrase in phrases]
    query = " OR ".join(f'abs:"{phrase}"' for phrase in quoted)
    response = requests.get(
        ADS_SEARCH,
        headers={"Authorization": f"Bearer {token}"},
        params={
            "q": f"({query}) AND database:astronomy",
            "fl": "bibcode,alternate_bibcode,doi,identifier,title,first_author,pubdate,abstract",
            "rows": 30,
            "sort": "date desc",
        },
        timeout=20,
    )
    response.raise_for_status()
    # Transient names are commonly written with or without spaces or hyphens.
    patterns = []
    for name in names:
        parts = r"[\s-]*".join(map(re.escape, name))
        patterns.append(
            (" ".join(name), re.compile(rf"(?<![^\W_]){parts}(?![^\W_])", re.I))
        )
    matches = []
    for record in response.json()["response"]["docs"]:
        titles = record.get("title") or []
        if not titles:
            continue
        fields = [*titles, record.get("abstract") or ""]
        designations = [
            label
            for label, pattern in patterns
            if any(pattern.search(field) for field in fields)
        ]
        if not designations:
            continue
        bibcode = record["bibcode"]
        arxiv_id = next(
            (
                match[1]
                for value in record.get("identifier", [])
                if (match := ARXIV_ID.fullmatch(value))
            ),
            None,
        )
        keys = [
            f"ads:{value}" for value in [bibcode, *record.get("alternate_bibcode", [])]
        ]
        keys.extend(f"doi:{value.lower()}" for value in record.get("doi", []))
        if arxiv_id:
            keys.append(f"arxiv:{arxiv_id.lower()}")
        date = record.get("pubdate") or None
        if date:
            date = date.removesuffix("-00").removesuffix("-00")
        # The identifier encodes the first submission month even if ADS has
        # replaced the preprint record with the journal version.
        if arxiv_id:
            year_month = arxiv_id.rsplit("/", 1)[-1][:4]
            year = int(year_month[:2])
            month = f"{(1900 if year >= 91 else 2000) + year:04d}-{year_month[2:4]}"
            if date is None or month < date[:7] or date == month[:4]:
                date = month
        matches.append(
            {
                "bibcode": bibcode,
                "keys": keys,
                "arxiv_id": arxiv_id,
                "title": titles[0],
                "first_author": record.get("first_author"),
                "date": date,
                "designations": designations,
            }
        )
    return matches


def collect_papers(matches, limit):
    groups = {}
    for obj_id, match in matches:
        keys = match["keys"]
        merged = {}
        for key in keys:
            group = groups.get(key)
            if group is not None:
                merged.update(group)
        merged[obj_id, match["bibcode"]] = match
        for record in merged.values():
            for key in record["keys"]:
                groups[key] = merged

    papers = []
    for group in {id(group): group for group in groups.values()}.values():
        records = sorted(
            group.values(),
            key=lambda record: ("arXiv" in record["bibcode"], record["bibcode"]),
        )
        preferred = records[0]
        dates = [record["date"] for record in records if record["date"]]
        date = min(dates, default=None)
        if date and len(date) == 7:
            date = min(
                (value for value in dates if value.startswith(date + "-")), default=date
            )
        sources = {}
        for (obj_id, _), record in group.items():
            sources.setdefault(obj_id, set()).update(record["designations"])
        papers.append(
            {
                "bibcode": preferred["bibcode"],
                "title": preferred["title"],
                "first_author": preferred["first_author"],
                "date": date,
                "arxiv_id": next(
                    (record["arxiv_id"] for record in records if record["arxiv_id"]),
                    None,
                ),
                "sources": [
                    {"id": obj_id, "designations": sorted(designations)}
                    for obj_id, designations in sorted(sources.items())
                ],
            }
        )
    papers.sort(key=lambda paper: (paper["date"] or "", paper["bibcode"]), reverse=True)
    return papers[:limit]
