from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import re
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


T = TypeVar("T")


def normalize_code_prefixes(value: str) -> str:
    """把中英文逗号、分号或空白分隔的多个编号前缀规范成英文逗号连接，去重并保持顺序。"""
    seen: list[str] = []
    for part in re.split(r"[,，;；\s]+", value):
        prefix = part.strip().upper()
        if prefix and prefix not in seen:
            seen.append(prefix)
    return ",".join(seen)


class PageOut(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=60)
    name: str = Field(min_length=1, max_length=80)
    role_name: str = Field(default="业务人员", min_length=1, max_length=80)
    phone: str | None = None
    remark: str | None = None
    password: str = Field(min_length=8)
    is_active: bool = True
    permissions: list[str] = []


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=60)
    name: str | None = None
    role_name: str | None = Field(default=None, min_length=1, max_length=80)
    phone: str | None = None
    remark: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)
    permissions: list[str] | None = None


    @field_validator("username", mode="before")
    @classmethod
    def clean_username(cls, value):
        if not isinstance(value, str):
            raise ValueError("登录账号不能为空")
        return value.strip()


class UserOut(ORMModel):
    id: int
    username: str
    name: str
    role_name: str
    phone: str | None
    remark: str | None
    is_active: bool
    is_superadmin: bool
    must_change_password: bool
    permissions: list[str]
    created_at: datetime


class MaterialBase(BaseModel):
    name: str
    material_type: Literal["MATERIAL", "SCRAP"] = "MATERIAL"
    specification: str = ""
    material_unit: str = "个"
    conversion_enabled: bool = False
    stock_unit: str = ""
    conversion_ratio: Decimal = Field(default=1, gt=0, max_digits=18, decimal_places=2)
    price: Decimal = Field(default=0, ge=0, max_digits=18, decimal_places=2)
    warning_enabled: bool = False
    safety_threshold: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    is_active: bool = True
    remark: str | None = None

    @model_validator(mode="after")
    def check_threshold(self):
        self.material_unit = self.material_unit.strip()
        if not self.material_unit:
            raise ValueError("物料单位不能为空")
        if self.conversion_enabled:
            self.stock_unit = self.stock_unit.strip()
            if not self.stock_unit:
                raise ValueError("启用单位换算时必须填写库存单位")
        else:
            self.stock_unit = self.material_unit
            self.conversion_ratio = Decimal(1)
        if self.warning_enabled and self.safety_threshold is None:
            raise ValueError("启用库存预警时必须填写安全库存阈值")
        return self


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(MaterialBase):
    pass


class MaterialSupplierPriceOut(ORMModel):
    id: int
    supplier_id: int
    supplier_name: str
    purchase_price: Decimal


class MaterialOut(ORMModel, MaterialBase):
    id: int
    stock: Decimal
    converted_stock: Decimal | None
    warning_status: str
    supplier_prices: list[MaterialSupplierPriceOut] = []


class PartnerBase(BaseModel):
    name: str
    contact: str | None = None
    phone: str | None = None
    address: str | None = None
    remark: str | None = None
    is_active: bool = True


class SupplierMaterialInput(BaseModel):
    material_id: int
    purchase_price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)


class SupplierMaterialOut(ORMModel):
    id: int
    material_id: int
    material_name: str
    material_type: str
    specification: str
    unit: str
    purchase_price: Decimal


class SupplierCreate(PartnerBase):
    material_prices: list[SupplierMaterialInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_materials(self):
        if len({item.material_id for item in self.material_prices}) != len(self.material_prices):
            raise ValueError("同一供应商不能重复配置原材料")
        return self


class SupplierOut(ORMModel, PartnerBase):
    id: int
    material_prices: list[SupplierMaterialOut] = Field(default_factory=list)


class SourceCreate(PartnerBase):
    is_default: bool = False
    sort_order: int = 0


class SourceOut(ORMModel, SourceCreate):
    id: int


class SpecCreate(BaseModel):
    name: str
    inspection_price: Decimal = Field(default=0, ge=0, max_digits=18, decimal_places=2)
    volume: Decimal = Field(default=0, ge=0, max_digits=18, decimal_places=2)
    wall_thickness: Decimal = Field(default=0, ge=0, max_digits=18, decimal_places=2)
    is_default: bool = False
    sort_order: int = 0
    is_active: bool = True
    remark: str | None = None


class SpecOut(ORMModel, SpecCreate):
    id: int


class SpecOptionOut(ORMModel):
    id: int
    name: str
    is_default: bool
    sort_order: int
    is_active: bool


class QuickConfigCreate(BaseModel):
    category: Literal["CODE_PREFIX", "INSPECTION_NOTE", "MANUFACTURE_DATE"]
    name: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=200)
    sort_order: int = 0
    is_active: bool = True


class QuickConfigOut(ORMModel, QuickConfigCreate):
    id: int


class ManufacturerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    code_prefix: str = Field(default="", max_length=200)
    sort_order: int = 0
    is_active: bool = True
    remark: str | None = None

    @model_validator(mode="after")
    def clean_fields(self):
        self.name = self.name.strip()
        self.code_prefix = normalize_code_prefixes(self.code_prefix)
        if not self.name:
            raise ValueError("厂家名称不能为空")
        return self


class ManufacturerOut(ORMModel, ManufacturerCreate):
    id: int


class ManufacturerOptionOut(ORMModel):
    id: int
    name: str
    code_prefix: str
    sort_order: int
    is_active: bool


class MaterialLineInput(BaseModel):
    material_id: int
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)


class PurchaseOrderLineInput(BaseModel):
    material_id: int
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class PurchaseOrderCreate(BaseModel):
    order_date: date
    supplier_id: int
    handler: str = Field(min_length=1, max_length=80)
    note: str | None = None
    lines: list[PurchaseOrderLineInput] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_materials(self):
        if len({item.material_id for item in self.lines}) != len(self.lines):
            raise ValueError("同一张采购单不能重复选择原材料")
        return self


class PurchaseOrderLineOut(ORMModel):
    id: int
    material_id: int
    material_name: str
    specification: str
    unit: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal


class PurchaseOrderOut(ORMModel):
    id: int
    order_no: str
    order_date: date
    supplier_id: int
    supplier_name: str
    handler: str
    note: str | None
    status: str
    is_paid: bool
    total_amount: Decimal
    inbound_document_id: int | None
    lines: list[PurchaseOrderLineOut]
    created_by: int
    created_by_name: str
    created_at: datetime
    updated_by: int | None
    updated_by_name: str | None
    updated_at: datetime
    confirmed_by: int | None
    confirmed_by_name: str | None
    confirmed_at: datetime | None
    voided_by: int | None
    voided_by_name: str | None
    voided_at: datetime | None


class PurchaseOrderPaymentUpdate(BaseModel):
    is_paid: bool


class MaterialDocumentCreate(BaseModel):
    document_type: Literal["NORMAL_IN", "OUTBOUND", "RETURN_IN"]
    business_date: date
    supplier_id: int | None = None
    purchase_order_id: int | None = None
    related_outbound_id: int | None = None
    inbound_mode: Literal["DIRECT", "PURCHASE_ORDER"] = "DIRECT"
    inbound_category: Literal["MATERIAL", "SCRAP", "PURCHASE"] = "MATERIAL"
    outbound_category: Literal["MATERIAL", "SCRAP"] = "MATERIAL"
    is_paid: bool = False
    handler: str
    note: str | None = None
    lines: list[MaterialLineInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_relation(self):
        if self.document_type == "RETURN_IN" and not self.related_outbound_id:
            raise ValueError("退料入库单必须绑定原出库单")
        if self.document_type != "RETURN_IN" and self.related_outbound_id:
            raise ValueError("只有退料入库单可以绑定原出库单")
        if self.is_paid:
            raise ValueError("付款状态请在供应商采购单中维护")
        if self.document_type != "NORMAL_IN" and (self.inbound_mode != "DIRECT" or self.inbound_category not in {"MATERIAL", "PURCHASE"}):
            raise ValueError("只有一般入库单可以设置入库类型")
        if self.document_type == "NORMAL_IN" and self.inbound_mode == "PURCHASE_ORDER" and not self.purchase_order_id:
            raise ValueError("采购单入库必须选择采购单")
        if self.inbound_mode != "PURCHASE_ORDER" and self.purchase_order_id:
            raise ValueError("只有采购单入库可以关联采购单")
        if self.inbound_mode == "PURCHASE_ORDER" and self.inbound_category == "SCRAP":
            raise ValueError("采购单入库只能作为原料入库")
        if self.inbound_mode != "PURCHASE_ORDER" and not self.lines:
            raise ValueError("请填写原材料明细")
        if self.document_type != "OUTBOUND" and self.outbound_category != "MATERIAL":
            raise ValueError("只有材料出库单可以设置出库类型")
        return self


class MaterialPaymentUpdate(BaseModel):
    is_paid: bool


class MaterialLineOut(ORMModel):
    id: int
    material_id: int
    material_name: str
    specification: str
    unit: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal


class MaterialDocumentOut(ORMModel):
    id: int
    document_no: str
    document_type: str
    business_date: date
    supplier_id: int | None
    purchase_order_id: int | None
    related_outbound_id: int | None
    inbound_mode: str
    inbound_category: str
    outbound_category: str
    is_paid: bool
    handler: str
    note: str | None
    status: str
    lines: list[MaterialLineOut]
    created_by: int
    created_by_name: str
    created_at: datetime
    updated_by: int | None
    updated_by_name: str | None
    updated_at: datetime
    posted_by: int | None
    posted_by_name: str | None
    posted_at: datetime | None
    voided_by: int | None
    voided_by_name: str | None
    voided_at: datetime | None


class BottleInboundLineCreate(BaseModel):
    spec_id: int
    pending_quantity: int = Field(default=0, ge=0)
    temporary_quantity: int = Field(default=0, ge=0)
    scrap_quantity: int = Field(default=0, ge=0)


class BottleInboundLineOut(ORMModel, BottleInboundLineCreate):
    id: int
    spec_name: str
    total_quantity: int


class BottleInboundCreate(BaseModel):
    business_date: date
    source_id: int
    pending_quantity: int = Field(default=0, ge=0)
    temporary_quantity: int = Field(default=0, ge=0)
    scrap_quantity: int = Field(default=0, ge=0)
    lines: list[BottleInboundLineCreate] = Field(default_factory=list)
    handler: str
    note: str | None = None

    @model_validator(mode="after")
    def positive_total(self):
        if self.lines:
            if len({line.spec_id for line in self.lines}) != len(self.lines):
                raise ValueError("同一入库单不能重复选择钢瓶规格")
            self.pending_quantity = sum(line.pending_quantity for line in self.lines)
            self.temporary_quantity = sum(line.temporary_quantity for line in self.lines)
            self.scrap_quantity = sum(line.scrap_quantity for line in self.lines)
        if self.pending_quantity + self.temporary_quantity + self.scrap_quantity <= 0:
            raise ValueError("本批入库总量必须大于零")
        return self


class BottleInboundOut(ORMModel):
    id: int
    document_no: str
    business_date: date
    source_id: int
    pending_quantity: int
    temporary_quantity: int
    scrap_quantity: int
    total_quantity: int
    lines: list[BottleInboundLineOut]
    handler: str
    note: str | None
    status: str
    created_at: datetime
    posted_at: datetime | None


class BottleCodingCreate(BaseModel):
    inbound_id: int
    body_code: str
    manufacture_date: date
    source_id: int
    spec_id: int


class BottleCodingUpdate(BaseModel):
    body_code: str = Field(min_length=1, max_length=100)
    manufacture_date: date | None = None
    source_id: int
    spec_id: int
    manufacturer: str | None = Field(default=None, max_length=160)


class BottleOut(ORMModel):
    coding_customer_id: int | None = None
    effective_coding_customer_id: int
    coding_customer_name: str
    id: int
    inbound_id: int | None
    body_code: str
    manufacture_date: date | None
    source_id: int
    spec_id: int
    zone: str
    process_status: str
    coding_date: date | None
    coding_sequence: int | None
    coding_note: str | None
    manufacturer: str | None = None
    coded_by: int
    coded_by_name: str
    inspection_result: str | None
    coded_at: datetime
    inspected_at: datetime | None
    inspection_note: str | None
    returned_to_customer: bool | None = None
    inspection_document_status: str = "UNINSPECTED"
    inspection_document_no: str | None = None


class CodingReviewPageOut(PageOut[BottleOut]):
    suspect_count: int


class InspectionCreate(BaseModel):
    result: Literal["GOOD", "BAD"]
    note: str | None = None


class BottleStatusUpdate(BaseModel):
    zone: Literal["GOOD", "BAD", "SCRAP"]
    note: str | None = None
    returned_to_customer: bool | None = None


class QuickEntryCreate(BaseModel):
    body_code: str
    manufacture_date: date | None = None
    inbound_id: int | None = None
    source_id: int | None = None
    spec_id: int | None = None
    note: str | None = None
    manufacturer: str | None = None


class GoodBottleExportOut(BaseModel):
    id: int
    body_code: str
    manufacture_date: date | None = None
    volume: Decimal = Decimal(0)
    manufacturer: str | None = None


class InspectionDocumentCreate(BaseModel):
    inspection_date: date


class InspectionDocumentGenerate(BaseModel):
    inspection_date: date | None = None
    inspection_dates: list[date] | None = Field(default=None, min_length=1, max_length=31)
    document_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if (self.inspection_date is None) == (self.inspection_dates is None):
            raise ValueError("请选择一个日期或多个日期")
        if self.inspection_dates:
            if self.document_date is None:
                raise ValueError("请选择检验单日期")
            self.inspection_dates = sorted(set(self.inspection_dates))
            if len({(day.year, day.month) for day in self.inspection_dates}) != 1:
                raise ValueError("请选择同一月份内的日期")
        elif self.document_date is not None:
            raise ValueError("单日兼容模式不能另行指定检验单日期")
        return self


class InspectionDocumentUpdate(BaseModel):
    customer_name: str = Field(default="", max_length=160)
    inspector_id: int | None = None


class InspectionDocumentLineUpdate(BaseModel):
    body_code: str | None = Field(default=None, max_length=100)
    manufacture_date: date | None = None
    manufacturer: str | None = Field(default=None, max_length=160)
    volume: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    next_inspection_date: date | None = None
    spec_id: int | None = Field(default=None, ge=1)


class InspectionDocumentLineOut(ORMModel):
    id: int
    bottle_id: int | None
    source_line_id: int | None
    spec_id: int | None
    sequence: int
    device_category: str
    body_code: str
    manufacture_date: date | None
    manufacturer: str
    volume: Decimal
    next_inspection_date: date | None
    inspector_name: str | None
    inbound_at: datetime | None
    inspection_time: date | None
    inspection_result: str
    is_unverified: bool = False
    validation_error: str | None = None


class InspectionDocumentSummaryOut(ORMModel):
    source_dates: list[date]
    id: int
    document_no: str
    inspection_date: date
    source_id: int | None
    customer_name: str
    inspector_id: int | None
    inspector_name: str
    is_archived: bool
    is_retry: bool
    status: str
    created_by: int
    created_by_name: str
    total_quantity: int
    created_at: datetime
    updated_at: datetime
    voided_at: datetime | None


class InspectionDocumentOut(InspectionDocumentSummaryOut):
    lines: list[InspectionDocumentLineOut]
    export_dates: dict[str, date]


class InspectionDocumentSplitPreview(BaseModel):
    start_sequence: int = Field(ge=1)
    end_sequence: int = Field(ge=1)
    customer_id: int = Field(ge=1)
    target_document_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_sequence < self.start_sequence:
            raise ValueError("结束序号不能小于起始序号")
        return self


class InspectionDocumentSplitCreate(InspectionDocumentSplitPreview):
    expected_line_ids: list[int] = Field(min_length=1)
    expected_source_updated_at: datetime
    expected_target_id: int | None
    expected_target_updated_at: datetime | None
    confirm_create: bool = False


class InspectionDocumentSplitHistoryOut(ORMModel):
    id: int
    source_document_id: int
    target_document_id: int
    source_document_no: str
    target_document_no: str
    source_customer_name: str
    target_customer_name: str
    inspection_date: date
    start_sequence: int
    end_sequence: int
    quantity: int
    target_created: bool
    source_emptied: bool
    source_quantity_before: int
    target_quantity_before: int
    snapshot: list[dict]
    created_by_name: str
    created_at: datetime


class InspectionWordCodeUpdate(BaseModel):
    report_date: date
    first_number: int = Field(ge=1, le=998)


class InspectionWordTemplateChoiceUpdate(BaseModel):
    template_key: str


class UnverifiedBottleImport(BaseModel):
    raw_text: str = Field(min_length=1, max_length=50000)


class UnverifiedBottleImportResult(BaseModel):
    matched_sequences: list[int]
    unmatched_sequences: list[int]
    total_marked: int


class UnverifiedBottleBatchCreate(BaseModel):
    document_no: str | None = None
    body_code: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    inspection_date: date | None = None


class UnverifiedBottleOut(ORMModel):
    id: int
    inspection_document_id: int
    document_no: str
    inspection_date: date
    inspection_line_id: int
    bottle_id: int | None
    sequence: int
    body_code: str
    manufacture_date: date | None
    manufacturer: str
    spec_id: int | None
    spec_name: str | None
    volume: Decimal
    wall_thickness: Decimal | None
    inspection_price: Decimal | None
    customer_name: str
    inspector_name: str
    error_message: str
    raw_fragment: str
    status: str
    created_by: int
    created_by_name: str
    created_at: datetime
    updated_at: datetime


class BottleOutboundLineCreate(BaseModel):
    spec_id: int
    quantity: int = Field(default=0, ge=0)
    good_quantity: int = Field(default=0, ge=0)
    bad_quantity: int = Field(default=0, ge=0)
    temporary_quantity: int = Field(default=0, ge=0)
    scrap_quantity: int = Field(default=0, ge=0)
    bad_bottle_ids: list[int] = Field(default_factory=list)
    scrap_bottle_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_quantities(self):
        category_total = self.good_quantity + self.bad_quantity + self.temporary_quantity + self.scrap_quantity
        if category_total <= 0:
            if self.quantity <= 0:
                raise ValueError("出库数量必须大于零")
            self.good_quantity = self.quantity
        else:
            self.quantity = category_total
        if len(set(self.bad_bottle_ids + self.scrap_bottle_ids)) != len(self.bad_bottle_ids) + len(self.scrap_bottle_ids):
            raise ValueError("同一瓶子不能重复选择")
        if self.bad_bottle_ids and len(self.bad_bottle_ids) != self.bad_quantity:
            raise ValueError("已选不良品瓶数必须与不良品出库数量一致")
        if self.scrap_bottle_ids and len(self.scrap_bottle_ids) != self.scrap_quantity:
            raise ValueError("已选报废瓶数必须与报废出库数量一致")
        return self


class BottleOutboundAllocationOut(ORMModel):
    id: int
    bottle_id: int | None
    body_code: str
    origin_zone: str
    source_id: int
    spec_id: int
    allocation_method: str
    is_active: bool
    inspection_note: str | None = None


class BottleOutboundCreate(BaseModel):
    business_date: date
    source_id: int
    handler: str = Field(min_length=1, max_length=80)
    note: str | None = None
    lines: list[BottleOutboundLineCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_specs(self):
        if len({line.spec_id for line in self.lines}) != len(self.lines):
            raise ValueError("同一出库单不能重复选择钢瓶规格")
        return self


class BottleOutboundLineOut(ORMModel, BottleOutboundLineCreate):
    id: int
    spec_name: str
    good_adjustment_quantity: int
    bad_adjustment_quantity: int
    selected_bottles: list[BottleOutboundAllocationOut] = Field(default_factory=list)


class BottleOutboundCorrectionCreate(BaseModel):
    body_code: str = Field(min_length=1, max_length=100)
    outbound_id: int = Field(ge=1)


class BottleInventoryAdjustmentCreate(BaseModel):
    business_date: date
    source_id: int | None = None
    spec_id: int
    zone: Literal["GOOD", "TEMPORARY", "SCRAP", "BAD"]
    quantity: int
    note: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def non_zero_quantity(self):
        if self.quantity == 0:
            raise ValueError("库存调整数量不能为 0")
        return self


class BottleInventoryAdjustmentOut(ORMModel, BottleInventoryAdjustmentCreate):
    id: int
    spec_name: str
    created_by: int
    created_by_name: str
    created_at: datetime


class BottleMonthlyInventoryUpdate(BaseModel):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    source_id: int = Field(gt=0)
    spec_id: int = Field(gt=0)
    metric: Literal[
        "INBOUND_PENDING",
        "INBOUND_TEMPORARY",
        "INBOUND_SCRAP",
        "OUTBOUND_PENDING",
        "OUTBOUND_TEMPORARY",
        "OUTBOUND_SCRAP",
        "OUTBOUND_BAD",
        "BALANCE_PENDING",
        "BALANCE_TEMPORARY",
        "BALANCE_SCRAP",
        "BALANCE_BAD",
    ]
    value: int = Field(ge=0)
    reason: str | None = Field(default=None, max_length=200)


class BottleDailyInventoryUpdate(BaseModel):
    business_date: date
    source_id: int = Field(gt=0)
    spec_id: int = Field(gt=0)
    metric: Literal[
        "INBOUND_PENDING", "INBOUND_TEMPORARY", "INBOUND_SCRAP",
        "OUTBOUND_PENDING", "OUTBOUND_TEMPORARY", "OUTBOUND_SCRAP", "OUTBOUND_BAD",
        "BALANCE_PENDING", "BALANCE_TEMPORARY", "BALANCE_SCRAP", "BALANCE_BAD",
    ]
    value: int = Field(ge=0)
    reason: str | None = Field(default=None, max_length=200)


class BottleOutboundOut(ORMModel):
    id: int
    document_no: str
    business_date: date
    source_id: int | None
    customer: str
    handler: str
    note: str | None
    status: str
    total_quantity: int
    lines: list[BottleOutboundLineOut]
    created_by: int
    created_by_name: str
    created_at: datetime
    updated_by: int | None
    updated_by_name: str | None
    updated_at: datetime
    posted_by: int | None
    posted_by_name: str | None
    posted_at: datetime | None
    voided_by: int | None
    voided_by_name: str | None
    voided_at: datetime | None
