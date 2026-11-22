import re

import requests

ADS_SEARCH = "https://api.adsabs.harvard.edu/v1/search/query"
ADS_DESIGNATIONS_PER_QUERY = 20
ADS_PAGE_SIZE = 500
ADS_MATCHES_PER_SOURCE = 30
ARXIV_ID = re.compile(r"arxiv:((?:\d{4}\.\d{4,5}|[a-z.-]+/\d{7}))(?:v\d+)?", re.I)


def paper_corner_enabled(cfg):
    return bool(cfg.get("paper_corner.ads_token"))


def designation_patterns(designation):
    words = re.findall(r"[^\W_]+", designation)
    phrases = [designation]
    names = [words]
    if tns := re.fullmatch(r"(AT|SN)[\s-]*(\d{4}[a-z]+)", designation, re.I):
        prefix, stem = tns.groups()
        # TNS may reclassify an AT as an SN after papers have used its AT name.
        names = [[prefix, stem], ["SN" if prefix.upper() == "AT" else "AT", stem]]
    for name in names:
        phrases.extend((" ".join(name), "".join(name)))
    patterns = []
    for name in names:
        parts = r"[\s-]*".join(map(re.escape, name))
        patterns.append(
            (" ".join(name), re.compile(rf"(?<![^\W_]){parts}(?![^\W_])", re.I))
        )
    return phrases, patterns


def paper_metadata(record):
    bibcode = record["bibcode"]
    arxiv_id = next(
        (
            match[1]
            for value in record.get("identifier", [])
            if (match := ARXIV_ID.fullmatch(value))
        ),
        None,
    )
    keys = [f"ads:{value}" for value in [bibcode, *record.get("alternate_bibcode", [])]]
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
    return {
        "bibcode": bibcode,
        "keys": keys,
        "arxiv_id": arxiv_id,
        "title": record["title"][0],
        "first_author": record.get("first_author"),
        "date": date,
    }


class ADSRequestLimit(Exception):
    pass


class ADSClient:
    def __init__(self, token, max_requests):
        self.token = token
        self.remaining = max_requests
        self.resume_at = 0

    def _page(self, query, offset):
        if self.remaining <= 0:
            raise ADSRequestLimit
        self.remaining -= 1
        response = requests.get(
            ADS_SEARCH,
            headers={"Authorization": f"Bearer {self.token}"},
            params={
                "q": query,
                "fl": "bibcode,alternate_bibcode,doi,identifier,title,first_author,pubdate,abstract",
                "rows": ADS_PAGE_SIZE,
                "sort": "date desc,bibcode desc",
                "start": offset,
            },
            timeout=20,
        )
        quota = response.headers.get("X-RateLimit-Remaining", "")
        if quota.isdecimal():
            self.remaining = min(self.remaining, int(quota))
        if quota == "0" or response.status_code == 429:
            self.remaining = 0
            reset = response.headers.get("X-RateLimit-Reset", "")
            if reset.isdecimal():
                self.resume_at = int(reset)
        if response.status_code == 429:
            raise ADSRequestLimit
        response.raise_for_status()
        return response.json()["response"]

    def search(self, designations):
        matches = {designation: [] for designation in designations}
        if not matches:
            return matches

        phrases = {}
        patterns = {}
        for designation in matches:
            variants, patterns[designation] = designation_patterns(designation)
            phrases.update(dict.fromkeys(variants))
        quoted = [
            phrase.replace("\\", "\\\\").replace('"', '\\"') for phrase in phrases
        ]
        query = " OR ".join(f'abs:"{phrase}"' for phrase in quoted)
        query = f"({query}) AND database:astronomy"

        offset = 0
        seen = set()
        while patterns:
            page = self._page(query, offset)
            docs = page["docs"]
            for record in docs:
                if not record.get("title") or record["bibcode"] in seen:
                    continue
                seen.add(record["bibcode"])
                fields = [*record["title"], record.get("abstract") or ""]
                for designation, aliases in list(patterns.items()):
                    labels = [
                        label
                        for label, pattern in aliases
                        if any(pattern.search(field) for field in fields)
                    ]
                    if labels:
                        matches[designation].append(
                            {**paper_metadata(record), "designations": labels}
                        )
                        if len(matches[designation]) == ADS_MATCHES_PER_SOURCE:
                            del patterns[designation]
            offset += len(docs)
            if offset >= page["numFound"]:
                break
            if not docs:
                raise ValueError("ADS returned an incomplete search page")
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
