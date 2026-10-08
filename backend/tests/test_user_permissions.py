from sqlalchemy.orm import Session

from test_material_daily import setup


def test_admin_can_rename_account_and_duplicate_is_atomic(setup):
    client, engine, mid, actor = setup
    first = client.post('/api/users', json={'username': 'before', 'name': '测试人员', 'password': 'Password123', 'permissions': []}).json()
    client.post('/api/users', json={'username': 'taken', 'name': '已占用', 'password': 'Password123'})
    endpoint = f"/api/users/{first['id']}"
    result = client.put(endpoint, json={'username': '  renamed  '})
    assert result.status_code == 200, result.text
    assert result.json()['username'] == 'renamed'
    assert result.json()['id'] == first['id']
    assert client.post('/api/auth/login', json={'username': 'before', 'password': 'Password123'}).status_code == 401
    assert client.post('/api/auth/login', json={'username': 'renamed', 'password': 'Password123'}).status_code == 200
    assert client.put(endpoint, json={'username': 'taken', 'name': '不能保存的姓名'}).status_code == 400
    assert client.put(endpoint, json={'username': 'renamed'}).json()['name'] == '测试人员'
    for username in [' ', None, 'x', 'a' * 61]:
        assert client.put(endpoint, json={'username': username}).status_code == 422
    actor.is_superadmin = False; actor.permissions = ['users:update']
    assert client.put(endpoint, json={'username': 'forbidden'}).status_code == 403
    assert client.put(endpoint, json={'name': '可以修改姓名'}).status_code == 200


def test_each_page_permission_and_document_scope(setup):
    client, engine, mid, actor = setup
    from backend.app.permissions import ALL_PERMISSION_KEYS
    catalog = client.get('/api/permissions/catalog').json()
    assert {'daily_inventory:view', 'material_daily_logs:view', 'bottle_lifecycle:view', 'material_inbound:view', 'material_outbound:view', 'material_return:view'} <= ALL_PERMISSION_KEYS
    assert len([key for group in catalog for key, _ in group['items']]) == len(ALL_PERMISSION_KEYS)
    docs = {}
    for kind in ['NORMAL_IN', 'OUTBOUND']:
        response = client.post('/api/material-documents', json={'document_type': kind, 'business_date': '2026-09-01', 'handler': '测试', 'lines': [{'material_id': mid, 'quantity': 1}]})
        assert response.status_code == 201, response.text
        docs[kind] = response.json()['id']
    actor.is_superadmin = False; actor.permissions = ['material_inbound:view', 'material_inbound:create']
    assert client.get('/api/material-documents?document_type=OUTBOUND').status_code == 403
    assert client.get('/api/material-documents').json()['total'] == 1
    assert client.delete(f"/api/material-documents/{docs['OUTBOUND']}").status_code == 403
    actor.permissions = ['material_return:view']
    assert client.get('/api/material-documents/return-options').status_code == 200
    assert client.get('/api/material-documents?document_type=OUTBOUND').status_code == 403
    for permission, allowed, forbidden in [
        ('daily_inventory:view', '/api/daily-inventory/logs', '/api/monthly-inventory/logs'),
        ('monthly_inventory:view', '/api/monthly-inventory/logs', '/api/daily-inventory/logs'),
        ('material_daily_logs:view', '/api/material-daily/logs/list', '/api/material-daily?business_date=2026-09-01'),
    ]:
        actor.permissions = [permission]
        assert client.get(allowed).status_code == 200
        assert client.get(forbidden).status_code == 403
    actor.permissions = ['coding:view']
    assert client.get('/api/bottles/lifecycle?body_code=missing').status_code == 403
    actor.permissions = ['bottle_lifecycle:view']
    assert client.get('/api/bottles/lifecycle?body_code=missing').status_code == 404


def test_permission_migration_preserves_access_only_once(setup):
    from backend.app.models import User
    from backend.app.permissions import migrate_page_permissions
    client, engine, mid, actor = setup
    with Session(engine) as db:
        user = User(username='legacy', name='历史权限', password_hash='unused', permissions=['material_docs:view', 'material_docs:post', 'monthly_inventory:view', 'monthly_inventory:update', 'material_daily:view', 'coding:view'])
        db.add(user); db.commit()
        migrate_page_permissions(db)
        db.refresh(user)
        assert {'daily_inventory:view', 'daily_inventory:update', 'bottle_lifecycle:view', 'material_daily_logs:view', 'material_inbound:view', 'material_outbound:view', 'material_return:post'} <= set(user.permissions)
        assert 'material_docs:view' not in user.permissions
        user.permissions = ['monthly_inventory:view']; db.commit()
        migrate_page_permissions(db); db.refresh(user)
        assert user.permissions == ['monthly_inventory:view']
