# -*- coding: utf-8 -*-
"""Pricing Engine v8 - Flags based"""
import json
from pathlib import Path

try:
    import clips
except ImportError:
    clips = None
    print("[!] clipspy not installed")

BASE_DIR = Path(__file__).resolve().parent.parent
RULES_DIR = BASE_DIR / "rules"
TABLES_FILE = RULES_DIR / "price_tables.json"
RULES_FILE = RULES_DIR / "pricing_rules.clp"


def _read_text(path):
    try:
        return path.read_text(encoding='utf-8-sig')
    except Exception:
        return path.read_text(encoding='utf-8')


def compute_flags(description, action_code=""):
    """يحدد المكونات المطلوبة من النص + action_code."""
    d = (description or '').lower()
    c = (action_code or '').upper()
    return {
        'use_supply': 'yes' if ('S' in c or 'توريد' in d or 'supply' in d or 'provide' in d) else 'no',
        'use_install': 'yes' if ('I' in c or 'تركيب' in d or 'install' in d) else 'no',
        'use_welding': 'yes' if ('W' in c or 'جروفد' in d or 'groov' in d or 'غراء' in d or 'solvent' in d or 'welded' in d or 'لحام' in d) else 'no',
        'use_painting': 'yes' if ('P' in c or 'دهان' in d or 'برايمر' in d or 'paint' in d or 'primer' in d) else 'no',
        'use_supports': 'yes' if ('H' in c or 'مثبت' in d or 'تعاليق' in d or 'support' in d or 'hanger' in d or 'fastener' in d or 'bracket' in d) else 'no',
        'use_testing': 'yes' if ('T' in c or 'اختبار' in d or 'test' in d or 'commission' in d) else 'no',
    }


def description_to_action_code(description):
    d = (description or '').lower()
    code = ""
    if 'توريد' in d or 'supply' in d or 'provide' in d: code += 'S'
    if 'تركيب' in d or 'install' in d: code += 'I'
    if 'جروفد' in d or 'groov' in d or 'غراء' in d or 'solvent' in d or 'welded' in d or 'لحام' in d: code += 'W'
    if 'دهان' in d or 'برايمر' in d or 'paint' in d or 'primer' in d: code += 'P'
    if 'مثبت' in d or 'تعاليق' in d or 'support' in d or 'hanger' in d or 'fastener' in d or 'bracket' in d: code += 'H'
    if 'اختبار' in d or 'test' in d or 'commission' in d: code += 'T'
    return code if code else 'S'


class PricingEngine:
    def __init__(self):
        self.env = None
        self.price_tables = {}
        self._load_tables()
        self._load_clips()

    def _load_tables(self):
        if TABLES_FILE.exists():
            try:
                data = _read_text(TABLES_FILE).lstrip('\ufeff')
                self.price_tables = json.loads(data) if data.strip() else {}
                print("[+] Loaded " + str(len(self.price_tables)) + " tables")
            except Exception as e:
                print("[!] load: " + str(e))
                self.price_tables = {}

    def _load_clips(self):
        if clips is None or not RULES_FILE.exists():
            return
        try:
            self.env = clips.Environment()
            self.env.load(str(RULES_FILE))
            if self.price_tables:
                self.env.build(self._build_deffacts())
            self.env.reset()
            n = sum(1 for f in self.env.facts() if f.template.name == 'price_row')
            print("[+] CLIPS: " + str(n) + " price facts")
        except Exception as e:
            print("[!] CLIPS: " + str(e))
            self.env = None

    def _build_deffacts(self):
        lines = ["(deffacts price-data"]
        for tbl, sizes in self.price_tables.items():
            for size, comps in sizes.items():
                for cname, price in comps.items():
                    lines.append(
                        '  (price_row (table_name "' + str(tbl) +
                        '") (size "' + str(size) +
                        '") (component "' + str(cname) +
                        '") (price ' + str(float(price)) + '))'
                    )
        lines.append(")")
        return "\n".join(lines)

    def reload(self):
        self.env = None
        self.price_tables = {}
        self._load_tables()
        self._load_clips()
        return self.env is not None

    def save_tables(self, tables):
        TABLES_FILE.parent.mkdir(parents=True, exist_ok=True)
        TABLES_FILE.write_text(json.dumps(tables, ensure_ascii=False, indent=2),
                               encoding='utf-8', newline='\n')
        self.price_tables = tables
        return self.reload()

    def price_item(self, item_description, size, connection='Grooved',
                   action_code=None, quantity=0, include_tax=False):
        if self.env is None:
            return {'success': False, 'error': 'engine not loaded'}
        if not self.price_tables:
            return {'success': False, 'error': 'prices empty'}

        flags = compute_flags(item_description, action_code or "")

        self.env.reset()
        try:
            t = self.env.find_template('boq_item')
            t.assert_fact(
                item_description=str(item_description),
                size=str(size).strip(),
                connection=str(connection),
                use_supply=flags['use_supply'],
                use_install=flags['use_install'],
                use_welding=flags['use_welding'],
                use_painting=flags['use_painting'],
                use_supports=flags['use_supports'],
                use_testing=flags['use_testing'],
                quantity=float(quantity),
                include_tax='yes' if include_tax else 'no',
            )
        except Exception as e:
            return {'success': False, 'error': 'assert: ' + str(e)}

        try:
            self.env.run()
        except Exception as e:
            return {'success': False, 'error': 'run: ' + str(e)}

        err = None
        res = None
        for f in self.env.facts():
            if f.template.name == 'error_result':
                err = f['message']
            elif f.template.name == 'pricing_result':
                res = f

        if err:
            return {'success': False, 'error': err}
        if res is None:
            return {'success': False, 'error': 'no result'}

        return {
            'success': True,
            'item': res['item_description'],
            'size': res['size'],
            'connection': res['connection'],
            'action_code': (action_code or description_to_action_code(item_description)),
            'quantity': float(res['quantity']),
            'rule_applied': res['table_name'],
            'price_table': res['table_name'],
            'unit_price': round(float(res['unit_price']), 2),
            'subtotal': round(float(res['subtotal']), 2),
            'tax_amount': round(float(res['tax_amount']), 2),
            'discount_amount': round(float(res['discount_amount']), 2),
            'grand_total': round(float(res['grand_total']), 2),
            'currency': 'EGP',
            'engine': 'CLIPS v8',
        }


if __name__ == "__main__":
    e = PricingEngine()
    print("Tables:", len(e.price_tables))
    print("Ready:", e.env is not None)
    if e.env:
        tests = [
            ("توريد وتركيب 3 بوصة جروفد", "3", "Grooved", 10, True),
            ("توريد وتركيب 4 بوصة", "4", "Grooved", 80, True),
            ("PVC 4 بوصة غراء", "4", "Solvent Welded", 210, True),
        ]
        for desc, size, conn, qty, tax in tests:
            r = e.price_item(desc, size, conn, quantity=qty, include_tax=tax)
            print()
            print("--- " + desc + " | " + conn + " size=" + size + " ---")
            if r.get('success'):
                print("  Unit:  " + str(r['unit_price']))
                print("  Total: " + str(r['grand_total']))
            else:
                print("  Error: " + r.get('error', '?'))