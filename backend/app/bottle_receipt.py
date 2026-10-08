"""Build an editable receipt from explicitly selected posted records."""
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Annotated

from .config import settings
from .database import get_db
from .models import Bottle, BottleInbound, BottleOutbound, BottleSource, User
from .security import require

router = APIRouter(prefix="/api")


def chinese_date(value: date) -> str:
    return f"{value.year}年{value.month}月{value.day}号"


class ReceiptSelection(BaseModel):
    inbound_ids: list[Annotated[int, Field(gt=0)]] = Field(default_factory=list, max_length=500)
    outbound_ids: list[Annotated[int, Field(gt=0)]] = Field(default_factory=list, max_length=500)


@router.post('/bottle-receipt/preview')
def receipt_preview(payload: ReceiptSelection,
                    _: User = Depends(require('bottle_inbound:export')), db: Session = Depends(get_db)):
    in_ids, out_ids = set(payload.inbound_ids), set(payload.outbound_ids)
    if not in_ids and not out_ids:
        raise HTTPException(400, '请先勾选要导出的入库单或出库单')
    incoming = list(db.scalars(select(BottleInbound).where(BottleInbound.id.in_(in_ids))
                              .order_by(BottleInbound.business_date, BottleInbound.id)))
    outgoing = list(db.scalars(select(BottleOutbound).where(BottleOutbound.id.in_(out_ids))
                              .order_by(BottleOutbound.business_date, BottleOutbound.id)))
    records = incoming + outgoing
    if len(incoming) != len(in_ids) or len(outgoing) != len(out_ids):
        raise HTTPException(404, '部分勾选的单据已不存在，请重新选择')
    if any(row.status != 'POSTED' for row in records):
        raise HTTPException(400, '只能导出已生效的入库单和出库单')
    source_ids = {row.source_id for row in records}
    if len(source_ids) != 1 or None in source_ids:
        raise HTTPException(400, '同一份收发记录只能选择一个客户，且单据必须关联供瓶单位')
    source_id = source_ids.pop()
    source = db.get(BottleSource, source_id)
    if not source:
        raise HTTPException(404, '供瓶单位不存在')
    date_from, date_to = min(row.business_date for row in records), max(row.business_date for row in records)
    inbound_ids = [row.id for row in incoming]
    outbound_ids = [row.id for row in outgoing]
    bottles = list(db.scalars(select(Bottle).where(or_(
        Bottle.inbound_id.in_(inbound_ids), Bottle.outbound_id.in_(outbound_ids),
    )).order_by(Bottle.body_code, Bottle.id)))
    lines = ['液化石油气']
    warnings = ['质量明细采用关联钢瓶当前状态及退还标识；请核对历史批次和未关联瓶号后导出。']
    for row in incoming:
        lines.extend([f'{chinese_date(row.business_date)}收到{source.name}', f'液化石油气瓶共{row.total_quantity}个'])
    for row in outgoing:
        good = sum(item.good_quantity for item in row.lines)
        lines.extend([f'{chinese_date(row.business_date)}出给{source.name}',
                      f'液化石油气瓶共{row.total_quantity}个，其中检验合格的共{good}个（带回）'])
        temporary = sum(item.temporary_quantity for item in row.lines)
        scrap = sum(item.scrap_quantity for item in row.lines)
        if temporary:
            lines.append(f'暂存未检验的共{temporary}个（带回）')
        if scrap:
            lines.append(f'报废共{scrap}个（带回；出库单按数量登记）')
    detail_start = len(lines)
    groups = defaultdict(list)
    resolved = defaultdict(int)
    named_bad_out = defaultdict(int)
    for bottle in bottles:
        is_selected_out = bottle.outbound_id in outbound_ids and bottle.zone == 'OUTBOUND'
        zone = bottle.outbound_origin_zone if bottle.zone == 'OUTBOUND' else bottle.zone
        if zone in {'GOOD', 'BAD', 'SCRAP'} and (bottle.inbound_id in inbound_ids):
            resolved[bottle.spec_id] += 1
        if zone == 'BAD':
            returned = True if is_selected_out else bottle.returned_to_customer
            label = (bottle.inspection_note or '不良品').strip() or '不良品'
            # Keep separate paragraphs even when the stored note contains line breaks.
            label = ' '.join(label.splitlines())
            groups[(label, returned, bottle.spec.name)].append(bottle.body_code)
            if is_selected_out:
                named_bad_out[(bottle.outbound_id, bottle.spec_id)] += 1
        elif zone == 'SCRAP':
            groups[('报废', bottle.returned_to_customer, bottle.spec.name)].append(bottle.body_code)
    for (label, returned, spec_name), codes in groups.items():
        marker = '带回' if returned is True else '未带回' if returned is False else '退还情况未标记'
        lines.append(f'{label}共{len(codes)}个（{marker}）')
        lines.append(f'规格：{spec_name}')
        lines.extend(codes)
    for row in outgoing:
        for item in row.lines:
            missing = item.bad_quantity - named_bad_out[(row.id, item.spec_id)]
            if missing > 0:
                lines.append(f'不良品共{missing}个（带回；规格：{item.spec_name}；未关联瓶号，出库单{row.document_no}）')
                warnings.append(f'出库单{row.document_no}的{item.spec_name}有{missing}个不良品未关联瓶号。')
    pending = defaultdict(int)
    spec_names = {}
    for row in incoming:
        for item in row.lines:
            pending[item.spec_id] += item.pending_quantity
            spec_names[item.spec_id] = item.spec_name
    if pending:
        # Only explicit selected-batch links may contribute; never pull in unselected records.
        remaining = sum(max(quantity - resolved[spec], 0) for spec, quantity in pending.items())
        lines.append(f'未检验的共{remaining}个（未带回）')
        for spec, quantity in pending.items():
            lines.append(f'规格：{spec_names[spec]}，未检验 {max(quantity - resolved[spec], 0)} 个')
        warnings.append('未检验数量按勾选入库单减已关联分库钢瓶计算；未关联入库单的快捷抄码不自动归入，请核对后修改。')
    if any(b.returned_to_customer is None and b.zone in {'BAD', 'SCRAP'} for b in bottles):
        warnings.append('存在历史退还情况未标记的钢瓶，未自动归入带回或未带回。')
    def document_payload(row, direction):
        details = []
        for item in row.lines:
            quantities = ({'pending': item.pending_quantity, 'temporary': item.temporary_quantity,
                           'scrap': item.scrap_quantity, 'good': 0, 'bad': 0} if direction == 'inbound' else
                          {'pending': 0, 'temporary': item.temporary_quantity, 'scrap': item.scrap_quantity,
                           'good': item.good_quantity, 'bad': item.bad_quantity})
            details.append({'spec_id': item.spec_id, 'spec_name': item.spec_name,
                            **quantities, 'total': sum(quantities.values())})
        quality_bottles = []
        quality_counts = defaultdict(int)
        included_bottle_ids = set()
        if direction == 'outbound':
            for item in row.lines:
                for allocation in item.allocations:
                    if allocation.origin_zone not in {'BAD', 'SCRAP'}:
                        continue
                    bottle = allocation.bottle
                    quality_bottles.append({
                        'spec_id': item.spec_id, 'spec_name': item.spec_name,
                        'zone': allocation.origin_zone,
                        'zone_name': '不良品' if allocation.origin_zone == 'BAD' else '报废',
                        'quantity': 1, 'body_code': allocation.body_code,
                        'note': (bottle.inspection_note or '') if bottle else '',
                    })
                    quality_counts[(item.spec_id, allocation.origin_zone)] += 1
                    if allocation.bottle_id:
                        included_bottle_ids.add(allocation.bottle_id)
            # Keep old outbound records useful even if they predate the allocation snapshot table.
            for bottle in bottles:
                zone = bottle.outbound_origin_zone
                if bottle.outbound_id != row.id or zone not in {'BAD', 'SCRAP'} or bottle.id in included_bottle_ids:
                    continue
                quality_bottles.append({
                    'spec_id': bottle.spec_id, 'spec_name': bottle.spec.name,
                    'zone': zone, 'zone_name': '不良品' if zone == 'BAD' else '报废',
                    'quantity': 1, 'body_code': bottle.body_code,
                    'note': bottle.inspection_note or '',
                })
                quality_counts[(bottle.spec_id, zone)] += 1
            for item in row.lines:
                for zone, quantity in [('BAD', item.bad_quantity), ('SCRAP', item.scrap_quantity)]:
                    missing = quantity - quality_counts[(item.spec_id, zone)]
                    if missing > 0:
                        quality_bottles.append({
                            'spec_id': item.spec_id, 'spec_name': item.spec_name,
                            'zone': zone, 'zone_name': '不良品' if zone == 'BAD' else '报废',
                            'quantity': missing, 'body_code': '', 'note': '',
                        })
        else:
            for bottle in bottles:
                if bottle.inbound_id != row.id:
                    continue
                zone = bottle.outbound_origin_zone if bottle.zone == 'OUTBOUND' else bottle.zone
                if zone not in {'BAD', 'SCRAP'}:
                    continue
                quality_bottles.append({
                    'spec_id': bottle.spec_id, 'spec_name': bottle.spec.name,
                    'zone': zone, 'zone_name': '不良品' if zone == 'BAD' else '报废',
                    'quantity': 1, 'body_code': bottle.body_code,
                    'note': bottle.inspection_note or '',
                })
                quality_counts[(bottle.spec_id, zone)] += 1
            for item in row.lines:
                missing = item.scrap_quantity - quality_counts[(item.spec_id, 'SCRAP')]
                if missing > 0:
                    quality_bottles.append({
                        'spec_id': item.spec_id, 'spec_name': item.spec_name,
                        'zone': 'SCRAP', 'zone_name': '报废',
                        'quantity': missing, 'body_code': '', 'note': '',
                    })
        return {'id': row.id, 'direction': direction, 'document_no': row.document_no,
                'business_date': row.business_date, 'customer': source.name, 'handler': row.handler,
                'note': row.note or '', 'total': row.total_quantity, 'lines': details,
                'quality_bottles': quality_bottles}

    documents = [document_payload(row, 'inbound') for row in incoming] + [document_payload(row, 'outbound') for row in outgoing]
    by_spec = {}
    for document in documents:
        for item in document['lines']:
            summary = by_spec.setdefault(item['spec_id'], {'spec_id': item['spec_id'], 'spec_name': item['spec_name'], 'inbound': 0, 'outbound': 0})
            summary[document['direction']] += item['total']
    return {'title': '收发记录', 'company': settings.app_name, 'customer': source.name,
            'date_from': date_from, 'date_to': date_to, 'documents': documents,
            'spec_summary': list(by_spec.values()),
            'inbound_total': sum(row.total_quantity for row in incoming),
            'outbound_total': sum(row.total_quantity for row in outgoing),
            'notes_text': '\n'.join(lines[detail_start:]),
            'text': '\n'.join(lines), 'warnings': warnings,
            'inbound_count': len(incoming), 'outbound_count': len(outgoing)}
