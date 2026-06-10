from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Candidate
from ..schemas import CandidateOut, VoterRegistrationOut

router = APIRouter(prefix="/api", tags=["actions"])

# vote.gov state slugs for register/check links.
_STATE_SLUGS = {
    "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas",
    "CA": "california", "CO": "colorado", "CT": "connecticut", "DE": "delaware",
    "DC": "district-of-columbia", "FL": "florida", "GA": "georgia", "HI": "hawaii",
    "ID": "idaho", "IL": "illinois", "IN": "indiana", "IA": "iowa",
    "KS": "kansas", "KY": "kentucky", "LA": "louisiana", "ME": "maine",
    "MD": "maryland", "MA": "massachusetts", "MI": "michigan", "MN": "minnesota",
    "MS": "mississippi", "MO": "missouri", "MT": "montana", "NE": "nebraska",
    "NV": "nevada", "NH": "new-hampshire", "NJ": "new-jersey", "NM": "new-mexico",
    "NY": "new-york", "NC": "north-carolina", "ND": "north-dakota", "OH": "ohio",
    "OK": "oklahoma", "OR": "oregon", "PA": "pennsylvania", "RI": "rhode-island",
    "SC": "south-carolina", "SD": "south-dakota", "TN": "tennessee", "TX": "texas",
    "UT": "utah", "VT": "vermont", "VA": "virginia", "WA": "washington",
    "WV": "west-virginia", "WI": "wisconsin", "WY": "wyoming",
}


@router.get("/candidates", response_model=list[CandidateOut])
def candidates(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Candidate).where(Candidate.active.is_(True)).order_by(Candidate.state, Candidate.name)
    )
    return list(rows)


@router.get("/actions/voter-registration", response_model=VoterRegistrationOut)
def voter_registration(state: str = Query(min_length=2, max_length=2)):
    state = state.upper()
    slug = _STATE_SLUGS.get(state)
    register_url = f"https://vote.gov/register/{slug}" if slug else "https://vote.gov/register"
    return VoterRegistrationOut(
        state=state,
        register_url=register_url,
        check_url="https://www.nass.org/can-i-vote/voter-registration-status",
        note="Registration deadlines vary by state — check early before an election.",
    )
