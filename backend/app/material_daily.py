"""Daily material entry: editable quantities plus immutable change history."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from .database import get_db
from .models import Material, MaterialDailyEntry, MaterialDailyLog, MaterialDocument, MaterialDocumentLine, User
from .schemas import MaterialOut
from .security import require

router = APIRouter(prefix="/api/material-daily", tags=["material-daily"])


class DailyUpdate(BaseModel):
    inbound: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    outbound: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    version: int = Field(ge=0)


def movements(db, material_id=None):
    """Use business dates, excluding drafts and voided documents."""
    stmt = select(MaterialDocumentLine.material_id, MaterialDocument.business_date,
                  MaterialDocument.document_type, func.sum(MaterialDocumentLine.quantity)).join(
        MaterialDocument, MaterialDocument.id == MaterialDocumentLine.document_id
    ).where(MaterialDocument.status == "POSTED")
    if material_id is not None:
        stmt = stmt.where(MaterialDocumentLine.material_id == material_id)
    stmt = stmt.group_by(MaterialDocumentLine.material_id, MaterialDocument.business_date, MaterialDocument.document_type)
    result = defaultdict(lambda: defaultdict(lambda: [Decimal(0), Decimal(0)]))
    for mid, day, kind, qty in db.execute(stmt):
        result[mid][day][1 if kind == "OUTBOUND" else 0] += qty
    return result


def rows(db, business_date, material_id=None):
    stmt = select(Material).order_by(Material.id)
    if material_id is None:
        stmt = stmt.where(Material.is_active.is_(True))
    if material_id is not None:
        stmt = stmt.where(Material.id == material_id)
    materials = db.scalars(stmt).all()
    docs = movements(db, material_id)
    entries_stmt = select(MaterialDailyEntry)
    if material_id is not None:
        entries_stmt = entries_stmt.where(MaterialDailyEntry.material_id == material_id)
    entries = defaultdict(dict)
    for entry in db.scalars(entries_stmt):
        entries[entry.material_id][entry.business_date] = entry
    result = []
    for material in materials:
        daily = entries[material.id]
        document = docs[material.id]
        entry = daily.get(business_date)
        inbound = entry.inbound if entry else Decimal(0)
        outbound = entry.outbound if entry else Decimal(0)
        doc_in, doc_out = document.get(business_date, [Decimal(0), Decimal(0)])
        future = sum((e.inbound - e.outbound for d, e in daily.items() if d > business_date), Decimal(0))
        future += sum((i - o for d, (i, o) in document.items() if d > business_date), Decimal(0))
        closing = material.stock - future
        result.append(dict(material=MaterialOut.model_validate(material), inbound=inbound, outbound=outbound,
                           document_inbound=doc_in, document_outbound=doc_out,
                           opening=closing - inbound + outbound - doc_in + doc_out, closing=closing,
                           version=entry.version if entry else 0))
    return result


@router.get("")
def list_daily(business_date: date, db: Session = Depends(get_db), _: User = Depends(require("material_daily:view"))):
    return {"items": rows(db, business_date)}


@router.put("/{material_id}")
def update_daily(material_id: int, business_date: date, payload: DailyUpdate,
                 db: Session = Depends(get_db), user: User = Depends(require("material_daily:update"))):
    # A write lock also serializes first-entry creation on SQLite; PostgreSQL locks this material row.
    db.execute(update(Material).where(Material.id == material_id).values(stock=Material.stock))
    material = db.scalar(select(Material).where(Material.id == material_id).with_for_update())
    if not material:
        raise HTTPException(404, "原材料不存在")
    if not material.is_active:
        raise HTTPException(400, "原材料已停用")
    entry = db.scalar(select(MaterialDailyEntry).where(MaterialDailyEntry.material_id == material_id,
                                                      MaterialDailyEntry.business_date == business_date))
    if payload.version != (entry.version if entry else 0):
        raise HTTPException(409, "该记录已被其他人修改，请刷新后重试")
    old_in, old_out = (entry.inbound, entry.outbound) if entry else (Decimal(0), Decimal(0))
    if (old_in, old_out) == (payload.inbound, payload.outbound):
        db.rollback()
        return rows(db, business_date, material_id)[0]
    delta = payload.inbound - payload.outbound - old_in + old_out
    if material.stock + delta < 0:
        raise HTTPException(400, "修改后当前库存不足")
    # Preserve opening balance imported before the movement history, then validate all affected days.
    timeline = movements(db, material_id)[material_id]
    for existing in db.scalars(select(MaterialDailyEntry).where(MaterialDailyEntry.material_id == material_id)):
        timeline[existing.business_date][0] += existing.inbound
        timeline[existing.business_date][1] += existing.outbound
    balance = material.stock - sum((i - o for i, o in timeline.values()), Decimal(0))
    timeline[business_date][0] += payload.inbound - old_in
    timeline[business_date][1] += payload.outbound - old_out
    for day, (incoming, outgoing) in sorted(timeline.items()):
        balance += incoming - outgoing
        if day >= business_date and balance < 0:
            raise HTTPException(400, f"修改后 {day} 的结余不足，请先补充入库数量")
    if entry is None:
        entry = MaterialDailyEntry(material_id=material_id, business_date=business_date, version=0)
        db.add(entry)
    entry.inbound, entry.outbound = payload.inbound, payload.outbound
    entry.version += 1
    material.stock += delta
    db.add(MaterialDailyLog(material_id=material_id, material_name=material.name, unit=material.material_unit,
                            business_date=business_date, old_inbound=old_in, old_outbound=old_out,
                            inbound=payload.inbound, outbound=payload.outbound, balance_after=material.stock,
                            created_by=user.id, operator_name=user.name))
    db.commit()
    return rows(db, business_date, material_id)[0]


@router.get("/logs/list")
def list_logs(business_date: date | None = None, material_id: int | None = None,
              date_from: date | None = None, date_to: date | None = None,
              query: str = Query("", max_length=120), page: int = Query(1, ge=1),
              page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db),
              _: User = Depends(require("material_daily_logs:view"))):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(400, "开始日期不能晚于结束日期")
    stmt = select(MaterialDailyLog)
    if business_date is not None:
        stmt = stmt.where(MaterialDailyLog.business_date == business_date)
    if date_from is not None:
        stmt = stmt.where(MaterialDailyLog.business_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(MaterialDailyLog.business_date <= date_to)
    if query.strip():
        stmt = stmt.where(MaterialDailyLog.material_name.contains(query.strip(), autoescape=True))
    if material_id is not None:
        stmt = stmt.where(MaterialDailyLog.material_id == material_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(MaterialDailyLog.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": items, "total": total}
