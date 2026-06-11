from fastapi import APIRouter, HTTPException, Query

from ..schemas import RepLookupOut
from ..services import congress

router = APIRouter(prefix="/api/reps", tags=["representatives"])


@router.get("/lookup", response_model=RepLookupOut)
def lookup(zip: str = Query(min_length=5, max_length=10)):
    result = congress.lookup_zip(zip)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No congressional district found for zip {zip}")
    state, districts, reps = result
    return RepLookupOut(zip=zip[:5], state=state, districts=districts, representatives=reps)
