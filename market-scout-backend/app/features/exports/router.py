from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.features.auth.dependencies import get_current_user
from app.features.businesses.dependencies import business_filters
from app.features.businesses.schemas import BusinessSort, SortDirection
from app.features.businesses.service import BusinessFilters
from app.features.exports import crm, service
from app.features.exports.crm import CrmLayout

router = APIRouter()

CSV_MEDIA_TYPE = "text/csv; charset=utf-8"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _download(file, count: int, media_type: str, extension: str, name: str = "leads") -> StreamingResponse:
    return StreamingResponse(
        service.iter_file(file),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="market-scout-{name}-{date.today().isoformat()}.{extension}"',
            "X-Row-Count": str(count),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Row-Count",
        },
    )


@router.get("/leads.csv")
def export_leads_csv(
    filters: BusinessFilters = Depends(business_filters),
    sort: Optional[BusinessSort] = Query(None),
    direction: Optional[SortDirection] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    file, count = service.write_leads_csv(db, filters, sort=sort, direction=direction)
    return _download(file, count, CSV_MEDIA_TYPE, "csv")


@router.get("/leads.xlsx")
def export_leads_xlsx(
    filters: BusinessFilters = Depends(business_filters),
    sort: Optional[BusinessSort] = Query(None),
    direction: Optional[SortDirection] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    file, count = service.write_leads_xlsx(db, filters, sort=sort, direction=direction)
    return _download(file, count, XLSX_MEDIA_TYPE, "xlsx")


@router.get("/crm.csv")
def export_crm_csv(
    layout: CrmLayout = Query(CrmLayout.GENERIC),
    filters: BusinessFilters = Depends(business_filters),
    sort: Optional[BusinessSort] = Query(None),
    direction: Optional[SortDirection] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    file, count = crm.write_crm_csv(db, filters, layout, sort=sort, direction=direction)
    return _download(file, count, CSV_MEDIA_TYPE, "csv", name=f"{layout.value}")
