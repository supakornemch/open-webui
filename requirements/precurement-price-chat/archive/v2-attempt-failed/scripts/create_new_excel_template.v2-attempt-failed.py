#!/usr/bin/env python3
"""
Create new Excel template for Procurement Price Chatbot
with sample data from existing Excel (20 items)
"""

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
import json

# Source file
SOURCE_FILE = "Trade Marketing Materials price for Y2026.final.xlsx"
OUTPUT_FILE = "Procurement_Price_Template_v2.xlsx"

def create_products_sheet(wb):
    """Sheet 1: Products (Master list)"""
    ws = wb.create_sheet("Products", 0)
    
    # Headers
    headers = [
        "Product Code",
        "Category", 
        "Product Name",
        "Description",
        "Pricing Model",
        "Unit",
        "Formula",
        "Has Variants",
        "Related Products",
        "Notes"
    ]
    
    # Header style
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(1, col_idx, header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    # Sample data from product-variants-table.md
    products = [
        # POSM (flat pricing with variants)
        ["POSM-001", "POSM", "ร่มโค้ก", "ร่มสำหรับร้านค้า มีขนาด 36/40 นิ้ว × โครงเหล็ก/ไฟเบอร์ × สีตาย/ไล่ระดับสี", "flat", "piece", "", "TRUE", "", ""],
        ["POSM-002", "POSM", "กล่องทิชชู-โค้ก", "กล่องทิชชูพร้อมโลโก้โค้ก", "flat", "piece", "", "FALSE", "", ""],
        ["POSM-003", "POSM", "ผ้ากันเปื้อนโคคา-โคล่า", "เอี้ยม (เต็มตัว) ไขว้หลัง หรือ ครึ่งตัว", "flat", "piece", "", "TRUE", "", ""],
        ["POSM-004", "POSM", "ถังใส่น้ำแข็ง-โค้ก", "ทรงสี่เหลี่ยม", "flat", "piece", "", "FALSE", "", ""],
        ["POSM-005", "POSM", "กล่องใส่ช้อน/ตะเกียบ", "แบบแนวตั้ง", "flat", "piece", "", "FALSE", "", ""],
        ["POSM-006", "POSM", "Mega Rack", "แร็คสำหรับ TT-DSD และ WS มีขนาด 120x40x150 cm และ 150x60x150 cm", "flat", "piece", "", "TRUE", "", ""],
        
        # Printing (unit-based & flat)
        ["PRINT-001", "Printing", "PP Board", "ป้ายหน้าเคาน์เตอร์ มีขนาด 120x120, 85x190, 70x150 cm", "flat", "piece", "", "TRUE", "", ""],
        ["PRINT-002", "Printing", "ป้ายรายการอาหารโค้ก", "60x120 cm", "flat", "piece", "", "FALSE", "", ""],
        ["PRINT-003", "Printing", "แบนเนอร์โค้ก", "80x300 cm", "flat", "piece", "", "FALSE", "", ""],
        ["PRINT-004", "Printing", "ผ้าใบกันสาด-โค้ก", "1.8x3.5 m", "flat", "piece", "", "FALSE", "", ""],
        ["PRINT-005", "Printing", "แผ่นริจิ-โค้ก", "มีขนาด 16x24 นิ้ว และ 24x32 นิ้ว", "flat", "piece", "", "TRUE", "", ""],
        
        # Garment (flat with color modifiers)
        ["GARMT-001", "Garment", "เสื้อยืด", "Cotton สีขาว หรือ สีอื่นๆ (สีอ่อน +5฿ / สีกลาง +10฿ / สีเข้ม +20฿)", "flat", "piece", "", "TRUE", "", ""],
        ["GARMT-002", "Garment", "เสื้อโปโล TC", "ผ้า TC สีขาว หรือ สีอื่นๆ", "flat", "piece", "", "TRUE", "", ""],
        ["GARMT-003", "Garment", "เสื้อโปโล ผ้าไมโคร", "ซับลิเมชั่น", "flat", "piece", "", "FALSE", "", ""],
        ["GARMT-004", "Garment", "สกรีน", "1-4 สี", "flat", "piece", "", "TRUE", "", ""],
        
        # Premium (flat)
        ["PREM-001", "Premium", "แก้วกระดาษ", "แก้วกระดาษพิมพ์โลโก้ มีขนาด 6.5 ออนซ์ และ 22 ออนซ์", "flat", "piece", "", "TRUE", "", ""],
        ["PREM-003", "Premium", "ร่มเสาข้าง", "ร่มขนาดใหญ่สำหรับร้านค้า", "flat", "piece", "", "FALSE", "", ""],
        ["PREM-004", "Premium", "Bean Bag", "หนังชามัวร์ หรือ วัสดุผ้า", "flat", "piece", "", "TRUE", "", ""],
    ]
    
    for row_idx, product in enumerate(products, 2):
        for col_idx, value in enumerate(product, 1):
            ws.cell(row_idx, col_idx, value)
    
    # Auto-size columns
    for col_idx in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 18
    
    ws.column_dimensions['C'].width = 35  # product_name
    ws.column_dimensions['D'].width = 30  # description
    ws.column_dimensions['I'].width = 30  # related_products
    ws.column_dimensions['J'].width = 40  # notes

def create_variants_sheet(wb):
    """Sheet 2: Variants (includes Pricing Rules)"""
    ws = wb.create_sheet("Variants")
    
    headers = [        "Variant Code",        "Product Code",
        "Description",
        "Attribute",
        "Condition",
        "Base Price Modifier",
        "Modifier Type",
        "Priority",
        "Notes"
    ]
    
    header_fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(1, col_idx, header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    # Sample variants from product-variants-table.md
    variants = [
        # ร่มโค้ก - 8 variants (ขนาด × โครง × สี)
        ["POSM-001-V1", "POSM-001", "36 นิ้ว โครงเหล็ก สีตาย (ไม่เกิน 4 สี)", "ขนาด+โครง+สี", "36นิ้ว,เหล็ก,สีตาย", "0", "+", "1", ""],
        ["POSM-001-V2", "POSM-001", "36 นิ้ว โครงเหล็ก ไล่ระดับสี (ไม่เกิน 8 เฉด)", "ขนาด+โครง+สี", "36นิ้ว,เหล็ก,ไล่ระดับสี", "5", "+", "2", "+5 บาทจากสีตาย"],
        ["POSM-001-V3", "POSM-001", "36 นิ้ว โครงไฟเบอร์ สีตาย (ไม่เกิน 4 สี)", "ขนาด+โครง+สี", "36นิ้ว,ไฟเบอร์,สีตาย", "0", "+", "1", ""],
        ["POSM-001-V4", "POSM-001", "36 นิ้ว โครงไฟเบอร์ ไล่ระดับสี (ไม่เกิน 8 เฉด)", "ขนาด+โครง+สี", "36นิ้ว,ไฟเบอร์,ไล่ระดับสี", "5", "+", "2", "+5 บาทจากสีตาย"],
        ["POSM-001-V5", "POSM-001", "40 นิ้ว โครงเหล็ก สีตาย (ไม่เกิน 4 สี)", "ขนาด+โครง+สี", "40นิ้ว,เหล็ก,สีตาย", "20", "+", "1", "+20 บาทจาก 36 นิ้ว"],
        ["POSM-001-V6", "POSM-001", "40 นิ้ว โครงเหล็ก ไล่ระดับสี (ไม่เกิน 8 เฉด)", "ขนาด+โครง+สี", "40นิ้ว,เหล็ก,ไล่ระดับสี", "25", "+", "2", "+25 บาทจาก 36 นิ้ว"],
        ["POSM-001-V7", "POSM-001", "40 นิ้ว โครงไฟเบอร์ สีตาย (ไม่เกิน 4 สี)", "ขนาด+โครง+สี", "40นิ้ว,ไฟเบอร์,สีตาย", "20", "+", "1", "+20 บาทจาก 36 นิ้ว"],
        ["POSM-001-V8", "POSM-001", "40 นิ้ว โครงไฟเบอร์ ไล่ระดับสี (ไม่เกิน 8 เฉด)", "ขนาด+โครง+สี", "40นิ้ว,ไฟเบอร์,ไล่ระดับสี", "25", "+", "2", "+25 บาทจาก 36 นิ้ว"],
        
        # ผ้ากันเปื้อน - 2 variants
        ["POSM-003-V1", "POSM-003", "เอี้ยม (เต็มตัว) ไขว้หลัง", "แบบ", "เต็มตัว", "0", "+", "1", ""],
        ["POSM-003-V2", "POSM-003", "ครึ่งตัว", "แบบ", "ครึ่งตัว", "-10", "+", "1", "ถูกกว่าแบบเต็มตัว"],
        
        # Mega Rack - 2 variants
        ["POSM-006-V1", "POSM-006", "120x40x150 cm (TT-DSD)", "ขนาด+ประเภท", "120x40x150,TT-DSD", "0", "+", "1", ""],
        ["POSM-006-V2", "POSM-006", "150x60x150 cm (WS)", "ขนาด+ประเภท", "150x60x150,WS", "200", "+", "1", "ขนาดใหญ่กว่า +200 บาท"],
        
        # PP Board - 3 variants
        ["PRINT-001-V1", "PRINT-001", "120x120 cm (โค้กเขียนชื่อร้านค้า)", "ขนาด", "120x120", "0", "+", "1", "ขนาดใหญ่สุด"],
        ["PRINT-001-V2", "PRINT-001", "85x190 cm (ป้ายหน้าเคาน์เตอร์)", "ขนาด", "85x190", "-130", "+", "2", "ถูกกว่า 120x120"],
        ["PRINT-001-V3", "PRINT-001", "70x150 cm (ป้ายหน้าเคาน์เตอร์)", "ขนาด", "70x150", "-230", "+", "3", "ขนาดเล็กสุด"],
        
        # แผ่นริจิ-โค้ก - 2 variants (ขนาด)
        ["PRINT-005-V1", "PRINT-005", "16x24 นิ้ว", "ขนาด", "16x24", "0", "+", "1", "ขนาดเล็ก"],
        ["PRINT-005-V2", "PRINT-005", "24x32 นิ้ว", "ขนาด", "24x32", "15", "+", "1", "ขนาดใหญ่ +15 บาท"],
        
        # เสื้อยืด - 4 variants (สี)
        ["GARMT-001-V1", "GARMT-001", "สีขาว", "สี", "ขาว", "0", "+", "1", "ราคาฐาน"],
        ["GARMT-001-V2", "GARMT-001", "สีอ่อน", "สี", "อ่อน", "5", "+", "2", "+5 บาท"],
        ["GARMT-001-V3", "GARMT-001", "สีกลาง", "สี", "กลาง", "10", "+", "3", "+10 บาท"],
        ["GARMT-001-V4", "GARMT-001", "สีเข้ม", "สี", "เข้ม", "20", "+", "4", "+20 บาท"],
        
        # เสื้อโปโล TC - 4 variants (สี)
        ["GARMT-002-V1", "GARMT-002", "ผ้า TC สีขาว", "สี", "ขาว", "0", "+", "1", "ราคาฐาน"],
        ["GARMT-002-V2", "GARMT-002", "ผ้า TC สีอ่อน", "สี", "อ่อน", "5", "+", "2", "+5 บาท"],
        ["GARMT-002-V3", "GARMT-002", "ผ้า TC สีกลาง", "สี", "กลาง", "10", "+", "3", "+10 บาท"],
        ["GARMT-002-V4", "GARMT-002", "ผ้า TC สีเข้ม", "สี", "เข้ม", "20", "+", "4", "+20 บาท"],
        
        # สกรีน - 4 variants (จำนวนสี)
        ["GARMT-004-V1", "GARMT-004", "1 สี", "จำนวนสี", "1", "0", "+", "1", ""],
        ["GARMT-004-V2", "GARMT-004", "2 สี", "จำนวนสี", "2", "5", "+", "2", "+5 บาทต่อสีเพิ่ม"],
        ["GARMT-004-V3", "GARMT-004", "3 สี", "จำนวนสี", "3", "10", "+", "3", "+10 บาทจากราคาฐาน"],
        ["GARMT-004-V4", "GARMT-004", "4 สี", "จำนวนสี", "4", "15", "+", "4", "+15 บาทจากราคาฐาน"],
        
        # Bean Bag - 2 variants (วัสดุ)
        ["PREM-004-V1", "PREM-004", "หนังชามัวร์", "วัสดุ", "หนังชามัวร์", "0", "+", "1", "ราคาฐาน"],
        ["PREM-004-V2", "PREM-004", "วัสดุผ้า", "วัสดุ", "ผ้า", "-50", "+", "2", "ถูกกว่าหนัง 50 บาท"],
        
        # แก้วกระดาษ - 2 variants
        ["PREM-001-V1", "PREM-001", "6.5 ออนซ์", "ขนาด", "6.5oz", "0", "+", "1", "ขนาดเล็ก"],
        ["PREM-001-V2", "PREM-001", "22 ออนซ์", "ขนาด", "22oz", "2.41", "+", "2", "ขนาดใหญ่ +2.41 บาท"],
    ]
    
    for row_idx, variant in enumerate(variants, 2):
        for col_idx, value in enumerate(variant, 1):
            ws.cell(row_idx, col_idx, value)
    
    for col_idx in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 18
    ws.column_dimensions['B'].width = 45  # description
    ws.column_dimensions['H'].width = 30  # notes

def create_vendors_sheet(wb):
    """Sheet 3: Vendors Master Data"""
    ws = wb.create_sheet("Vendors")
    
    headers = [
        "Vendor Code",
        "Vendor Name",
        "Contact Person",
        "Phone",
        "Email",
        "Address",
        "Notes"
    ]
    
    header_fill = PatternFill(start_color="9B59B6", end_color="9B59B6", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(1, col_idx, header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    # Sample vendors
    vendors = [
        ["VEN-A", "Vendor A", "นายเอ", "02-111-1111", "vendora@example.com", "กรุงเทพฯ", "Vendor หลัก POSM"],
        ["VEN-B", "Vendor B", "นางสาวบี", "02-222-2222", "vendorb@example.com", "กรุงเทพฯ", ""],
        ["VEN-C", "Vendor C", "นายซี", "02-333-3333", "vendorc@example.com", "สมุทรปราการ", "Vendor หลัก Printing"],
        ["VEN-D", "Vendor D", "นางสาวดี", "02-444-4444", "vendord@example.com", "นนทบุรี", ""],
        ["VEN-E", "Vendor E", "นายอี", "02-555-5555", "vendore@example.com", "กรุงเทพฯ", ""],
        ["VEN-F", "Vendor F", "นางเอฟ", "02-666-6666", "vendorf@example.com", "ปทุมธานี", "Vendor หลัก PP Board"],
        ["VEN-G", "Vendor G", "นายจี", "02-777-7777", "vendorg@example.com", "กรุงเทพฯ", ""],
        ["VEN-H", "Vendor H", "นางสาวเอช", "02-888-8888", "vendorh@example.com", "สมุทรปราการ", ""],
        ["VEN-I", "Vendor I", "นายไอ", "02-999-9999", "vendori@example.com", "กรุงเทพฯ", "Vendor หลัก Garment"],
        ["VEN-J", "Vendor J", "นางเจ", "02-101-0101", "vendorj@example.com", "กรุงเทพฯ", ""],
        ["VEN-K", "Vendor K", "นายเค", "02-102-0202", "vendork@example.com", "นนทบุรี", "สกรีน"],
        ["VEN-L", "Vendor L", "นางสาวแอล", "02-103-0303", "vendorl@example.com", "กรุงเทพฯ", ""],
        ["VEN-M", "Vendor M", "นายเอ็ม", "02-104-0404", "vendorm@example.com", "สมุทรปราการ", "Premium Items"],
        ["VEN-N", "Vendor N", "นางเอ็น", "02-105-0505", "vendorn@example.com", "กรุงเทพฯ", "Mega Rack"],
        ["VEN-O", "Vendor O", "นายโอ", "02-106-0606", "vendoro@example.com", "กรุงเทพฯ", "ราคาถูก แต่คุณภาพต่ำ"],
    ]
    
    for row_idx, vendor in enumerate(vendors, 2):
        for col_idx, value in enumerate(vendor, 1):
            ws.cell(row_idx, col_idx, value)
    
    # Column widths
    ws.column_dimensions['A'].width = 14  # Vendor Code
    ws.column_dimensions['B'].width = 25  # Vendor Name
    ws.column_dimensions['C'].width = 20  # Contact Person
    ws.column_dimensions['D'].width = 15  # Phone
    ws.column_dimensions['E'].width = 25  # Email
    ws.column_dimensions['F'].width = 25  # Address
    ws.column_dimensions['G'].width = 30  # Notes

def create_vendor_prices_sheet(wb):
    """Sheet 4: Vendor Prices - with VLOOKUP for Product Name/Description/Vendor Name"""
    ws = wb.create_sheet("Vendor_Prices")
    
    # Reorder columns: Product Code, Variant Code, Vendor Code, Price info, then VLOOKUP columns
    headers = [
        "Product Code",
        "Variant Code",
        "Vendor Code",
        "Price",
        "Unit",
        "Qty",
        "Qty Range",
        "Year",
        "Is Winner",
        "Meets Spec",
        "Product Name",
        "Product Description",
        "Vendor Name",
        "Notes"
    ]
    
    header_fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
    header_font = Font(bold=True, color="000000")
    
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(1, col_idx, header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    # Sample prices - only core data, VLOOKUP will fill Product Name/Description/Vendor Name
    prices = [
        # ร่มโค้ก variants
        ["POSM-001", "POSM-001-V1", "VEN-A", 523, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["POSM-001", "POSM-001-V1", "VEN-B", 565, "piece", 1, "", 2026, "FALSE", "TRUE"],
        ["POSM-001", "POSM-001-V1", "VEN-C", 480, "piece", 1, "", 2026, "FALSE", "FALSE"],
        ["POSM-001", "POSM-001-V2", "VEN-A", 528, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["POSM-001", "POSM-001-V3", "VEN-A", 523, "piece", 1, "", 2026, "TRUE", "TRUE"],
        
        # กล่องทิชชู (no variant)
        ["POSM-002", "", "VEN-C", 28.5, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["POSM-002", "", "VEN-D", 30, "piece", 1, "", 2026, "FALSE", "TRUE"],
        ["POSM-002", "", "VEN-E", 25, "piece", 1, "", 2026, "FALSE", "FALSE"],
        
        # ผ้ากันเปื้อน variants
        ["POSM-003", "POSM-003-V1", "VEN-E", 65, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["POSM-003", "POSM-003-V2", "VEN-E", 55, "piece", 1, "", 2026, "TRUE", "TRUE"],
        
        # Mega Rack variants
        ["POSM-006", "POSM-006-V1", "VEN-N", 3500, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["POSM-006", "POSM-006-V2", "VEN-N", 3700, "piece", 1, "", 2026, "TRUE", "TRUE"],
        
        # PP Board variants
        ["PRINT-001", "PRINT-001-V1", "VEN-F", 580, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["PRINT-001", "PRINT-001-V2", "VEN-F", 450, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["PRINT-001", "PRINT-001-V3", "VEN-F", 350, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["PRINT-002", "", "VEN-G", 350, "piece", 1, "", 2026, "TRUE", "TRUE"],
        
        # แผ่นริจิ variants
        ["PRINT-005", "PRINT-005-V1", "VEN-H", 45, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["PRINT-005", "PRINT-005-V2", "VEN-H", 60, "piece", 1, "", 2026, "TRUE", "TRUE"],
        
        # เสื้อยืด variants
        ["GARMT-001", "GARMT-001-V1", "VEN-I", 90, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["GARMT-001", "GARMT-001-V2", "VEN-I", 95, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["GARMT-001", "GARMT-001-V3", "VEN-I", 100, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["GARMT-001", "GARMT-001-V4", "VEN-I", 110, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["GARMT-001", "GARMT-001-V1", "VEN-O", 75, "piece", 1, "", 2026, "FALSE", "FALSE"],
        
        # เสื้อโปโล TC variants
        ["GARMT-002", "GARMT-002-V1", "VEN-J", 120, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["GARMT-002", "GARMT-002-V3", "VEN-J", 130, "piece", 1, "", 2026, "TRUE", "TRUE"],
        
        # สกรีน variants
        ["GARMT-004", "GARMT-004-V1", "VEN-K", 25, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["GARMT-004", "GARMT-004-V2", "VEN-K", 30, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["GARMT-004", "GARMT-004-V4", "VEN-K", 40, "piece", 1, "", 2026, "TRUE", "TRUE"],
        
        # แก้วกระดาษ variants
        ["PREM-001", "PREM-001-V1", "VEN-L", 1.53, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["PREM-001", "PREM-001-V2", "VEN-L", 3.94, "piece", 1, "", 2026, "TRUE", "TRUE"],
        
        # Bean Bag variants
        ["PREM-004", "PREM-004-V1", "VEN-M", 850, "piece", 1, "", 2026, "TRUE", "TRUE"],
        ["PREM-004", "PREM-004-V2", "VEN-M", 800, "piece", 1, "", 2026, "TRUE", "TRUE"],
    ]
    
    # Write data rows
    for row_idx, price in enumerate(prices, 2):
        for col_idx, value in enumerate(price, 1):
            ws.cell(row_idx, col_idx, value)
    
    # Add VLOOKUP formulas for Product Name (column K), Product Description (column L), and Vendor Name (column M)
    products_sheet_name = "Products"
    vendors_sheet_name = "Vendors"
    for row_idx in range(2, len(prices) + 2):
        # Column K: Product Name = VLOOKUP(A2, Products!A:C, 3, FALSE)
        ws.cell(row_idx, 11).value = f'=VLOOKUP(A{row_idx}, {products_sheet_name}!$A:$C, 3, FALSE)'
        # Column L: Product Description = VLOOKUP(A2, Products!A:D, 4, FALSE)
        ws.cell(row_idx, 12).value = f'=VLOOKUP(A{row_idx}, {products_sheet_name}!$A:$D, 4, FALSE)'
        # Column M: Vendor Name = VLOOKUP(C2, Vendors!A:B, 2, FALSE)
        ws.cell(row_idx, 13).value = f'=VLOOKUP(C{row_idx}, {vendors_sheet_name}!$A:$B, 2, FALSE)'
    
    # Column widths - adjusted for new order with Vendor Code
    ws.column_dimensions['A'].width = 14  # Product Code
    ws.column_dimensions['B'].width = 18  # Variant Code
    ws.column_dimensions['C'].width = 14  # Vendor Code
    ws.column_dimensions['D'].width = 12  # Price
    ws.column_dimensions['E'].width = 10  # Unit
    ws.column_dimensions['F'].width = 10  # Qty
    ws.column_dimensions['G'].width = 12  # Qty Range
    ws.column_dimensions['H'].width = 10  # Year
    ws.column_dimensions['I'].width = 12  # Is Winner
    ws.column_dimensions['J'].width = 12  # Meets Spec
    ws.column_dimensions['K'].width = 25  # Product Name (VLOOKUP)
    ws.column_dimensions['L'].width = 40  # Product Description (VLOOKUP)
    ws.column_dimensions['M'].width = 25  # Vendor Name (VLOOKUP)
    ws.column_dimensions['N'].width = 30  # Notes

def create_related_products_sheet(wb):
    """Sheet 4: Related Products (Accessories)"""
    ws = wb.create_sheet("Related_Products")
    
    headers = [
        "Product Code",
        "Related Product Code",
        "Related Product Name",
        "Relation Type",
        "Notes"
    ]
    
    header_fill = PatternFill(start_color="9966FF", end_color="9966FF", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(1, col_idx, header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    # Sample related products
    relations = [
        ["POSM-001", "PREM-BASE-001", "ฐานร่ม น้ำหนัก 15 kg", "accessory", "แนะนำใช้คู่กับร่ม"],
        ["PREM-003", "PREM-BASE-002", "ฐานร่มเสาข้าง คอนกรีต", "accessory", "จำเป็นต้องมีฐาน"],
    ]
    
    for row_idx, relation in enumerate(relations, 2):
        for col_idx, value in enumerate(relation, 1):
            ws.cell(row_idx, col_idx, value)
    
    for col_idx in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 18
    ws.column_dimensions['C'].width = 30  # Related Product Name
    ws.column_dimensions['E'].width = 30  # Notes

def create_pricing_rules_sheet(wb):
    """Sheet 5: Pricing Rules (Optional - for complex modifiers)"""
    ws = wb.create_sheet("Pricing_Rules")
    
    headers = [
        "Product Code",
        "Attribute",
        "Condition",
        "Modifier",
        "Modifier Type",
        "Priority",
        "Notes"
    ]
    
    header_fill = PatternFill(start_color="E74C3C", end_color="E74C3C", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(1, col_idx, header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    # Sample rules
    rules = [
        ["GARMT-001", "สี", "สีอ่อน", 5, "+", 1, "เพิ่ม 5 บาท"],
        ["GARMT-001", "สี", "สีกลาง", 10, "+", 2, "เพิ่ม 10 บาท"],
        ["GARMT-001", "สี", "สีเข้ม", 20, "+", 3, "เพิ่ม 20 บาท"],
        ["GARMT-001", "ไซด์", "2XL+", 1, "+", 4, "+1 บาทต่อไซด์พิเศษ"],
    ]
    
    for row_idx, rule in enumerate(rules, 2):
        for col_idx, value in enumerate(rule, 1):
            ws.cell(row_idx, col_idx, value)
    
    for col_idx in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 16
    ws.column_dimensions['G'].width = 30  # Notes

def create_readme_sheet(wb):
    """Sheet 6: README (Instructions)"""
    ws = wb.create_sheet("README", 0)  # First sheet
    
    ws['A1'] = "PROCUREMENT PRICE TEMPLATE v2.0"
    ws['A1'].font = Font(bold=True, size=16, color="1F4E78")
    
    instructions = [
        "",
        "📋 SHEET DESCRIPTIONS:",
        "",
        "1. Products - Master product list",
        "   • product_id: Unique ID (e.g., POSM-001, GARMT-001)",
        "   • pricing_model: flat / unit / tiered",
        "   • unit: piece / sqm / set / etc.",
        "   • formula: for unit-based (e.g., 'width * height')",
        "",
        "2. Variants - Product variations",
        "   • For products with multiple specs (color, size, material)",
        "   • base_price_modifier: additional cost (+5, +10, etc.)",
        "",
        "3. Vendor_Prices - Actual pricing from vendors",
        "   • qty_min/max: price brackets (for tiered pricing)",
        "   • is_winner: TRUE for lowest price in each bracket",
        "",
        "4. Related_Products - Accessories/add-ons",
        "   • relation_type: accessory / alternative / bundle",
        "   • required: TRUE if must-have (e.g., flag base)",
        "",
        "5. Pricing_Rules - Complex modifiers (optional)",
        "   • Use when modifiers are too complex for Variants sheet",
        "",
        "🎯 PRICING MODELS:",
        "",
        "• FLAT: fixed price per unit",
        "  Example: ร่มโค้ก = 523 บาท/อัน",
        "",
        "• UNIT: price per measurement unit (sqm, meter, etc.)",
        "  Example: ป้ายไวนิล = 150 บาท/ตร.ม.",
        "  → User: '2×3 เมตร' → 6 ตร.ม. × 150 = 900 บาท",
        "",
        "• TIERED: price varies by quantity bracket",
        "  Example: สติ๊กเกอร์ PVC",
        "  → 1-100 ชิ้น = 5 บาท/ชิ้น",
        "  → 101-500 ชิ้น = 4 บาท/ชิ้น",
        "  → 501+ ชิ้น = 3 บาท/ชิ้น",
        "",
        "⚠️ IMPORTANT NOTES:",
        "",
        "• All prices in THB",
        "• year = 2026 (update annually)",
        "• Flag unit-based products in 'notes' column",
        "• LLM will auto-convert units (cm→m, นิ้ว→cm)",
        "• Related products: will be suggested by LLM if missing dimensions",
        "",
        "📞 SUPPORT:",
        "IT Team - Supakorn E. (supakorn@haadthip.com)",
        "Procurement - Densri K. (densri@haadthip.com)",
        "",
        "Last updated: 2026-07-31",
    ]
    
    for idx, line in enumerate(instructions, 3):
        ws[f'A{idx}'] = line
    
    ws.column_dimensions['A'].width = 80

def main():
    print("Creating new Excel template...")
    
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default sheet
    
    print("  [1/4] README sheet...")
    create_readme_sheet(wb)
    
    print("  [2/5] Products sheet...")
    create_products_sheet(wb)
    
    print("  [3/5] Variants sheet...")
    create_variants_sheet(wb)
    
    print("  [4/5] Vendors sheet...")
    create_vendors_sheet(wb)
    
    print("  [5/5] Vendor_Prices sheet...")
    create_vendor_prices_sheet(wb)
    
    wb.save(OUTPUT_FILE)
    print(f"\n✅ Created: {OUTPUT_FILE}")
    print(f"   📊 5 sheets (README, Products, Variants, Vendors, Vendor_Prices)")
    print(f"   📝 20 products, 15 vendors, 32 price entries")
    print(f"   🔗 VLOOKUP formulas: Product Name/Description + Vendor Name")

if __name__ == "__main__":
    main()
