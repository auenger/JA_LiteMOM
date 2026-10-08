from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, select, text

from .api import router
from .material_daily import router as material_daily_router
from .menu_settings import router as menu_settings_router
from .bottle_receipt import router as bottle_receipt_router
from .config import settings
from .database import Base, SessionLocal, engine
from .models import InspectionDocument, User
from .security import hash_password
from .permissions import migrate_page_permissions


def allow_archived_inspection_lines_sqlite() -> None:
    """SQLite cannot drop NOT NULL in place; rebuild only the two affected tables."""
    inspector = inspect(engine)
    line_column = next(column for column in inspector.get_columns("inspection_document_lines") if column["name"] == "bottle_id")
    unverified_column = next(column for column in inspector.get_columns("unverified_bottles") if column["name"] == "bottle_id")
    if line_column["nullable"] and unverified_column["nullable"]:
        return
    connection = engine.raw_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("BEGIN")
        if not line_column["nullable"]:
            cursor.execute("""
                CREATE TABLE inspection_document_lines_migrated (
                    id INTEGER NOT NULL PRIMARY KEY,
                    document_id INTEGER NOT NULL REFERENCES inspection_documents(id) ON DELETE CASCADE,
                    bottle_id INTEGER REFERENCES bottles(id),
                    source_line_id INTEGER REFERENCES inspection_document_lines(id),
                    spec_id INTEGER REFERENCES bottle_specs(id),
                    sequence INTEGER NOT NULL,
                    device_category VARCHAR(80) DEFAULT '焊接气瓶' NOT NULL,
                    body_code VARCHAR(100) NOT NULL,
                    manufacture_date DATE,
                    manufacturer VARCHAR(160) NOT NULL,
                    volume NUMERIC(18, 2) NOT NULL,
                    next_inspection_date DATE,
                    inspector_name VARCHAR(80),
                    inspection_time DATE,
                    inspected_at DATETIME,
                    inspection_result VARCHAR(20) NOT NULL,
                    CONSTRAINT uq_inspection_document_bottle UNIQUE(document_id, bottle_id)
                )
            """)
            cursor.execute("""
                INSERT INTO inspection_document_lines_migrated
                SELECT id, document_id, bottle_id, source_line_id, spec_id, sequence, device_category, body_code,
                       manufacture_date, manufacturer, volume, next_inspection_date,
                       inspector_name, inspection_time, inspected_at, inspection_result
                FROM inspection_document_lines
            """)
            cursor.execute("DROP TABLE inspection_document_lines")
            cursor.execute("ALTER TABLE inspection_document_lines_migrated RENAME TO inspection_document_lines")
            cursor.execute("CREATE INDEX ix_inspection_document_lines_document_id ON inspection_document_lines(document_id)")
            cursor.execute("CREATE INDEX ix_inspection_document_lines_bottle_id ON inspection_document_lines(bottle_id)")
        if not unverified_column["nullable"]:
            cursor.execute("""
                CREATE TABLE unverified_bottles_migrated (
                    id INTEGER NOT NULL PRIMARY KEY,
                    inspection_document_id INTEGER NOT NULL REFERENCES inspection_documents(id),
                    inspection_line_id INTEGER NOT NULL REFERENCES inspection_document_lines(id),
                    bottle_id INTEGER REFERENCES bottles(id),
                    sequence INTEGER NOT NULL,
                    body_code VARCHAR(100) NOT NULL,
                    manufacture_date DATE,
                    manufacturer VARCHAR(160) NOT NULL,
                    error_message TEXT NOT NULL,
                    raw_fragment TEXT NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    created_by INTEGER NOT NULL REFERENCES users(id),
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
            """)
            cursor.execute("INSERT INTO unverified_bottles_migrated SELECT * FROM unverified_bottles")
            cursor.execute("DROP TABLE unverified_bottles")
            cursor.execute("ALTER TABLE unverified_bottles_migrated RENAME TO unverified_bottles")
            cursor.execute("CREATE INDEX ix_unverified_bottles_inspection_document_id ON unverified_bottles(inspection_document_id)")
            cursor.execute("CREATE UNIQUE INDEX ix_unverified_bottles_inspection_line_id ON unverified_bottles(inspection_line_id)")
            cursor.execute("CREATE INDEX ix_unverified_bottles_bottle_id ON unverified_bottles(bottle_id)")
            cursor.execute("CREATE INDEX ix_unverified_bottles_body_code ON unverified_bottles(body_code)")
            cursor.execute("CREATE INDEX ix_unverified_bottles_status ON unverified_bottles(status)")
        if cursor.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("SQLite 检验单归档字段迁移后外键校验失败")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.close()


def initialize_database():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("materials")}
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    document_columns = {column["name"] for column in inspector.get_columns("material_documents")}
    bottle_column_info = inspector.get_columns("bottles")
    bottle_columns = {column["name"] for column in bottle_column_info}
    bottle_outbound_columns = {column["name"] for column in inspector.get_columns("bottle_outbounds")}
    bottle_outbound_line_columns = {column["name"] for column in inspector.get_columns("bottle_outbound_lines")}
    bottle_adjustment_columns = {column["name"] for column in inspector.get_columns("bottle_inventory_adjustments")}
    spec_columns = {column["name"] for column in inspector.get_columns("bottle_specs")}
    inspection_document_columns = {column["name"] for column in inspector.get_columns("inspection_documents")}
    inspection_line_columns = {column["name"] for column in inspector.get_columns("inspection_document_lines")}
    manufacture_date_nullable = next((column["nullable"] for column in bottle_column_info if column["name"] == "manufacture_date"), True)
    inbound_id_nullable = next((column["nullable"] for column in bottle_column_info if column["name"] == "inbound_id"), True)
    additions = {
        "material_type": "VARCHAR(20) DEFAULT 'MATERIAL' NOT NULL",
        "material_unit": "VARCHAR(20) DEFAULT '个' NOT NULL",
        "conversion_enabled": "BOOLEAN DEFAULT FALSE NOT NULL",
        "stock_unit": "VARCHAR(20) DEFAULT '个' NOT NULL",
        "conversion_ratio": "NUMERIC(18, 2) DEFAULT 1 NOT NULL",
    }
    with engine.begin() as connection:
        if "role_name" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN role_name VARCHAR(80) DEFAULT '业务人员' NOT NULL"))
            connection.execute(text("UPDATE users SET role_name = '超级管理员' WHERE is_superadmin = TRUE"))
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE materials ADD COLUMN {name} {definition}"))
                if name == "material_type":
                    connection.execute(text("CREATE INDEX ix_materials_material_type ON materials (material_type)"))
        if "unit" in columns and ("material_unit" not in columns or "stock_unit" not in columns):
            connection.execute(text("UPDATE materials SET material_unit = unit, stock_unit = unit"))
        for name in ("updated_by", "posted_by", "voided_by"):
            if name not in document_columns:
                connection.execute(text(f"ALTER TABLE material_documents ADD COLUMN {name} INTEGER"))
        if "is_paid" not in document_columns:
            connection.execute(text("ALTER TABLE material_documents ADD COLUMN is_paid BOOLEAN DEFAULT FALSE NOT NULL"))
        if "inbound_category" not in document_columns:
            connection.execute(text("ALTER TABLE material_documents ADD COLUMN inbound_category VARCHAR(20) DEFAULT 'PURCHASE' NOT NULL"))
        if "outbound_category" not in document_columns:
            connection.execute(text("ALTER TABLE material_documents ADD COLUMN outbound_category VARCHAR(20) DEFAULT 'MATERIAL' NOT NULL"))
        if "purchase_order_id" not in document_columns:
            connection.execute(text("ALTER TABLE material_documents ADD COLUMN purchase_order_id INTEGER"))
            connection.execute(text("CREATE INDEX ix_material_documents_purchase_order_id ON material_documents (purchase_order_id)"))
        if "inbound_mode" not in document_columns:
            connection.execute(text("ALTER TABLE material_documents ADD COLUMN inbound_mode VARCHAR(20) DEFAULT 'DIRECT' NOT NULL"))
            connection.execute(text("CREATE INDEX ix_material_documents_inbound_mode ON material_documents (inbound_mode)"))
            connection.execute(text("UPDATE material_documents SET inbound_mode = 'PURCHASE_ORDER' WHERE inbound_category = 'PURCHASE_ORDER'"))
            connection.execute(text("UPDATE material_documents SET inbound_category = 'MATERIAL' WHERE inbound_category IN ('DIRECT', 'PURCHASE_ORDER')"))
        bottle_additions = {
            "coding_date": "DATE",
            "coding_sequence": "INTEGER",
            "coding_note": "TEXT",
            "coding_customer_id": "INTEGER REFERENCES bottle_sources(id)",
            "manufacturer": "VARCHAR(160)",
            "good_entry_date": "DATE",
            "outbound_id": "INTEGER",
            "outbound_origin_zone": "VARCHAR(20)",
            "returned_to_customer": "BOOLEAN",
        }
        for name, definition in bottle_additions.items():
            if name not in bottle_columns:
                connection.execute(text(f"ALTER TABLE bottles ADD COLUMN {name} {definition}"))
        # 历史良品数据用抄码业务日期（北京时间）回填进入良品库日期。
        connection.execute(text("UPDATE bottles SET good_entry_date = coding_date WHERE good_entry_date IS NULL AND zone = 'GOOD' AND coding_date IS NOT NULL"))
        if engine.dialect.name == "sqlite" and (not manufacture_date_nullable or not inbound_id_nullable):
            connection.execute(text("""
                CREATE TABLE bottles_migrated (
                    id INTEGER NOT NULL PRIMARY KEY,
                    inbound_id INTEGER REFERENCES bottle_inbounds(id),
                    body_code VARCHAR(100) NOT NULL,
                    manufacture_date DATE,
                    source_id INTEGER NOT NULL REFERENCES bottle_sources(id),
                    spec_id INTEGER NOT NULL REFERENCES bottle_specs(id),
                    inspection_price NUMERIC(18, 2) NOT NULL,
                    zone VARCHAR(20) NOT NULL,
                    process_status VARCHAR(30) NOT NULL,
                    coding_date DATE,
                    coding_sequence INTEGER,
                    coding_note TEXT,
                    coding_customer_id INTEGER REFERENCES bottle_sources(id),
                    manufacturer VARCHAR(160),
                    good_entry_date DATE,
                    outbound_id INTEGER REFERENCES bottle_outbounds(id),
                    outbound_origin_zone VARCHAR(20),
                    coded_by INTEGER NOT NULL REFERENCES users(id),
                    coded_at DATETIME NOT NULL,
                    inspection_result VARCHAR(20),
                    inspected_by INTEGER REFERENCES users(id),
                    inspected_at DATETIME,
                    inspection_note TEXT,
                    returned_to_customer BOOLEAN,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
            """))
            connection.execute(text("""
                INSERT INTO bottles_migrated (
                    id, inbound_id, body_code, manufacture_date, source_id, spec_id,
                    inspection_price, zone, process_status, coding_date, coding_sequence,
                    coding_note, coding_customer_id, manufacturer, good_entry_date, outbound_id, outbound_origin_zone, coded_by, coded_at, inspection_result,
                    inspected_by, inspected_at, inspection_note, returned_to_customer, created_at, updated_at
                )
                SELECT id, inbound_id, body_code, manufacture_date, source_id, spec_id,
                    inspection_price, zone, process_status, coding_date, coding_sequence,
                    coding_note, coding_customer_id, manufacturer, good_entry_date, outbound_id, outbound_origin_zone, coded_by, coded_at, inspection_result,
                    inspected_by, inspected_at, inspection_note, returned_to_customer, created_at, updated_at
                FROM bottles
            """))
            connection.execute(text("DROP TABLE bottles"))
            connection.execute(text("ALTER TABLE bottles_migrated RENAME TO bottles"))
            connection.execute(text("CREATE UNIQUE INDEX ix_bottles_body_code ON bottles (body_code)"))
            for column_name in ("inbound_id", "source_id", "spec_id", "zone", "process_status", "coding_date", "outbound_id"):
                connection.execute(text(f"CREATE INDEX ix_bottles_{column_name} ON bottles ({column_name})"))
        if "source_id" not in bottle_outbound_columns:
            connection.execute(text("ALTER TABLE bottle_outbounds ADD COLUMN source_id INTEGER"))
        if "source_id" not in bottle_adjustment_columns:
            connection.execute(text("ALTER TABLE bottle_inventory_adjustments ADD COLUMN source_id INTEGER REFERENCES bottle_sources(id)"))
            connection.execute(text("CREATE INDEX ix_bottle_inventory_adjustments_source_id ON bottle_inventory_adjustments (source_id)"))
        if "volume" not in spec_columns:
            connection.execute(text("ALTER TABLE bottle_specs ADD COLUMN volume NUMERIC(18, 2) DEFAULT 0 NOT NULL"))
        if "wall_thickness" not in spec_columns:
            connection.execute(text("ALTER TABLE bottle_specs ADD COLUMN wall_thickness NUMERIC(18, 2) DEFAULT 0 NOT NULL"))
        if "is_archived" not in inspection_document_columns:
            connection.execute(text("ALTER TABLE inspection_documents ADD COLUMN is_archived BOOLEAN DEFAULT FALSE NOT NULL"))
        if "generation_dates" not in inspection_document_columns:
            connection.execute(text("ALTER TABLE inspection_documents ADD COLUMN generation_dates JSON DEFAULT '[]' NOT NULL"))
        if "is_retry" not in inspection_document_columns:
            connection.execute(text("ALTER TABLE inspection_documents ADD COLUMN is_retry BOOLEAN DEFAULT FALSE NOT NULL"))
        if "source_id" not in inspection_document_columns:
            connection.execute(text("ALTER TABLE inspection_documents ADD COLUMN source_id INTEGER REFERENCES bottle_sources(id)"))
            connection.execute(text("CREATE INDEX ix_inspection_documents_source_id ON inspection_documents (source_id)"))
        connection.execute(text("""
            UPDATE inspection_documents
            SET source_id = (
                SELECT MIN(b.source_id)
                FROM inspection_document_lines line JOIN bottles b ON b.id = line.bottle_id
                WHERE line.document_id = inspection_documents.id
            )
            WHERE source_id IS NULL AND is_archived = FALSE AND is_retry = FALSE
              AND EXISTS (SELECT 1 FROM inspection_document_lines line WHERE line.document_id = inspection_documents.id AND line.bottle_id IS NOT NULL)
              AND 1 = (
                  SELECT COUNT(DISTINCT b.source_id)
                  FROM inspection_document_lines line JOIN bottles b ON b.id = line.bottle_id
                  WHERE line.document_id = inspection_documents.id
              )
        """))
        inspection_line_additions = {
            "spec_id": "INTEGER REFERENCES bottle_specs(id)",
            "source_line_id": "INTEGER REFERENCES inspection_document_lines(id)",
            "device_category": "VARCHAR(80) DEFAULT '焊接气瓶' NOT NULL",
            "next_inspection_date": "DATE",
            "inspector_name": "VARCHAR(80)",
            "inspection_time": "DATE",
        }
        for name, definition in inspection_line_additions.items():
            if name not in inspection_line_columns:
                connection.execute(text(f"ALTER TABLE inspection_document_lines ADD COLUMN {name} {definition}"))
        connection.execute(text("""
            UPDATE inspection_document_lines
            SET spec_id = (SELECT spec_id FROM bottles WHERE bottles.id = inspection_document_lines.bottle_id)
            WHERE spec_id IS NULL AND bottle_id IS NOT NULL
        """))
        for name in ("good_quantity", "good_adjustment_quantity", "bad_quantity", "bad_adjustment_quantity", "temporary_quantity", "scrap_quantity"):
            if name not in bottle_outbound_line_columns:
                connection.execute(text(f"ALTER TABLE bottle_outbound_lines ADD COLUMN {name} INTEGER DEFAULT 0 NOT NULL"))
        connection.execute(text("""
            UPDATE bottle_outbound_lines
            SET good_quantity = quantity
            WHERE good_quantity = 0 AND bad_quantity = 0 AND temporary_quantity = 0 AND scrap_quantity = 0
        """))
        if engine.dialect.name == "postgresql":
            connection.execute(text("ALTER TABLE inspection_document_lines ALTER COLUMN bottle_id DROP NOT NULL"))
            connection.execute(text("ALTER TABLE unverified_bottles ALTER COLUMN bottle_id DROP NOT NULL"))
            connection.execute(text("ALTER TABLE bottle_manufacturers ALTER COLUMN code_prefix TYPE VARCHAR(200)"))
            connection.execute(text("ALTER TABLE bottles ALTER COLUMN manufacture_date DROP NOT NULL"))
            connection.execute(text("ALTER TABLE bottles ALTER COLUMN inbound_id DROP NOT NULL"))
            connection.execute(text("""
                INSERT INTO bottle_inbound_lines (inbound_id, spec_id, pending_quantity, temporary_quantity, scrap_quantity)
                SELECT bi.id, chosen.id, bi.pending_quantity, bi.temporary_quantity, bi.scrap_quantity
                FROM bottle_inbounds bi
                CROSS JOIN LATERAL (
                    SELECT id FROM bottle_specs
                    ORDER BY is_default DESC, sort_order, id LIMIT 1
                ) chosen
                WHERE NOT EXISTS (SELECT 1 FROM bottle_inbound_lines line WHERE line.inbound_id = bi.id)
            """))
            connection.execute(text("UPDATE bottles SET coding_date = coded_at::date WHERE coding_date IS NULL"))
            connection.execute(text("""
                WITH numbered AS (
                    SELECT id, ROW_NUMBER() OVER (PARTITION BY coding_date ORDER BY coded_at, id) AS seq
                    FROM bottles WHERE coding_sequence IS NULL
                )
                UPDATE bottles SET coding_sequence = numbered.seq
                FROM numbered WHERE bottles.id = numbered.id
            """))
            decimal_columns = {
                "materials": ["conversion_ratio", "price", "stock", "safety_threshold"],
                "material_document_lines": ["quantity", "unit_price", "amount"],
                "material_movements": ["quantity_change", "balance_after"],
                "bottle_specs": ["inspection_price", "volume", "wall_thickness"],
                "bottles": ["inspection_price"],
            }
            for table_name, column_names in decimal_columns.items():
                for column_name in column_names:
                    connection.execute(text(
                        f"ALTER TABLE {table_name} ALTER COLUMN {column_name} "
                        f"TYPE NUMERIC(18, 2) USING ROUND({column_name}::numeric, 2)"
                    ))
    if engine.dialect.name == "sqlite":
        allow_archived_inspection_lines_sqlite()
    with SessionLocal() as db:
        migrate_page_permissions(db)
        # Preserve existing inspection sequences on startup. Generation, synchronization
        # and splitting explicitly resequence their own documents and rejection records.
        db.commit()
        preset_admins = [
            (settings.initial_admin_username, settings.initial_admin_password, "超级管理员"),
            (settings.second_admin_username, settings.second_admin_password, "备用超级管理员"),
        ]
        created = False
        for username, password, name in preset_admins:
            if not db.scalar(select(User).where(User.username == username)):
                db.add(User(
                    username=username,
                    name=name,
                    role_name="超级管理员",
                    password_hash=hash_password(password),
                    is_superadmin=True,
                    is_active=True,
                    must_change_password=True,
                    permissions=[],
                ))
                created = True
        if created:
            db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(material_daily_router)
app.include_router(menu_settings_router)
app.include_router(bottle_receipt_router)
