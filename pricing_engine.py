# -*- coding: utf-8 -*-
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RULES_DIR = BASE_DIR / "rules"
TABLES_FILE = RULES_DIR / "price_tables.json"

def description_to_action_code(description):
    d = (description or '').lower()
    code = ""
    if 'توريد' in d or 'supply' in d or 'provide' in d: code += 'S'
    if 'تركيب' in d or 'install' in d: code += 'I'
    if 'اختبار' in d or 'test' in d: code += 'T'
    return code if code else 'S'

class PricingEngine:
    def __init__(self):
        self.env = True # محاكاة وجود المحرك
        self.price_tables = {}
        self._load_tables()

    def _load_tables(self):
        if TABLES_FILE.exists():
            try:
                with open(TABLES_FILE, 'r', encoding='utf-8-sig') as f:
                    self.price_tables = json.load(f)
                print("[+] Loaded " + str(len(self.price_tables)) + " tables")
            except Exception as e:
                print("[!] load: " + str(e))
                self.price_tables = {}

    def reload(self):
        self._load_tables()
        return True

    def save_tables(self, tables):
        TABLES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TABLES_FILE, 'w', encoding='utf-8') as f:
            json.dump(tables, f, ensure_ascii=False, indent=2)
        self.price_tables = tables
        return self.reload()

    def price_item(self, item_description, size, connection='Grooved',
                   action_code=None, quantity=0, include_tax=False):
        
        if not self.price_tables:
            return {'success': False, 'error': 'prices empty'}

        if not action_code:
            action_code = description_to_action_code(item_description)

        system = 'general'
        if 'حريق' in item_description or 'fire' in item_description.lower(): system = 'fire'
        elif 'صرف' in item_description or 'sewage' in item_description.lower(): system = 'sewage'

        table_name = f"{system}_{action_code}"
        if table_name not in self.price_tables:
            table_name = f"{system}_S"

        table = self.price_tables.get(table_name, {})
        size_data = table.get(str(size), {})

        if not size_data:
            return {'success': False, 'error': f'لا توجد أسعار للقطر {size} في {table_name}'}

        unit_price = sum(size_data.values())
        subtotal = unit_price * float(quantity)
        
        tax = 0.0
        if include_tax:
            tax = subtotal * 0.14

        before_discount = subtotal + tax
        discount = 0.0
        if float(quantity) > 100:
            discount = before_discount * 0.05

        grand_total = before_discount - discount

        return {
            'success': True,
            'item': item_description,
            'size': size,
            'connection': connection,
            'action_code': action_code,
            'quantity': float(quantity),
            'price_table': table_name,
            'unit_price': round(unit_price, 2),
            'subtotal': round(subtotal, 2),
            'tax_amount': round(tax, 2),
            'discount_amount': round(discount, 2),
            'grand_total': round(grand_total, 2),
            'currency': 'EGP',
            'engine': 'Python Engine (CLIPS Compatible)',
        }