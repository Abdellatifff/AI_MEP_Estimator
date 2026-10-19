# -*- coding: utf-8 -*-
from pathlib import Path

RULES_DIR = Path(r"D:\AI_MEP_Estimator\rules")
RULES_DIR.mkdir(parents=True, exist_ok=True)

clp = r''';;
;; Pricing Rules v6 - Components-based
;;

(deftemplate boq_item
   (slot item_description (type STRING))
   (slot size (type STRING))
   (slot connection (type STRING))
   (slot action_code (type STRING))
   (slot quantity (type FLOAT))
   (slot include_tax (type STRING) (default "no")))

(deftemplate price_row
   (slot table_name (type STRING))
   (slot size (type STRING))
   (slot component (type STRING))
   (slot price (type FLOAT)))

(deftemplate selected_table
   (slot table_name (type STRING)))

(deftemplate pricing_result
   (slot item_description (type STRING))
   (slot size (type STRING))
   (slot connection (type STRING))
   (slot action_code (type STRING))
   (slot quantity (type FLOAT))
   (slot table_name (type STRING))
   (slot unit_price (type FLOAT))
   (slot subtotal (type FLOAT))
   (slot tax_amount (type FLOAT))
   (slot discount_amount (type FLOAT))
   (slot grand_total (type FLOAT))
   (slot breakdown (type STRING)))

(deftemplate error_result
   (slot message (type STRING)))

(deffunction component-included (?comp ?code)
   (if (eq ?comp "supply_price") then
       (return (> (str-index "S" ?code) 0)))
   (if (eq ?comp "installation_price") then
       (return (> (str-index "I" ?code) 0)))
   (if (eq ?comp "welding_or_grooving") then
       (return (> (str-index "W" ?code) 0)))
   (if (eq ?comp "painting_price") then
       (return (> (str-index "P" ?code) 0)))
   (if (eq ?comp "supports_and_hangers") then
       (return (> (str-index "H" ?code) 0)))
   (if (eq ?comp "testing_and_commissioning") then
       (return (> (str-index "T" ?code) 0)))
   (return FALSE))

(defrule select_table
   (declare (salience 100))
   (boq_item (connection ?conn))
   =>
   (assert (selected_table (table_name ?conn))))

(defrule error_no_rule
   (declare (salience 5))
   (boq_item (connection ?conn))
   (not (selected_table))
   =>
   (assert (error_result
      (message (str-cat "لا يوجد جدول للـ connection: " ?conn)))))

(defrule error_no_price
   (declare (salience 40))
   (boq_item (size ?size))
   (selected_table (table_name ?tbl))
   (not (price_row (table_name ?tbl) (size ?size)))
   =>
   (assert (error_result
      (message (str-cat "لا توجد أسعار للقطر " ?size " في " ?tbl)))))

(defrule calculate_pricing
   (declare (salience 30))
   (boq_item (item_description ?desc) (size ?size) (connection ?conn)
             (action_code ?code) (quantity ?q) (include_tax ?tax_flag))
   (selected_table (table_name ?tbl))
   (price_row (table_name ?tbl) (size ?size))
   (not (error_result))
   (not (pricing_result))
   =>
   (bind ?unit 0.0)
   (bind ?bd "")
   (do-for-all-facts ((?pr price_row))
      (and (eq ?pr:table_name ?tbl) (eq ?pr:size ?size))
      (if (component-included ?pr:component ?code) then
          (bind ?unit (+ ?unit ?pr:price))
          (bind ?bd (str-cat ?bd ?pr:component "=" ?pr:price " "))))

   (bind ?subtotal (* ?unit ?q))

   (bind ?tax 0.0)
   (if (eq ?tax_flag "yes") then
      (bind ?tax (* ?subtotal 0.14)))

   (bind ?before_discount (+ ?subtotal ?tax))

   (bind ?discount 0.0)
   (if (> ?q 100) then
      (bind ?discount (* ?before_discount 0.05)))

   (bind ?grand (- ?before_discount ?discount))

   (assert (pricing_result
      (item_description ?desc)
      (size ?size)
      (connection ?conn)
      (action_code ?code)
      (quantity ?q)
      (table_name ?tbl)
      (unit_price ?unit)
      (subtotal ?subtotal)
      (tax_amount ?tax)
      (discount_amount ?discount)
      (grand_total ?grand)
      (breakdown ?bd))))
'''

(RULES_DIR / "pricing_rules.clp").write_text(clp, encoding='utf-8', newline='\n')
print("[+] pricing_rules.clp written")

eng = r'''# -*- coding: utf-8 -*-
"""Pricing Engine v6 - Components based"""
import json
from pathlib import Path

try:
    import clips
except ImportError:
    clips = None
    print("[!] clipspy غير مثبت")

BASE_DIR = Path(r"D:\AI_MEP_Estimator")
RULES_DIR = BASE_DIR / "rules"
TABLES_FILE = RULES_DIR / "price_tables.json"
RULES_FILE = RULES_DIR / "pricing_rules.clp"


def _read_text(path):
    try:
        return path.read_text(encoding='utf-8-sig')
    except Exception:
        return path.read_text(encoding='utf-8')


def description_to_action_code(description):
    d = (description or '').lower()
    code = ""
    if 'توريد' in d or 'supply' in d or 'provide' in d:
        code += 'S'
    if 'تركيب' in d or 'install' in d:
        code += 'I'
    if 'جروفد' in d or 'groov' in d or 'غراء' in d or 'solvent' in d or 'welded' in d or 'لحام' in d:
        code += 'W'
    if 'دهان' in d or 'برايمر' in d or 'paint' in d or 'primer' in d:
        code += 'P'
    if 'مثبت' in d or 'تعاليق' in d or 'support' in d or 'hanger' in d or 'fastener' in d or 'bracket' in d:
        code += 'H'
    if 'اختبار' in d or 'test' in d or 'commission' in d:
        code += 'T'
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
                print("[!] load tables: " + str(e))
                self.price_tables = {}
        else:
            print("[i] no tables")

    def _load_clips(self):
        if clips is None:
            return
        if not RULES_FILE.exists():
            print("[!] rules not found")
            return
        try:
            self.env = clips.Environment()
            self.env.load(str(RULES_FILE))
            if self.price_tables:
                self.env.build(self._build_deffacts())
            self.env.reset()
            n = sum(1 for f in self.env.facts() if f.template.name == 'price_row')
            print("[+] CLIPS loaded: " + str(n) + " price facts")
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
            return {'success': False, 'error': 'محرك CLIPS غير محمّل'}
        if not self.price_tables:
            return {'success': False, 'error': 'قاعدة الأسعار فارغة'}

        if not action_code:
            action_code = description_to_action_code(item_description)

        self.env.reset()
        try:
            t = self.env.find_template('boq_item')
            t.assert_fact(
                item_description=str(item_description),
                size=str(size).strip(),
                connection=str(connection),
                action_code=str(action_code),
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
            'action_code': res['action_code'],
            'quantity': float(res['quantity']),
            'rule_applied': res['table_name'],
            'price_table': res['table_name'],
            'unit_price': round(float(res['unit_price']), 2),
            'subtotal': round(float(res['subtotal']), 2),
            'tax_amount': round(float(res['tax_amount']), 2),
            'discount_amount': round(float(res['discount_amount']), 2),
            'grand_total': round(float(res['grand_total']), 2),
            'breakdown_raw': str(res['breakdown']),
            'currency': 'EGP',
            'engine': 'CLIPS',
        }


if __name__ == "__main__":
    e = PricingEngine()
    print("Tables:", len(e.price_tables))
    print("Ready:", e.env is not None)
'''

(BASE_DIR := Path(r"D:\AI_MEP_Estimator")) / "engine"
(BASE_DIR / "engine" / "pricing_engine.py").write_text(eng, encoding='utf-8', newline='\n')
print("[+] pricing_engine.py written")