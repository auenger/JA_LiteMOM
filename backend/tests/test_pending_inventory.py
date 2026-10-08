from datetime import date, datetime
from sqlalchemy.orm import Session
from test_material_daily import setup


def seed(engine, user):
    from backend.app.models import Bottle, BottleSource, BottleSpec, BottleInbound, BottleInboundLine, BottleOutbound, BottleOutboundLine
    with Session(engine) as db:
        source=BottleSource(name='盘点状态单位'); other=BottleSource(name='其他单位')
        spec=BottleSpec(name='测试规格'); db.add_all([source,other,spec]); db.flush()
        inbound=BottleInbound(document_no='STATE-IN',business_date=date(2050,1,30),source_id=source.id,handler='测试',status='POSTED',created_by=user.id,pending_quantity=10,temporary_quantity=0,scrap_quantity=0)
        inbound.lines=[BottleInboundLine(spec_id=spec.id,pending_quantity=10,temporary_quantity=0,scrap_quantity=0)]
        outbound=BottleOutbound(document_no='STATE-OUT',business_date=date(2050,2,1),source_id=source.id,customer='测试',handler='测试',status='POSTED',created_by=user.id)
        outbound.lines=[BottleOutboundLine(spec_id=spec.id,quantity=2,good_quantity=1,bad_quantity=1)]
        db.add_all([inbound,outbound]);db.flush()
        ids=[]
        for i,(zone,origin,day) in enumerate([('GOOD',None,31),('BAD',None,31),('SCRAP',None,31),('OUTBOUND','GOOD',31),('OUTBOUND','BAD',31),('PENDING',None,31),('GOOD',None,0)]):
            bottle=Bottle(body_code=f'STATE-{i}',inbound_id=inbound.id,source_id=source.id,spec_id=spec.id,zone=zone,process_status='INSPECTED' if zone!='PENDING' else 'CODED',coding_date=date(2050,1,day) if day else date(2050,2,3),coded_at=datetime(2050,1,31),coded_by=user.id,outbound_id=outbound.id if origin else None,outbound_origin_zone=origin)
            db.add(bottle);db.flush();ids.append(bottle.id)
        # Direct coding without an inbound link is also resolved stock of its own company.
        db.add(Bottle(body_code='OTHER',source_id=other.id,spec_id=spec.id,zone='GOOD',coding_date=date(2050,1,31),coded_by=user.id))
        db.commit();return source.id,spec.id,ids,outbound.id


def pending(report,spec):
    return next(r for r in report['tables']['balance']['rows'] if r['metric']=='BALANCE_PENDING' and r['spec_id']==spec)['values']


def test_pending_removes_resolved_without_double_deducting_outbound(setup):
    client,engine,_,actor=setup
    source,spec,ids,outbound=seed(engine,actor)
    def daily():
        r=client.get('/api/daily-inventory',params={'date_from':'2050-01-30','date_to':'2050-02-03','source_id':source});assert r.status_code==200,r.text
        return pending(r.json(),spec)
    assert daily()=={'2050-01-30':10,'2050-01-31':5,'2050-02-01':5,'2050-02-02':5,'2050-02-03':4}
    report=client.get('/api/monthly-inventory',params={'month_from':'2050-01','month_to':'2050-02','source_id':source}).json()
    assert pending(report,spec)=={'2050-01':5,'2050-02':4}
    # Changing GOOD to BAD does not deduct pending again.
    assert client.put(f'/api/bottles/{ids[0]}/status',json={'zone':'BAD','returned_to_customer':True}).status_code==200
    assert daily()['2050-02-02']==5
    # A cancelled outbound restores quality stock but must not restore pending.
    from backend.app.models import Bottle, BottleOutbound
    with Session(engine) as db:
        db.get(BottleOutbound,outbound).status='VOID'
        for bid,zone in [(ids[3],'GOOD'),(ids[4],'BAD')]:
            bottle=db.get(Bottle,bid);bottle.zone=zone;bottle.outbound_id=None;bottle.outbound_origin_zone=None
        db.commit()
    assert daily()['2050-02-02']==5
    # Explicit inventory counts still take priority and roll forward.
    r=client.put('/api/daily-inventory/value',json={'business_date':'2050-02-01','source_id':source,'spec_id':spec,'metric':'BALANCE_PENDING','value':8})
    assert r.status_code==200,r.text
    assert daily()['2050-02-02']==8
    assert daily()['2050-02-03']==7


def test_return_flag_is_persistent_filterable_and_does_not_create_outbound(setup):
    from backend.app.models import Bottle, BottleOutbound
    client,engine,_,actor=setup
    source,spec,ids,_=seed(engine,actor)
    url=f'/api/bottles/{ids[0]}/status'
    r=client.put(url,json={'zone':'BAD','returned_to_customer':True,'note':'退还客户标记'})
    assert r.status_code==200,r.text
    assert r.json()['returned_to_customer'] is True and r.json()['zone']=='BAD'
    yes=client.get('/api/bottles',params={'zone':'BAD','returned_to_customer':'true','page_size':1}).json()
    assert yes['total']==1 and yes['items'][0]['id']==ids[0]
    assert client.get('/api/bottles',params={'zone':'BAD','returned_to_customer':'false'}).json()['total']==0
    with Session(engine) as db:
        assert db.query(BottleOutbound).count()==1
        assert db.get(Bottle,ids[0]).outbound_id is None
        assert db.get(Bottle,ids[1]).returned_to_customer is None
    assert client.put(url,json={'zone':'GOOD','returned_to_customer':True}).status_code==400
    assert client.put(url,json={'zone':'GOOD'}).json()['returned_to_customer'] is None
    assert client.put(url,json={'zone':'BAD','returned_to_customer':False}).json()['returned_to_customer'] is False
    assert client.get('/api/bottles',params={'zone':'BAD','returned_to_customer':'false'}).json()['total']==1
    actor.is_superadmin=False;actor.permissions=['inspection:view']
    assert client.put(url,json={'zone':'BAD','returned_to_customer':True}).status_code==403
