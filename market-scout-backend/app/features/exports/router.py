from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.features.auth.dependencies import get_current_user
from app.features.businesses.dependencies import business_filters
from app.features.businesses.schemas import BusinessSort, SortDirection
from app.features.businesses.service import BusinessFilters
from app.features.exports import service

router = APIRouter()


@router.get("/leads.csv")
def export_leads_csv(
    filters: BusinessFilters = Depends(business_filters),
    sort: Optional[BusinessSort] = Query(None),
    direction: Optional[SortDirection] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """The leads matching the same filters as the list, as a CSV. Do-not-contact is excluded."""
    file, count = service.write_leads_csv(db, filters, sort=sort, direction=direction)
    return StreamingResponse(
        service.iter_file(file),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="market-scout-leads-{date.today().isoformat()}.csv"',
            "X-Row-Count": str(count),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Row-Count",
        },
    )
