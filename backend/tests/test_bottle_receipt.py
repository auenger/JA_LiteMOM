from datetime import date
from sqlalchemy.orm import Session
from test_material_daily import setup
from test_pending_inventory import seed


def test_receipt_only_selected_documents_and_current_return_marks(setup):
    from backend.app.models import Bottle, BottleInbound, BottleInboundLine
    client,engine,_,actor=setup
    source,spec,ids,outbound=seed(engine,actor)
    with Session(engine) as db:
        inbound=db.get(Bottle,ids[0]).inbound_id
        bad=db.get(Bottle,ids[1]);bad.inspection_note='沙眼';bad.returned_to_customer=True;bad.body_code='003210974252'
        scrap=db.get(Bottle,ids[2]);scrap.returned_to_customer=False; scrap.body_code='003221596860'
        other=BottleInbound(document_no='UNSELECTED',business_date=date(2050,1,29),source_id=source,handler='测试',status='POSTED',created_by=actor.id,pending_quantity=9876,temporary_quantity=0,scrap_quantity=0)
        other.lines=[BottleInboundLine(spec_id=spec,pending_quantity=9876,temporary_quantity=0,scrap_quantity=0)]
        db.add(other);db.flush()
        db.add(Bottle(inbound_id=other.id,body_code='UNSELECTED-BOTTLE',source_id=source,spec_id=spec,zone='BAD',coding_date=date(2050,1,31),coded_by=actor.id))
        db.commit()
    r=client.post('/api/bottle-receipt/preview',json={'inbound_ids':[inbound,inbound],'outbound_ids':[outbound]})
    assert r.status_code==200,r.text
    report=r.json();text=report['text']
    assert report['company'] == '锦安特种设备检测'
    assert report['inbound_total'] == 10 and report['outbound_total'] == 2
    assert report['spec_summary'] == [{'spec_id': spec, 'spec_name': '测试规格', 'inbound': 10, 'outbound': 2}]
    assert report['documents'][0]['lines'][0]['pending'] == 10
    assert report['documents'][1]['lines'][0]['good'] == 1
    assert report['documents'][1]['lines'][0]['bad'] == 1
    assert '规格：测试规格' in report['notes_text']
    assert report['inbound_count']==1 and report['outbound_count']==1
    for value in ['2050年1月30号收到','2050年2月1号出给','瓶共10个','沙眼共1个（带回）','003210974252','报废共1个（未带回）','003221596860']:
        assert value in text
    assert '9876' not in text and 'UNSELECTED-BOTTLE' not in text and '2050年1月29号' not in text
    with Session(engine) as db:
        assert db.query(BottleInbound).count()==2
    actor.is_superadmin=False;actor.permissions=['bottle_inbound:view','bottle_outbound:view']
    assert client.post('/api/bottle-receipt/preview',json={'inbound_ids':[inbound]}).status_code==403
    actor.permissions=['bottle_inbound:export']
    assert client.post('/api/bottle-receipt/preview',json={'inbound_ids':[inbound]}).status_code==200


def test_receipt_rejects_stale_mixed_customer_or_unposted_selection(setup):
    from backend.app.models import Bottle, BottleInbound, BottleSource
    client,engine,_,actor=setup
    source,spec,ids,outbound=seed(engine,actor)
    with Session(engine) as db:
        inbound=db.get(Bottle,ids[0]).inbound_id
        other_source=BottleSource(name='不能混合导出的客户');db.add(other_source);db.flush()
        other=BottleInbound(document_no='OTHER-RECEIPT',business_date=date(2050,1,30),source_id=other_source.id,handler='测试',status='POSTED',created_by=actor.id,pending_quantity=0,temporary_quantity=0,scrap_quantity=0)
        db.add(other);db.commit();other_id=other.id
    assert client.post('/api/bottle-receipt/preview',json={}).status_code==400
    assert client.post('/api/bottle-receipt/preview',json={'inbound_ids':[999999]}).status_code==404
    assert client.post('/api/bottle-receipt/preview',json={'inbound_ids':[-1]}).status_code==422
    assert client.post('/api/bottle-receipt/preview',json={'inbound_ids':[inbound,other_id]}).status_code==400
    with Session(engine) as db:
        db.get(BottleInbound,inbound).status='VOID';db.commit()
    assert client.post('/api/bottle-receipt/preview',json={'inbound_ids':[inbound],'outbound_ids':[outbound]}).status_code==400
