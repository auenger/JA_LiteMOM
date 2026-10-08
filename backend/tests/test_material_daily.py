from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool



@pytest.fixture
def setup():
    from backend.app.database import Base, get_db
    from backend.app.material_daily import router
    from backend.app.models import Material, User
    from backend.app.security import current_user

    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        user = User(username='tester', name='测试员', password_hash='unused', is_superadmin=True)
        material = Material(name='测试粉末', specification='A', material_unit='袋', unit='袋',
                            conversion_enabled=True, conversion_ratio=Decimal('2.5'), stock_unit='kg', stock=0)
        db.add_all([user, material]); db.commit()
        mid = material.id
    app = FastAPI()
    app.include_router(router)
    from backend.app.menu_settings import router as menu_router
    app.include_router(menu_router)
    from backend.app.api import router as api_router
    app.include_router(api_router)
    from backend.app.bottle_receipt import router as receipt_router
    app.include_router(receipt_router)
    def session():
        with Session(engine, expire_on_commit=False, autoflush=False) as db:
            yield db
    app.dependency_overrides[get_db] = session
    app.dependency_overrides[current_user] = lambda: user
    with TestClient(app) as client:
        yield client, engine, mid, user
    engine.dispose()


def put(client, mid, day, inbound, outbound, version=0):
    return client.put(f'/api/material-daily/{mid}', params={'business_date': day},
                      json={'inbound': inbound, 'outbound': outbound, 'version': version})


def row(client, day):
    return client.get('/api/material-daily', params={'business_date': day}).json()['items'][0]


def test_daily_history_and_audit(setup):
    client, engine, mid, user = setup
    assert row(client, '2026-09-01')['version'] == 0
    response = put(client, mid, '2026-09-01', 10, 2)
    assert response.status_code == 200, response.text
    assert float(response.json()['closing']) == 8
    assert float(response.json()['material']['converted_stock']) == 20
    assert put(client, mid, '2026-09-02', 0, 5).status_code == 200
    assert put(client, mid, '2026-09-01', 12, 2, 1).status_code == 200
    assert float(row(client, '2026-09-02')['opening']) == 10
    assert float(row(client, '2026-09-02')['closing']) == 5
    assert put(client, mid, '2026-09-01', 12, 2, 2).status_code == 200
    logs = client.get('/api/material-daily/logs/list?business_date=2026-09-01').json()
    assert logs['total'] == 2  # An unchanged retry must not duplicate stock or logs.
    assert float(logs['items'][0]['old_inbound']) == 10
    assert logs['items'][0]['operator_name'] == '测试员'
    assert put(client, mid, '2026-09-01', 20, 0, 1).status_code == 409
    assert put(client, mid, '2026-09-01', -1, 0, 2).status_code == 422
    assert put(client, mid, '2026-09-01', 'NaN', 0, 2).status_code == 422
    assert put(client, mid, '2026-09-01', 1.001, 0, 2).status_code == 422
    assert put(client, mid, '2026-09-01', 0, 0, 2).status_code == 400
    assert float(row(client, '2026-09-02')['closing']) == 5


def test_historical_shortage_even_when_current_stock_positive(setup):
    client, engine, mid, user = setup
    assert put(client, mid, '2026-09-01', 10, 0).status_code == 200
    assert put(client, mid, '2026-09-02', 0, 8).status_code == 200
    assert put(client, mid, '2026-09-03', 100, 0).status_code == 200
    response = put(client, mid, '2026-09-01', 5, 0, 1)
    assert response.status_code == 400
    assert '2026-09-02' in response.json()['detail']
    assert float(row(client, '2026-09-03')['closing']) == 102


def test_existing_documents_and_permissions(setup):
    from backend.app.models import Material, MaterialDocument, MaterialDocumentLine
    client, engine, mid, user = setup
    with Session(engine) as db:
        material = db.get(Material, mid)
        material.stock = 20
        document = MaterialDocument(document_no='TEST-IN', document_type='NORMAL_IN', business_date=date(2026, 9, 2),
                                    handler='仓管', status='POSTED', created_by=user.id)
        document.lines = [MaterialDocumentLine(material_id=mid, material_name='测试粉末', unit='袋', quantity=20, unit_price=0, amount=0)]
        db.add(document); db.commit()
    assert float(row(client, '2026-09-01')['closing']) == 0
    assert float(row(client, '2026-09-02')['document_inbound']) == 20
    assert put(client, mid, '2026-09-01', 0, 1).status_code == 400
    assert put(client, mid, '2026-09-02', 0, 3).status_code == 200
    assert float(row(client, '2026-09-02')['closing']) == 17
    user.is_superadmin = False
    user.permissions = ['material_daily:view']
    assert client.get('/api/material-daily?business_date=2026-09-02').status_code == 200
    assert put(client, mid, '2026-09-02', 0, 5, 1).status_code == 403
    user.permissions = []
    assert client.get('/api/material-daily/logs/list?business_date=2026-09-02').status_code == 403


def test_logs_pagination_and_date_filter(setup):
    from backend.app.models import MaterialDailyLog
    client, engine, mid, user = setup
    with Session(engine) as db:
        for day, count in [(date(2026, 9, 1), 25), (date(2026, 9, 2), 3)]:
            for index in range(count):
                db.add(MaterialDailyLog(material_id=mid, material_name='测试粉末', unit='袋',
                    business_date=day, old_inbound=index, old_outbound=0, inbound=index + 1,
                    outbound=0, balance_after=index + 1, created_by=user.id, operator_name=user.name))
        db.commit()
    def logs(page, size=20, day='2026-09-01'):
        return client.get('/api/material-daily/logs/list', params={
            'business_date': day, 'page': page, 'page_size': size})
    first, second = logs(1).json(), logs(2).json()
    assert first['total'] == second['total'] == 25
    assert len(first['items']) == 20
    assert len(second['items']) == 5
    ids = [item['id'] for item in first['items'] + second['items']]
    assert len(set(ids)) == 25
    assert ids == sorted(ids, reverse=True)
    assert len(logs(1, 10).json()['items']) == 10
    assert logs(3, 10).json()['items'] == second['items']
    assert logs(3).json()['items'] == []
    assert logs(1, day='2026-09-02').json()['total'] == 3
    assert logs(0).status_code == 422
    assert logs(1, 101).status_code == 422


def test_all_dates_and_log_search(setup):
    client, engine, mid, user = setup
    for day in ['2026-09-01', '2026-09-02', '2026-09-03']:
        assert put(client, mid, day, 10, 0).status_code == 200
    url = '/api/material-daily/logs/list'
    data = client.get(url).json()
    assert data['total'] == 3
    assert [r['business_date'] for r in data['items']] == ['2026-09-03', '2026-09-02', '2026-09-01']
    data = client.get(url, params={'date_from': '2026-09-02', 'date_to': '2026-09-03', 'query': '粉末', 'page_size': 1}).json()
    assert data['total'] == 2
    assert len(data['items']) == 1
    assert client.get(url, params={'date_to': '2026-09-01'}).json()['total'] == 1
    assert client.get(url, params={'query': '不存在'}).json()['total'] == 0
    assert client.get(url, params={'query': '%'}).json()['total'] == 0
    assert client.get(url, params={'date_from': '2026-09-03', 'date_to': '2026-09-01'}).status_code == 400


def test_menu_settings_permissions_persistence_and_conflicts(setup):
    client, engine, mid, user = setup
    url = '/api/menu-settings'
    assert client.get(url).json() == {'groups': [], 'version': 0}
    payload = {'version': 0, 'groups': [{'label': '原材料', 'items': [
        {'path': '/material-daily-logs', 'hidden': False},
        {'path': '/material-daily', 'hidden': True}]}]}
    user.is_superadmin = False
    user.permissions = ['users:update']
    assert client.put(url, json=payload).status_code == 403
    assert client.get(url).json()['version'] == 0
    user.is_superadmin = True
    response = client.put(url, json=payload)
    assert response.status_code == 200
    assert response.json()['version'] == 1
    assert client.get(url).json()['groups'] == payload['groups']
    assert client.put(url, json=payload).status_code == 409
    payload['version'] = 1
    payload['groups'][0]['items'].append({'path': '/material-daily', 'hidden': False})
    assert client.put(url, json=payload).status_code == 422
    payload['groups'][0]['items'] = [{'path': '/menu-settings', 'hidden': True}]
    assert client.put(url, json=payload).status_code == 422
    assert client.put(url, json={'version': 1, 'groups': []}).status_code == 200
    assert client.get(url).json() == {'groups': [], 'version': 2}


def test_custom_menu_names_and_groups(setup):
    client, engine, mid, user = setup
    url = '/api/menu-settings'
    payload = {'version': 0, 'groups': [{'label': ' 常用业务 ', 'items': [
        {'path': '/coding', 'label': ' 钢瓶登记 ', 'hidden': False}]}]}
    response = client.put(url, json=payload)
    assert response.status_code == 200
    assert client.get(url).json()['groups'] == [{'label': '常用业务', 'items': [
        {'path': '/coding', 'label': '钢瓶登记', 'hidden': False}]}]
    payload['version'] = 1
    payload['groups'][0]['items'][0]['label'] = '   '
    assert client.put(url, json=payload).status_code == 422
    payload['groups'][0]['items'][0]['label'] = '钢瓶登记'
    payload['groups'].append({'label': '常用业务', 'items': []})
    assert client.put(url, json=payload).status_code == 422
    assert client.get(url).json()['version'] == 1


def test_disabled_material_hidden_but_history_retained(setup):
    from backend.app.models import Material
    client, engine, mid, user = setup
    assert put(client, mid, '2026-09-01', 10, 2).status_code == 200
    with Session(engine) as db:
        db.get(Material, mid).is_active = False
        db.commit()
    assert client.get('/api/material-daily?business_date=2026-09-01').json()['items'] == []
    assert client.get('/api/material-daily/logs/list').json()['total'] == 1
    assert put(client, mid, '2026-09-01', 20, 2, 1).status_code == 400
    with Session(engine) as db:
        db.get(Material, mid).is_active = True
        db.commit()
    assert float(row(client, '2026-09-01')['closing']) == 8
