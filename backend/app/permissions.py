PERMISSIONS = [
    {"group": "日度盘点", "items": [("daily_inventory:view", "查询"), ("daily_inventory:update", "修改盘点值")]},
    {"group": "出入库日志", "items": [("material_daily_logs:view", "查询")]},
    {"group": "瓶子生命周期", "items": [("bottle_lifecycle:view", "查询"), ("bottle_lifecycle:update", "修改瓶子状态"), ("bottle_lifecycle:restore", "纠正出库关联")]},
    {"group": "原材料出入库管理", "items": [("material_daily:view", "查询"), ("material_daily:update", "修改出入库数量")]},
    {"group": "首页", "items": [("dashboard:view", "访问首页")]},
    {"group": "盈利成本计算", "items": [("profit:view", "查询盈利与成本")]},
    {"group": "人员信息", "items": [(f"users:{action}", label) for action, label in [("view", "查询"), ("create", "新增"), ("update", "编辑"), ("delete", "删除")] ]},
    {"group": "原材料档案", "items": [(f"materials:{action}", label) for action, label in [("view", "查询"), ("create", "新增"), ("update", "编辑"), ("delete", "删除"), ("import", "导入"), ("export", "导出")] ]},
    {"group": "供应商", "items": [(f"suppliers:{action}", label) for action, label in [("view", "查询"), ("create", "新增"), ("update", "编辑"), ("delete", "删除")] ]},
    {"group": "供应商采购单", "items": [("purchase_orders:view", "查询"), ("purchase_orders:create", "新增"), ("purchase_orders:update", "编辑"), ("purchase_orders:delete", "删除草稿"), ("purchase_orders:post", "确认采购单"), ("purchase_orders:void", "作废采购单"), ("purchase_orders:payment", "修改付款状态")]},
    {"group": "供瓶单位", "items": [(f"sources:{action}", label) for action, label in [("view", "查询"), ("create", "新增"), ("update", "编辑"), ("delete", "删除")] ]},
    {"group": "瓶子规格", "items": [(f"specs:{action}", label) for action, label in [("view", "查询"), ("create", "新增"), ("update", "编辑"), ("delete", "删除")] ]},
    {"group": "钢瓶生产厂家", "items": [(f"manufacturers:{action}", label) for action, label in [("view", "查询"), ("create", "新增"), ("update", "编辑"), ("delete", "删除")] ]},
    {"group": "抄码快捷配置", "items": [(f"quick_configs:{action}", label) for action, label in [("view", "查询"), ("create", "新增"), ("update", "编辑"), ("delete", "删除")] ]},
    *[{"group": label, "items": [(f"{prefix}:{action}", title) for action, title in [("view", "查询"), ("create", "新增"), ("update", "编辑"), ("delete", "删除草稿"), ("post", "确认入账"), ("void", "作废/撤销")]]}
      for prefix, label in [("material_inbound", "原材料入库"), ("material_outbound", "材料出库"), ("material_return", "退料入库")]],
    {"group": "钢瓶入库", "items": [("bottle_inbound:view", "查询"), ("bottle_inbound:export", "导出收发记录 Word"), ("bottle_inbound:create", "新增"), ("bottle_inbound:update", "编辑"), ("bottle_inbound:delete", "删除草稿"), ("bottle_inbound:post", "确认入库"), ("bottle_inbound:void", "作废/撤销")]},
    {"group": "良品钢瓶出库", "items": [("bottle_outbound:view", "查询"), ("bottle_outbound:create", "新增"), ("bottle_outbound:update", "编辑"), ("bottle_outbound:delete", "删除草稿"), ("bottle_outbound:post", "审批出库"), ("bottle_outbound:void", "撤销出库")]},
    {"group": "抄码工序", "items": [("coding:view", "查询"), ("coding:create", "新增"), ("coding:update", "编辑"), ("coding:delete", "删除")]},
    {"group": "移动快速入库", "items": [("quick_inbound:view", "访问页面"), ("quick_inbound:create", "快速入库")]},
    {"group": "移动快速出库", "items": [("quick_outbound:view", "访问页面"), ("quick_outbound:create", "快速出库")]},
    {"group": "移动快捷抄码", "items": [("quick_entry:view", "访问页面"), ("quick_entry:create", "快捷抄码")]},
    {"group": "钢瓶检验单", "items": [("inspection_documents:view", "查询"), ("inspection_documents:create", "生成/同步"), ("inspection_documents:update", "修改检验单与明细"), ("inspection_documents:export", "导出"), ("inspection_documents:void", "作废")]},
    {"group": "未经系统验证瓶子池", "items": [("unverified_bottles:view", "查询"), ("unverified_bottles:export", "导出全部 Excel"), ("unverified_bottles:create", "录入上游驳回信息"), ("unverified_bottles:update", "编辑驳回钢瓶"), ("unverified_bottles:batch", "生成重检单"), ("unverified_bottles:delete", "彻底删除钢瓶")]},
    {"group": "待抄码池", "items": [("coding_pool:view", "查询")]},
    {"group": "质量分类库", "items": [("inspection:view", "查询"), ("inspection:create", "修改良品/不良品/报废状态"), ("inspection:delete", "撤销状态修改")]},
    {"group": "钢瓶状态区", "items": [("bottle_zones:view", "查询")]},
    {"group": "月度盘点", "items": [("monthly_inventory:view", "查询"), ("monthly_inventory:update", "修改盘点值")]},
]

ALL_PERMISSION_KEYS = {key for group in PERMISSIONS for key, _ in group["items"]}


MATERIAL_DOCUMENT_PERMISSIONS = {
    "NORMAL_IN": "material_inbound", "OUTBOUND": "material_outbound", "RETURN_IN": "material_return",
}


def migrate_page_permissions(db):
    """Preserve existing access once; later revocations must remain revoked."""
    from sqlalchemy import select
    from .models import ApplicationMigration, User
    key = "independent_page_permissions_v1"
    if db.get(ApplicationMigration, key):
        return
    for user in db.scalars(select(User)):
        permissions = set(user.permissions or [])
        for action in ["view", "create", "update", "delete", "post", "void"]:
            if f"material_docs:{action}" in permissions:
                permissions.remove(f"material_docs:{action}")
                permissions.update(f"{prefix}:{action}" for prefix in MATERIAL_DOCUMENT_PERMISSIONS.values())
        for action in ["view", "update"]:
            if f"monthly_inventory:{action}" in permissions:
                permissions.add(f"daily_inventory:{action}")
        if "material_daily:view" in permissions:
            permissions.add("material_daily_logs:view")
        if permissions.intersection({"coding:view", "inspection_documents:view", "bottle_zones:view"}):
            permissions.add("bottle_lifecycle:view")
        if "inspection:create" in permissions:
            permissions.add("bottle_lifecycle:update")
        if "bottle_outbound:update" in permissions:
            permissions.add("bottle_lifecycle:restore")
        user.permissions = sorted(permissions)
    db.add(ApplicationMigration(key=key))
    db.commit()
