from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    role_name: Mapped[str] = mapped_column(String(80), default="业务人员")
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)


class Material(Base, TimestampMixin):
    __tablename__ = "materials"
    __table_args__ = (UniqueConstraint("name", "specification", name="uq_material_name_spec"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    material_type: Mapped[str] = mapped_column(String(20), default="MATERIAL", index=True)
    specification: Mapped[str] = mapped_column(String(200), default="")
    # Compatibility mirror for databases created before material/stock units were split.
    unit: Mapped[str] = mapped_column(String(20), default="个")
    material_unit: Mapped[str] = mapped_column(String(20), default="个")
    conversion_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    stock_unit: Mapped[str] = mapped_column(String(20), default="个")
    conversion_ratio: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=1)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    stock: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    warning_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    safety_threshold: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    supplier_prices: Mapped[list["SupplierMaterialPrice"]] = relationship(cascade="all, delete-orphan", lazy="selectin")

    @property
    def converted_stock(self) -> Optional[Decimal]:
        return self.stock * self.conversion_ratio if self.conversion_enabled else None

    @property
    def warning_stock(self) -> Decimal:
        return self.converted_stock if self.converted_stock is not None else self.stock

    @property
    def warning_status(self) -> str:
        if not self.warning_enabled:
            return "DISABLED"
        if self.safety_threshold is not None and self.warning_stock < self.safety_threshold:
            return "LOW"
        return "NORMAL"


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    contact: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    material_prices: Mapped[list["SupplierMaterialPrice"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class SupplierMaterialPrice(Base):
    __tablename__ = "supplier_material_prices"
    __table_args__ = (UniqueConstraint("supplier_id", "material_id", name="uq_supplier_material_price"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"), index=True)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    supplier: Mapped[Supplier] = relationship(back_populates="material_prices")
    material: Mapped[Material] = relationship(back_populates="supplier_prices")

    @property
    def supplier_name(self) -> str:
        return self.supplier.name

    @property
    def material_name(self) -> str:
        return self.material.name

    @property
    def specification(self) -> str:
        return self.material.specification

    @property
    def material_type(self) -> str:
        return self.material.material_type

    @property
    def unit(self) -> str:
        return self.material.material_unit


class BottleSource(Base, TimestampMixin):
    __tablename__ = "bottle_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    contact: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class BottleSpec(Base, TimestampMixin):
    __tablename__ = "bottle_specs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    inspection_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    volume: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    wall_thickness: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class QuickConfig(Base, TimestampMixin):
    __tablename__ = "quick_configs"
    __table_args__ = (UniqueConstraint("category", "value", name="uq_quick_config_category_value"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class BottleManufacturer(Base, TimestampMixin):
    __tablename__ = "bottle_manufacturers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    # 瓶身编号前缀，多个前缀用英文逗号分隔，快捷抄码按它们自动匹配生产厂家；留空表示不参与自动匹配。
    code_prefix: Mapped[str] = mapped_column(String(200), default="", index=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    order_date: Mapped[date] = mapped_column(Date, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    handler: Mapped[str] = mapped_column(String(80))
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", index=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    confirmed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    voided_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    supplier: Mapped[Supplier] = relationship()
    creator: Mapped[User] = relationship(foreign_keys=[created_by])
    editor: Mapped[Optional[User]] = relationship(foreign_keys=[updated_by])
    confirmer: Mapped[Optional[User]] = relationship(foreign_keys=[confirmed_by])
    voider: Mapped[Optional[User]] = relationship(foreign_keys=[voided_by])
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    inbound_documents: Mapped[list["MaterialDocument"]] = relationship(back_populates="purchase_order", lazy="selectin")

    @property
    def supplier_name(self) -> str:
        return self.supplier.name

    @property
    def total_amount(self) -> Decimal:
        return sum((line.amount for line in self.lines), Decimal(0))

    @property
    def inbound_document_id(self) -> Optional[int]:
        active = next((item for item in self.inbound_documents if item.status != "VOID"), None)
        return active.id if active else None

    @property
    def created_by_name(self) -> str:
        return self.creator.name

    @property
    def updated_by_name(self) -> Optional[str]:
        return self.editor.name if self.editor else None

    @property
    def confirmed_by_name(self) -> Optional[str]:
        return self.confirmer.name if self.confirmer else None

    @property
    def voided_by_name(self) -> Optional[str]:
        return self.voider.name if self.voider else None


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    material_name: Mapped[str] = mapped_column(String(120))
    specification: Mapped[str] = mapped_column(String(200), default="")
    unit: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    material: Mapped[Material] = relationship()


class MaterialDocument(Base, TimestampMixin):
    __tablename__ = "material_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    document_type: Mapped[str] = mapped_column(String(20), index=True)
    business_date: Mapped[date] = mapped_column(Date, index=True)
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    purchase_order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("purchase_orders.id"), nullable=True, index=True)
    related_outbound_id: Mapped[Optional[int]] = mapped_column(ForeignKey("material_documents.id"), nullable=True)
    inbound_mode: Mapped[str] = mapped_column(String(20), default="DIRECT", index=True)
    inbound_category: Mapped[str] = mapped_column(String(20), default="MATERIAL")
    outbound_category: Mapped[str] = mapped_column(String(20), default="MATERIAL")
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    handler: Mapped[str] = mapped_column(String(80))
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    posted_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    voided_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    supplier: Mapped[Optional[Supplier]] = relationship()
    purchase_order: Mapped[Optional[PurchaseOrder]] = relationship(back_populates="inbound_documents")
    related_outbound: Mapped[Optional["MaterialDocument"]] = relationship(remote_side="MaterialDocument.id")
    creator: Mapped[User] = relationship(foreign_keys=[created_by])
    editor: Mapped[Optional[User]] = relationship(foreign_keys=[updated_by])
    approver: Mapped[Optional[User]] = relationship(foreign_keys=[posted_by])
    voider: Mapped[Optional[User]] = relationship(foreign_keys=[voided_by])
    lines: Mapped[list["MaterialDocumentLine"]] = relationship(cascade="all, delete-orphan", lazy="selectin")

    @property
    def created_by_name(self) -> str:
        return self.creator.name

    @property
    def posted_by_name(self) -> Optional[str]:
        return self.approver.name if self.approver else None

    @property
    def updated_by_name(self) -> Optional[str]:
        return self.editor.name if self.editor else None

    @property
    def voided_by_name(self) -> Optional[str]:
        return self.voider.name if self.voider else None


class MaterialDocumentLine(Base):
    __tablename__ = "material_document_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("material_documents.id", ondelete="CASCADE"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    material_name: Mapped[str] = mapped_column(String(120))
    specification: Mapped[str] = mapped_column(String(200), default="")
    unit: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    material: Mapped[Material] = relationship()


class MaterialMovement(Base):
    __tablename__ = "material_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("material_documents.id"), index=True)
    movement_type: Mapped[str] = mapped_column(String(20))
    quantity_change: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class BottleInbound(Base, TimestampMixin):
    __tablename__ = "bottle_inbounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    business_date: Mapped[date] = mapped_column(Date, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("bottle_sources.id"), index=True)
    pending_quantity: Mapped[int] = mapped_column(default=0)
    temporary_quantity: Mapped[int] = mapped_column(default=0)
    scrap_quantity: Mapped[int] = mapped_column(default=0)
    handler: Mapped[str] = mapped_column(String(80))
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    source: Mapped[BottleSource] = relationship()
    bottles: Mapped[list["Bottle"]] = relationship(lazy="selectin")
    lines: Mapped[list["BottleInboundLine"]] = relationship(cascade="all, delete-orphan", lazy="selectin")

    @property
    def total_quantity(self) -> int:
        return self.pending_quantity + self.temporary_quantity + self.scrap_quantity


class BottleInboundLine(Base):
    __tablename__ = "bottle_inbound_lines"
    __table_args__ = (UniqueConstraint("inbound_id", "spec_id", name="uq_bottle_inbound_spec"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    inbound_id: Mapped[int] = mapped_column(ForeignKey("bottle_inbounds.id", ondelete="CASCADE"), index=True)
    spec_id: Mapped[int] = mapped_column(ForeignKey("bottle_specs.id"), index=True)
    pending_quantity: Mapped[int] = mapped_column(default=0)
    temporary_quantity: Mapped[int] = mapped_column(default=0)
    scrap_quantity: Mapped[int] = mapped_column(default=0)

    spec: Mapped[BottleSpec] = relationship()

    @property
    def spec_name(self) -> str:
        return self.spec.name

    @property
    def total_quantity(self) -> int:
        return self.pending_quantity + self.temporary_quantity + self.scrap_quantity


class Bottle(Base, TimestampMixin):
    __tablename__ = "bottles"

    id: Mapped[int] = mapped_column(primary_key=True)
    inbound_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bottle_inbounds.id"), nullable=True, index=True)
    body_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    manufacture_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("bottle_sources.id"), index=True)
    coding_customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bottle_sources.id"), nullable=True, index=True)
    spec_id: Mapped[int] = mapped_column(ForeignKey("bottle_specs.id"), index=True)
    inspection_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    zone: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    process_status: Mapped[str] = mapped_column(String(30), default="CODED", index=True)
    coding_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    coding_sequence: Mapped[Optional[int]] = mapped_column(nullable=True)
    coding_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 抄码时保存的生产厂家名称快照，供检验气瓶导出使用。
    manufacturer: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    # 进入良品库的业务日期（北京时间），导出检验气瓶按此日期筛选。
    good_entry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    outbound_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bottle_outbounds.id"), nullable=True, index=True)
    outbound_origin_zone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    coded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    coded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    inspection_result: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    inspected_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    inspected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    inspection_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    returned_to_customer: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    inbound: Mapped[Optional[BottleInbound]] = relationship(back_populates="bottles")
    source: Mapped[BottleSource] = relationship(foreign_keys=[source_id])
    coding_customer: Mapped[Optional[BottleSource]] = relationship(foreign_keys=[coding_customer_id])

    @property
    def effective_coding_customer_id(self) -> int:
        return self.coding_customer_id or self.source_id

    @property
    def coding_customer_name(self) -> str:
        return (self.coding_customer or self.source).name
    spec: Mapped[BottleSpec] = relationship()

    @property
    def coded_by_name(self) -> str:
        return self.coder.name

    coder: Mapped[User] = relationship(foreign_keys=[coded_by])
    inspection_lines: Mapped[list["InspectionDocumentLine"]] = relationship(back_populates="bottle", lazy="selectin")

    @property
    def inspection_document_status(self) -> str:
        return "INSPECTED" if any(line.document.status == "ACTIVE" for line in self.inspection_lines) else "UNINSPECTED"

    @property
    def inspection_document_no(self) -> Optional[str]:
        line = next((line for line in self.inspection_lines if line.document.status == "ACTIVE"), None)
        return line.document.document_no if line else None


class InspectionDocument(Base, TimestampMixin):
    __tablename__ = "inspection_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    inspection_date: Mapped[date] = mapped_column(Date, index=True)
    generation_dates: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bottle_sources.id"), nullable=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(160), default="")
    inspector_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    inspector_name: Mapped[str] = mapped_column(String(80), default="")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    is_retry: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    voided_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    creator: Mapped[User] = relationship(foreign_keys=[created_by])
    lines: Mapped[list["InspectionDocumentLine"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", lazy="selectin", order_by="InspectionDocumentLine.sequence"
    )
    export_records: Mapped[list["InspectionDocumentExportRecord"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    word_assignments: Mapped[list["InspectionWordExportAssignment"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    @property
    def source_dates(self) -> list[date]:
        return [date.fromisoformat(value) for value in self.generation_dates] if self.generation_dates else [self.inspection_date]

    @property
    def export_dates(self) -> dict[str, date]:
        return {record.kind: record.export_date for record in self.export_records}

    @property
    def created_by_name(self) -> str:
        return self.creator.name

    @property
    def total_quantity(self) -> int:
        return len(self.lines)


class InspectionDocumentSplitHistory(Base):
    __tablename__ = "inspection_document_split_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("inspection_documents.id"), index=True)
    target_document_id: Mapped[int] = mapped_column(ForeignKey("inspection_documents.id"), index=True)
    source_document_no: Mapped[str] = mapped_column(String(40))
    target_document_no: Mapped[str] = mapped_column(String(40))
    source_customer_name: Mapped[str] = mapped_column(String(160))
    target_customer_name: Mapped[str] = mapped_column(String(160))
    inspection_date: Mapped[date] = mapped_column(Date)
    start_sequence: Mapped[int] = mapped_column()
    end_sequence: Mapped[int] = mapped_column()
    quantity: Mapped[int] = mapped_column()
    target_created: Mapped[bool] = mapped_column(Boolean)
    source_emptied: Mapped[bool] = mapped_column(Boolean)
    source_quantity_before: Mapped[int] = mapped_column()
    target_quantity_before: Mapped[int] = mapped_column()
    snapshot: Mapped[list[dict]] = mapped_column(JSON)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    creator: Mapped[User] = relationship()

    @property
    def created_by_name(self) -> str:
        return self.creator.name


class InspectionDocumentExportRecord(Base, TimestampMixin):
    __tablename__ = "inspection_document_export_records"
    __table_args__ = (UniqueConstraint("document_id", "kind", name="uq_inspection_document_export_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("inspection_documents.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(80))
    export_date: Mapped[date] = mapped_column(Date)

    document: Mapped[InspectionDocument] = relationship(back_populates="export_records")


class InspectionWordTemplateChoice(Base, TimestampMixin):
    __tablename__ = "inspection_word_template_choices"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    template_key: Mapped[str] = mapped_column(String(40), default="default")


class InspectionWordDailyCounter(Base):
    __tablename__ = "inspection_word_daily_counters"

    report_date: Mapped[date] = mapped_column(Date, primary_key=True)
    last_number: Mapped[int] = mapped_column(default=0)


class InspectionWordReleasedPair(Base):
    __tablename__ = "inspection_word_released_pairs"

    report_date: Mapped[date] = mapped_column(Date, primary_key=True)
    first_number: Mapped[int] = mapped_column(primary_key=True)


class InspectionWordExportAssignment(Base, TimestampMixin):
    __tablename__ = "inspection_word_export_assignments"
    __table_args__ = (
        UniqueConstraint("document_id", "report_date", name="uq_inspection_word_document_date"),
        UniqueConstraint("report_date", "first_number", name="uq_inspection_word_date_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("inspection_documents.id", ondelete="CASCADE"), index=True)
    report_date: Mapped[date] = mapped_column(Date, index=True)
    first_number: Mapped[int] = mapped_column()

    document: Mapped[InspectionDocument] = relationship(back_populates="word_assignments")


class InspectionDocumentLine(Base):
    __tablename__ = "inspection_document_lines"
    __table_args__ = (UniqueConstraint("document_id", "bottle_id", name="uq_inspection_document_bottle"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("inspection_documents.id", ondelete="CASCADE"), index=True)
    bottle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bottles.id"), index=True, nullable=True)
    source_line_id: Mapped[Optional[int]] = mapped_column(ForeignKey("inspection_document_lines.id"), nullable=True)
    spec_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bottle_specs.id"), nullable=True)
    sequence: Mapped[int] = mapped_column()
    device_category: Mapped[str] = mapped_column(String(80), default="焊接气瓶")
    body_code: Mapped[str] = mapped_column(String(100))
    manufacture_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    manufacturer: Mapped[str] = mapped_column(String(160), default="")
    volume: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    next_inspection_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    inspector_name: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    inspection_time: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    inspected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    inspection_result: Mapped[str] = mapped_column(String(20), default="GOOD")

    document: Mapped[InspectionDocument] = relationship(back_populates="lines")
    bottle: Mapped[Optional[Bottle]] = relationship(back_populates="inspection_lines")
    source_line: Mapped[Optional["InspectionDocumentLine"]] = relationship(
        remote_side=[id], foreign_keys=[source_line_id]
    )
    spec: Mapped[Optional[BottleSpec]] = relationship()
    unverified_record: Mapped[Optional["UnverifiedBottle"]] = relationship(back_populates="inspection_line", uselist=False, lazy="selectin")

    @property
    def is_unverified(self) -> bool:
        return bool(self.unverified_record and self.unverified_record.status in ("PENDING", "RETRYING"))

    @property
    def inbound_at(self) -> Optional[datetime]:
        if self.bottle:
            return self.bottle.coded_at or self.bottle.created_at or self.document.created_at
        if self.source_line:
            return self.source_line.inbound_at or self.document.created_at
        return self.document.created_at

    @property
    def validation_error(self) -> Optional[str]:
        return self.unverified_record.error_message if self.is_unverified else None


class UnverifiedBottle(Base, TimestampMixin):
    __tablename__ = "unverified_bottles"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_document_id: Mapped[int] = mapped_column(ForeignKey("inspection_documents.id"), index=True)
    inspection_line_id: Mapped[int] = mapped_column(ForeignKey("inspection_document_lines.id"), unique=True, index=True)
    bottle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bottles.id"), index=True, nullable=True)
    sequence: Mapped[int] = mapped_column()
    body_code: Mapped[str] = mapped_column(String(100), index=True)
    manufacture_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    manufacturer: Mapped[str] = mapped_column(String(160), default="")
    error_message: Mapped[str] = mapped_column(Text)
    raw_fragment: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    inspection_document: Mapped[InspectionDocument] = relationship()
    inspection_line: Mapped[InspectionDocumentLine] = relationship(back_populates="unverified_record")
    bottle: Mapped[Optional[Bottle]] = relationship()
    creator: Mapped[User] = relationship()

    @property
    def document_no(self) -> str:
        return self.inspection_document.document_no

    @property
    def inspection_date(self) -> date:
        return self.inspection_document.inspection_date

    @property
    def customer_name(self) -> str:
        return self.inspection_document.customer_name

    @property
    def inspector_name(self) -> str:
        return self.inspection_document.inspector_name

    @property
    def spec(self) -> Optional[BottleSpec]:
        return self.inspection_line.spec or (self.bottle.spec if self.bottle else None)

    @property
    def spec_id(self) -> Optional[int]:
        return self.spec.id if self.spec else None

    @property
    def spec_name(self) -> Optional[str]:
        return self.spec.name if self.spec else None

    @property
    def volume(self) -> Decimal:
        return self.inspection_line.volume

    @property
    def wall_thickness(self) -> Optional[Decimal]:
        return self.spec.wall_thickness if self.spec else None

    @property
    def inspection_price(self) -> Optional[Decimal]:
        return self.spec.inspection_price if self.spec else None

    @property
    def created_by_name(self) -> str:
        return self.creator.name


class BottleOutbound(Base, TimestampMixin):
    __tablename__ = "bottle_outbounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    business_date: Mapped[date] = mapped_column(Date, index=True)
    source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bottle_sources.id"), nullable=True, index=True)
    customer: Mapped[str] = mapped_column(String(160), index=True)
    handler: Mapped[str] = mapped_column(String(80))
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    posted_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    voided_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    lines: Mapped[list["BottleOutboundLine"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    source: Mapped[Optional[BottleSource]] = relationship()
    creator: Mapped[User] = relationship(foreign_keys=[created_by])
    editor: Mapped[Optional[User]] = relationship(foreign_keys=[updated_by])
    approver: Mapped[Optional[User]] = relationship(foreign_keys=[posted_by])
    voider: Mapped[Optional[User]] = relationship(foreign_keys=[voided_by])

    @property
    def total_quantity(self) -> int:
        return sum(line.quantity for line in self.lines)

    @property
    def created_by_name(self) -> str:
        return self.creator.name

    @property
    def updated_by_name(self) -> Optional[str]:
        return self.editor.name if self.editor else None

    @property
    def posted_by_name(self) -> Optional[str]:
        return self.approver.name if self.approver else None

    @property
    def voided_by_name(self) -> Optional[str]:
        return self.voider.name if self.voider else None


class BottleOutboundLine(Base):
    __tablename__ = "bottle_outbound_lines"
    __table_args__ = (UniqueConstraint("outbound_id", "spec_id", name="uq_bottle_outbound_spec"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    outbound_id: Mapped[int] = mapped_column(ForeignKey("bottle_outbounds.id", ondelete="CASCADE"), index=True)
    spec_id: Mapped[int] = mapped_column(ForeignKey("bottle_specs.id"), index=True)
    quantity: Mapped[int] = mapped_column()
    good_quantity: Mapped[int] = mapped_column(default=0)
    good_adjustment_quantity: Mapped[int] = mapped_column(default=0)
    bad_quantity: Mapped[int] = mapped_column(default=0)
    bad_adjustment_quantity: Mapped[int] = mapped_column(default=0)
    temporary_quantity: Mapped[int] = mapped_column(default=0)
    scrap_quantity: Mapped[int] = mapped_column(default=0)
    spec: Mapped[BottleSpec] = relationship()
    allocations: Mapped[list["BottleOutboundAllocation"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", back_populates="line"
    )

    @property
    def spec_name(self) -> str:
        return self.spec.name

    @property
    def selected_bottles(self) -> list["BottleOutboundAllocation"]:
        return list(self.allocations)

    @property
    def bad_bottle_ids(self) -> list[int]:
        return [item.bottle_id for item in self.allocations if item.origin_zone == "BAD" and item.bottle_id]

    @property
    def scrap_bottle_ids(self) -> list[int]:
        return [item.bottle_id for item in self.allocations if item.origin_zone == "SCRAP" and item.bottle_id]


class BottleOutboundAllocation(Base):
    """Immutable bottle-number snapshot bound to an outbound line."""
    __tablename__ = "bottle_outbound_allocations"
    __table_args__ = (UniqueConstraint("outbound_id", "bottle_id", name="uq_bottle_outbound_allocation"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    outbound_id: Mapped[int] = mapped_column(ForeignKey("bottle_outbounds.id", ondelete="CASCADE"), index=True)
    line_id: Mapped[int] = mapped_column(ForeignKey("bottle_outbound_lines.id", ondelete="CASCADE"), index=True)
    bottle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bottles.id"), nullable=True, index=True)
    body_code: Mapped[str] = mapped_column(String(100), index=True)
    origin_zone: Mapped[str] = mapped_column(String(20), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("bottle_sources.id"), index=True)
    spec_id: Mapped[int] = mapped_column(ForeignKey("bottle_specs.id"), index=True)
    allocation_method: Mapped[str] = mapped_column(String(20), default="SELECTED")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    line: Mapped[BottleOutboundLine] = relationship(back_populates="allocations")
    bottle: Mapped[Optional[Bottle]] = relationship()

    @property
    def inspection_note(self) -> Optional[str]:
        return self.bottle.inspection_note if self.bottle else None


class BottleOutboundCorrection(Base):
    __tablename__ = "bottle_outbound_corrections"

    id: Mapped[int] = mapped_column(primary_key=True)
    outbound_id: Mapped[int] = mapped_column(index=True)
    outbound_document_no: Mapped[str] = mapped_column(String(40))
    original_bottle_id: Mapped[int] = mapped_column(index=True)
    original_body_code: Mapped[str] = mapped_column(String(100), index=True)
    replacement_bottle_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    replacement_body_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    replacement_type: Mapped[str] = mapped_column(String(20))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    creator: Mapped[User] = relationship()


class BottleInventoryAdjustment(Base, TimestampMixin):
    __tablename__ = "bottle_inventory_adjustments"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_date: Mapped[date] = mapped_column(Date, index=True)
    source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bottle_sources.id"), nullable=True, index=True)
    spec_id: Mapped[int] = mapped_column(ForeignKey("bottle_specs.id"), index=True)
    zone: Mapped[str] = mapped_column(String(20), index=True)
    quantity: Mapped[int] = mapped_column()
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    spec: Mapped[BottleSpec] = relationship()
    source: Mapped[Optional[BottleSource]] = relationship()
    creator: Mapped[User] = relationship()

    @property
    def spec_name(self) -> str:
        return self.spec.name

    @property
    def created_by_name(self) -> str:
        return self.creator.name


class BottleMonthlyInventoryOverride(Base, TimestampMixin):
    __tablename__ = "bottle_monthly_inventory_overrides"
    __table_args__ = (
        UniqueConstraint("month", "source_id", "spec_id", "metric", name="uq_bottle_monthly_inventory_override"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[date] = mapped_column(Date, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("bottle_sources.id"), index=True)
    spec_id: Mapped[int] = mapped_column(ForeignKey("bottle_specs.id"), index=True)
    metric: Mapped[str] = mapped_column(String(20), index=True)
    value: Mapped[int] = mapped_column()
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    source: Mapped[BottleSource] = relationship()
    spec: Mapped[BottleSpec] = relationship()
    editor: Mapped[User] = relationship()


class BottleMonthlyInventoryLog(Base):
    __tablename__ = "bottle_monthly_inventory_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[date] = mapped_column(Date, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("bottle_sources.id"), index=True)
    spec_id: Mapped[int] = mapped_column(ForeignKey("bottle_specs.id"), index=True)
    metric: Mapped[str] = mapped_column(String(20), index=True)
    old_value: Mapped[int] = mapped_column()
    new_value: Mapped[int] = mapped_column()
    reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    source: Mapped[BottleSource] = relationship()
    spec: Mapped[BottleSpec] = relationship()
    creator: Mapped[User] = relationship()


class BottleDailyInventoryOverride(Base, TimestampMixin):
    __tablename__ = "bottle_daily_inventory_overrides"
    __table_args__ = (UniqueConstraint("business_date", "source_id", "spec_id", "metric", name="uq_bottle_daily_inventory_override"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_date: Mapped[date] = mapped_column(Date, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("bottle_sources.id"), index=True)
    spec_id: Mapped[int] = mapped_column(ForeignKey("bottle_specs.id"), index=True)
    metric: Mapped[str] = mapped_column(String(20), index=True)
    value: Mapped[int] = mapped_column()
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class BottleDailyInventoryLog(Base):
    __tablename__ = "bottle_daily_inventory_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_date: Mapped[date] = mapped_column(Date, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("bottle_sources.id"), index=True)
    spec_id: Mapped[int] = mapped_column(ForeignKey("bottle_specs.id"), index=True)
    metric: Mapped[str] = mapped_column(String(20), index=True)
    old_value: Mapped[int] = mapped_column()
    new_value: Mapped[int] = mapped_column()
    reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    source: Mapped[BottleSource] = relationship()
    spec: Mapped[BottleSpec] = relationship()
    creator: Mapped[User] = relationship()


class MaterialDailyEntry(Base):
    __tablename__ = "material_daily_entries"
    __table_args__ = (UniqueConstraint("material_id", "business_date", name="uq_material_daily_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    business_date: Mapped[date] = mapped_column(Date, index=True)
    inbound: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    outbound: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    version: Mapped[int] = mapped_column(default=0)


class MaterialDailyLog(Base):
    __tablename__ = "material_daily_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    business_date: Mapped[date] = mapped_column(Date, index=True)
    material_name: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(20))
    old_inbound: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    old_outbound: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    inbound: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    outbound: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    operator_name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MenuConfiguration(Base):
    __tablename__ = "menu_configuration"

    id: Mapped[int] = mapped_column(primary_key=True)
    groups: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(default=1)
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApplicationMigration(Base):
    __tablename__ = "application_migrations"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
