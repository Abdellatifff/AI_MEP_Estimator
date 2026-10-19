# -*- coding: utf-8 -*-
"""ينشئ ملف prices.xlsx جاهز للرفع"""
from pathlib import Path

try:
    import openpyxl
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "openpyxl"])
    import openpyxl

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Prices"

# Header
ws.append(['system', 'size', 'supply_price', 'install_price', 'test_price'])

# Data
data = [
    # Fire
    ['fire', '3', 45.50, 25.00, 8.00],
    ['fire', '4', 62.00, 32.00, 10.50],
    ['fire', '6', 98.75, 48.50, 15.00],
    ['fire', '8', 145.00, 72.00, 20.00],
    # Sewage
    ['sewage', '3', 22.00, 12.00, 4.00],
    ['sewage', '4', 32.00, 16.00, 5.50],
    ['sewage', '6', 55.00, 28.00, 8.00],
    ['sewage', '8', 88.00, 42.00, 12.00],
    # General
    ['general', '3', 40.00, 20.00, 6.00],
    ['general', '4', 55.00, 28.00, 8.00],
    ['general', '6', 85.00, 40.00, 12.00],
    ['general', '8', 125.00, 60.00, 18.00],
]

for row in data:
    ws.append(row)

# Adjust column widths
for col in 'ABCDE':
    ws.column_dimensions[col].width = 15

out = Path(r"D:\AI_MEP_Estimator\prices.xlsx")
wb.save(str(out))
print("[+] Created: " + str(out))
print("[+] Size: " + str(out.stat().st_size) + " bytes")
print("[+] Rows: " + str(len(data)) + " + header")