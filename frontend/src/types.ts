export interface User {
  id: number
  username: string
  name: string
  role_name: string
  phone?: string
  remark?: string
  is_active: boolean
  is_superadmin: boolean
  must_change_password: boolean
  permissions: string[]
  created_at: string
}

export interface Material {
  id: number
  name: string
  material_type: 'MATERIAL' | 'SCRAP'
  specification: string
  material_unit: string
  conversion_enabled: boolean
  stock_unit: string
  conversion_ratio: string | number
  price: string | number
  stock: string | number
  converted_stock?: string | number | null
  warning_enabled: boolean
  safety_threshold?: string | number
  warning_status: 'DISABLED' | 'NORMAL' | 'LOW'
  is_active: boolean
  remark?: string
  supplier_prices: Array<{ id: number; supplier_id: number; supplier_name: string; purchase_price: string | number }>
}

export interface Supplier {
  id: number
  name: string
  contact?: string
  phone?: string
  address?: string
  remark?: string
  is_active: boolean
  material_prices: Array<{ id: number; material_id: number; material_name: string; material_type: 'MATERIAL' | 'SCRAP'; specification: string; unit: string; purchase_price: string | number }>
}

export interface PurchaseOrderLine {
  id: number
  material_id: number
  material_name: string
  specification: string
  unit: string
  quantity: string | number
  unit_price: string | number
  amount: string | number
}

export interface PurchaseOrder {
  id: number
  order_no: string
  order_date: string
  supplier_id: number
  supplier_name: string
  handler: string
  note?: string
  status: 'DRAFT' | 'CONFIRMED' | 'VOID'
  is_paid: boolean
  total_amount: string | number
  inbound_document_id?: number
  lines: PurchaseOrderLine[]
  created_by_name: string
  created_at: string
  updated_by_name?: string
  updated_at: string
  confirmed_by_name?: string
  confirmed_at?: string
  voided_by_name?: string
  voided_at?: string
}

export interface BottleSource extends Supplier {
  is_default: boolean
  sort_order: number
}

export interface BottleSpec {
  id: number
  name: string
  inspection_price?: string | number
  volume?: string | number
  wall_thickness?: string | number
  is_default: boolean
  sort_order: number
  is_active: boolean
  remark?: string
}

export interface BottleManufacturer {
  id: number
  name: string
  code_prefix: string
  sort_order: number
  is_active: boolean
  remark?: string
}

export interface MaterialDocumentLine {
  id: number
  material_id: number
  material_name: string
  specification: string
  unit: string
  quantity: string | number
  unit_price: string | number
  amount: string | number
}

export interface MaterialDocument {
  id: number
  document_no: string
  document_type: 'NORMAL_IN' | 'OUTBOUND' | 'RETURN_IN'
  business_date: string
  supplier_id?: number
  purchase_order_id?: number
  related_outbound_id?: number
  inbound_mode: 'DIRECT' | 'PURCHASE_ORDER'
  inbound_category: 'MATERIAL' | 'SCRAP' | 'PURCHASE'
  outbound_category: 'MATERIAL' | 'SCRAP'
  is_paid: boolean
  handler: string
  note?: string
  status: 'DRAFT' | 'POSTED' | 'VOID'
  lines: MaterialDocumentLine[]
  created_by: number
  created_by_name: string
  created_at: string
  updated_by?: number
  updated_by_name?: string
  updated_at: string
  posted_by?: number
  posted_by_name?: string
  posted_at?: string
  voided_by?: number
  voided_by_name?: string
  voided_at?: string
}

export interface BottleInbound {
  id: number
  document_no: string
  business_date: string
  source_id: number
  pending_quantity: number
  temporary_quantity: number
  scrap_quantity: number
  total_quantity: number
  lines: BottleInboundLine[]
  handler: string
  note?: string
  status: 'DRAFT' | 'POSTED' | 'VOID'
  created_at: string
}

export interface BottleInboundLine {
  id: number
  spec_id: number
  spec_name: string
  pending_quantity: number
  temporary_quantity: number
  scrap_quantity: number
  total_quantity: number
}

export interface QuickConfig {
  id: number
  category: 'CODE_PREFIX' | 'INSPECTION_NOTE' | 'MANUFACTURE_DATE'
  name: string
  value: string
  sort_order: number
  is_active: boolean
}

export interface Bottle {
  coding_customer_id?: number | null
  effective_coding_customer_id?: number
  coding_customer_name?: string
  id: number
  inbound_id: number | null
  body_code: string
  manufacture_date?: string
  source_id: number
  spec_id: number
  inspection_price?: string | number
  zone: 'PENDING' | 'GOOD' | 'BAD' | 'SCRAP' | 'OUTBOUND'
  process_status: 'CODED' | 'INSPECTED'
  coding_date?: string
  coding_sequence?: number
  coding_note?: string
  coded_by_name?: string
  manufacturer?: string
  inspection_result?: 'GOOD' | 'BAD'
  coded_at: string
  inspected_at?: string
  returned_to_customer?: boolean | null
  inspection_note?: string
  inspection_document_status?: 'INSPECTED' | 'UNINSPECTED'
  inspection_document_no?: string
}

export interface BottleOutboundLine {
  id: number
  spec_id: number
  spec_name: string
  quantity: number
  good_quantity: number
  bad_quantity: number
  temporary_quantity: number
  scrap_quantity: number
  bad_bottle_ids?: number[]
  scrap_bottle_ids?: number[]
  selected_bottles?: Array<{ id: number; bottle_id?: number; body_code: string; origin_zone: 'BAD' | 'SCRAP'; is_active: boolean; inspection_note?: string }>
}

export interface BottleOutbound {
  id: number
  document_no: string
  business_date: string
  source_id?: number
  customer: string
  handler: string
  note?: string
  status: 'DRAFT' | 'POSTED' | 'VOID'
  total_quantity: number
  lines: BottleOutboundLine[]
  created_by_name: string
  updated_by_name?: string
  posted_by_name?: string
  voided_by_name?: string
  created_at: string
  updated_at: string
  posted_at?: string
  voided_at?: string
}
