"""Member-of-Congress lookup by zip code.

Data sources (both public domain, cached on disk after first download):
  * legislators-current.json  — the @unitedstates project; every sitting member
    with phone, contact form, office address, etc.
  * zccd.csv                  — OpenSourceActivismTech zip -> congressional
    district mapping (a zip can span multiple districts).

If the machine has no network access we fall back to a small bundled sample
so the app can still be demoed end to end.
"""
from __future__ import annotations

import csv
import io
import json
import logging
from collections import defaultdict

import httpx

from ..config import DATA_DIR, LEGISLATORS_URL, ZCCD_URL
from ..schemas import Representative

log = logging.getLogger(__name__)

_LEGISLATORS_FILE = DATA_DIR / "legislators-current.json"
_ZCCD_FILE = DATA_DIR / "zccd.csv"

# zip -> [(state, district), ...]
_zip_districts: dict[str, list[tuple[str, int]]] = {}
# (state, district) -> Representative ; senators under (state, None)
_house: dict[tuple[str, int], Representative] = {}
_senate: dict[str, list[Representative]] = defaultdict(list)
_by_bioguide: dict[str, Representative] = {}

# Minimal fallback dataset (used only when the public datasets can't be fetched).
_FALLBACK_ZIPS = {
    "20001": [("DC", 0)],
    "94102": [("CA", 11)],
    "10001": [("NY", 12)],
    "78701": [("TX", 37)],
    "02139": [("MA", 7)],
}
_FALLBACK_MEMBERS = [
    {"bioguide_id": "SAMPLE-S1", "name": "Jane Sample", "role": "senator", "party": "Independent",
     "state": "CA", "district": None, "phone": "202-224-0001",
     "contact_form_url": "https://www.senate.gov", "website": "https://www.senate.gov",
     "office_address": "100 Senate Office Building, Washington DC 20510"},
    {"bioguide_id": "SAMPLE-S2", "name": "John Placeholder", "role": "senator", "party": "Independent",
     "state": "CA", "district": None, "phone": "202-224-0002",
     "contact_form_url": "https://www.senate.gov", "website": "https://www.senate.gov",
     "office_address": "200 Senate Office Building, Washington DC 20510"},
    {"bioguide_id": "SAMPLE-H1", "name": "Alex Example", "role": "representative", "party": "Independent",
     "state": "CA", "district": 11, "phone": "202-225-0001",
     "contact_form_url": "https://www.house.gov", "website": "https://www.house.gov",
     "office_address": "100 House Office Building, Washington DC 20515"},
]


def _download(url: str, dest) -> str | None:
    try:
        resp = httpx.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return resp.text
    except Exception as exc:  # network-restricted environments are expected
        log.warning("Could not download %s: %s", url, exc)
        return None


def _load_legislators(raw: str) -> None:
    members = json.loads(raw)
    for m in members:
        term = m["terms"][-1]
        if term["type"] not in ("rep", "sen"):
            continue
        role = "senator" if term["type"] == "sen" else "representative"
        bioguide = m["id"].get("bioguide", "")
        rep = Representative(
            bioguide_id=bioguide,
            name=m["name"].get("official_full")
            or f"{m['name'].get('first', '')} {m['name'].get('last', '')}".strip(),
            role=role,
            party=term.get("party"),
            state=term["state"],
            district=term.get("district") if role == "representative" else None,
            phone=term.get("phone"),
            contact_form_url=term.get("contact_form"),
            website=term.get("url"),
            office_address=term.get("address"),
            photo_url=(
                f"https://unitedstates.github.io/images/congress/450x550/{bioguide}.jpg"
                if bioguide else None
            ),
        )
        _by_bioguide[rep.bioguide_id] = rep
        if role == "senator":
            _senate[rep.state].append(rep)
        else:
            _house[(rep.state, rep.district or 0)] = rep


def _load_zccd(raw: str) -> None:
    reader = csv.DictReader(io.StringIO(raw))
    for row in reader:
        zcta = row["zcta"].strip().zfill(5)
        try:
            district = int(row["cd"])
        except ValueError:
            continue
        _zip_districts.setdefault(zcta, []).append((row["state_abbr"].strip(), district))


def _load_fallback() -> None:
    _zip_districts.update(_FALLBACK_ZIPS)
    for m in _FALLBACK_MEMBERS:
        rep = Representative(**m)
        _by_bioguide[rep.bioguide_id] = rep
        if rep.role == "senator":
            _senate[rep.state].append(rep)
        else:
            _house[(rep.state, rep.district or 0)] = rep


def load_data() -> None:
    """Called once at startup. Uses cached files when present."""
    leg_raw = _LEGISLATORS_FILE.read_text() if _LEGISLATORS_FILE.exists() else _download(
        LEGISLATORS_URL, _LEGISLATORS_FILE
    )
    zccd_raw = _ZCCD_FILE.read_text() if _ZCCD_FILE.exists() else _download(ZCCD_URL, _ZCCD_FILE)

    if leg_raw and zccd_raw:
        _load_legislators(leg_raw)
        _load_zccd(zccd_raw)
        log.info(
            "Loaded %d members across %d zips", len(_by_bioguide), len(_zip_districts)
        )
    else:
        log.warning("Falling back to bundled sample congressional data")
        _load_fallback()


def lookup_zip(zip_code: str) -> tuple[str, list[int], list[Representative]] | None:
    """Return (state, districts, members) for a 5-digit zip, or None if unknown."""
    pairs = _zip_districts.get(zip_code[:5].zfill(5))
    if not pairs:
        return None
    state = pairs[0][0]
    districts = sorted({d for _, d in pairs})
    reps: list[Representative] = list(_senate.get(state, []))
    for st, district in pairs:
        member = _house.get((st, district))
        if member and member not in reps:
            reps.append(member)
    return state, districts, reps


def get_member(bioguide_id: str) -> Representative | None:
    return _by_bioguide.get(bioguide_id)
