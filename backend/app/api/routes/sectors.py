"""Sector/theme ranking endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.sector import SectorListResponse
from app.services import queries

router = APIRouter()


@router.get("/sectors", response_model=SectorListResponse)
def read_sectors(db: Session = Depends(get_db)) -> SectorListResponse:
    return queries.get_sectors(db)
