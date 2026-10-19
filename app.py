# -*- coding: utf-8 -*-
import os, sys, json, threading, webbrowser, time, io, re, gc, atexit, csv
from datetime import datetime
from pathlib import Path

# إعداد المسار ليعمل على جهازك وعلى السحابة
BASE_DIR = Path(__file__).resolve().parent
os.chdir(str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR))

from flask import Flask, render_template_string, request, jsonify
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

try:
    from engine.pricing_engine import PricingEngine, description_to_action_code
    pricing_engine = PricingEngine()
    print("[OK] Pricing engine loaded")
except Exception as e:
    print("[!] Pricing engine failed: " + str(e))
    pricing_engine = None

app = Flask(__name__)

# محاكاة حالة الموديلات لكي لا تظهر رسائل خطأ (بما أننا نستخدم Groq)
class MockModelManager:
    def __init__(self):
        self.active = "Groq-API"
    def status(self):
        return {
            'models': {
                'groq': {'key': 'groq', 'name': 'Groq (Llama-3.3-70b)', 'type': 'llm', 'size_mb': 0, 'loaded': True, 'loading': False, 'error': None, 'active': True, 'can_orchestrate': True}
            },
            'active': self.active,
            'ram': {'used_gb': 0, 'total_gb': 0, 'percent': 0}
        }
mm = MockModelManager()

# ============================================================
# HTML (نفس التصميم الذي في الصور الخمسة)
# ============================================================
HTML = r"""
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<title>AI MEP Estimator - CLIPS</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Tahoma,sans-serif}
body{background:#0a0e17;color:#c9d1d9;height:100vh;display:flex;flex-direction:column;overflow:hidden}
.hdr{background:#161b22;padding:10px 20px;display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #7b1fa2}
.hdr h1{color:#c792ea;font-size:16px}
.hdr .stats{font-size:12px;color:#8b949e}
.hdr .stats b{color:#3fb950}
.hdr .stats .active{color:#c792ea}
.tabs{background:#0d1117;display:flex;border-bottom:1px solid #21262d;padding:0 15px;overflow-x:auto}
.tab{padding:10px 20px;cursor:pointer;font-size:13px;font-weight:bold;color:#8b949e;border-bottom:2px solid transparent;transition:all .2s;white-space:nowrap}
.tab:hover{color:#c9d1d9}
.tab.on{color:#c792ea;border-bottom-color:#c792ea}
.tab .badge{background:#c62828;color:#fff;padding:1px 6px;border-radius:8px;font-size:10px;margin-right:5px}
.page{flex:1;overflow-y:auto;padding:15px;display:none}
.page.on{display:block}
.chat{display:flex;flex-direction:column;height:calc(100vh - 130px)}
.messages{flex:1;overflow-y:auto;background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:15px;margin-bottom:10px}
.msg{margin-bottom:12px;padding:10px 14px;border-radius:8px;font-size:14px;line-height:1.7;white-space:pre-wrap;word-wrap:break-word}
.msg.user{background:#1a2a3a;margin-left:60px}
.msg.bot{background:#2a1a3a;border-right:3px solid #c792ea;margin-right:60px}
.msg.sys{background:#1a2a1a;color:#ffd700;font-size:11px;padding:5px 10px;margin-bottom:6px;border-radius:4px}
.msg.err{background:#2a1a1a;color:#f44;font-size:12px}
.msg.tool{background:#0a2a2a;color:#80cbc4;font-size:12px;border-right:3px solid #00897b;padding:8px 12px;margin:5px 0}
.input-bar{display:flex;gap:8px}
.input-bar textarea{flex:1;padding:12px;background:#0d1117;border:2px solid #21262d;border-radius:6px;color:#c9d1d9;font-size:14px;min-height:60px;resize:vertical;font-family:inherit}
.input-bar textarea:focus{outline:none;border-color:#7b1fa2}
.btn{padding:10px 20px;border:none;border-radius:6px;font-weight:bold;cursor:pointer;color:white;font-size:13px}
.btn:hover{opacity:.85}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-p{background:#7b1fa2}
.btn-g{background:#238636}
.btn-r{background:#c62828}
.btn-b{background:#1976d2}
.btn-o{background:#e65100}
.models-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px}
.mcard{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;position:relative}
.mcard.act{border-color:#c792ea;box-shadow:0 0 0 2px #c792ea inset}
.mcard .nm{font-weight:bold;margin-bottom:6px}
.mcard .meta{font-size:11px;color:#8b949e;margin-bottom:8px}
.mcard .btns{display:flex;gap:5px;flex-wrap:wrap}
.mcard button{padding:4px 10px;border:none;border-radius:4px;font-size:11px;font-weight:bold;cursor:pointer;color:white}
.mcard .tag{position:absolute;top:8px;left:8px;padding:2px 8px;border-radius:10px;font-size:9px;font-weight:bold}
.t-llm{background:#1f6feb}
.pricing-toolbar{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.pricing-result{background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:15px;overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:8px 12px;text-align:right;border-bottom:1px solid #21262d}
th{background:#161b22;color:#c792ea;font-weight:bold;position:sticky;top:0}
tr:hover{background:#161b22}
tr.err{background:#2a1a1a}
tr.ok{background:transparent}
.total-row{background:#1a2a1a;font-weight:bold;color:#3fb950;font-size:15px}
.empty{text-align:center;color:#8b949e;padding:40px;font-size:14px}
.sys-tag{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:bold;margin-left:5px}
.sys-fire{background:#c62828;color:#fff}
.sys-sewage{background:#00897b;color:#fff}
.sys-general{background:#616161;color:#fff}
</style>
</head>
<body>

<div class="hdr">
<h1>🏗️ AI MEP Estimator</h1>
<div class="stats">
  RAM: <b id="ram">?</b> |
  Orchestrator: <b class="active" id="active">GROQ API</b> |
  CLIPS: <b id="clips">?</b> |
  جداول: <b id="tablesCount">0</b>
</div>
</div>

<div class="tabs">
  <div class="tab on" data-page="chat">💬 المحادثة</div>
  <div class="tab" data-page="pricing">💰 التسعير</div>
  <div class="tab" data-page="pricedb">💵 الأسعار</div>
  <div class="tab" data-page="models">🧠 الموديلات</div>
  <div class="tab" data-page="files">📁 الملفات</div>
</div>

<div class="page on" id="page-chat">
  <div class="chat">
    <div class="messages" id="messages"></div>
    <div class="input-bar">
      <textarea id="userInput" placeholder="اكتب سؤالك... مثال: سعّر 100 متر مواسير حريق 6 بوصة توريد وتركيب مع الضريبة"></textarea>
      <button class="btn btn-p" id="sendBtn" onclick="send()">إرسال</button>
    </div>
  </div>
</div>

<div class="page" id="page-pricing">
  <div class="pricing-toolbar">
    <button class="btn btn-o" onclick="document.getElementById('boqFile').click()">📊 رفع BOQ (Excel)</button>
    <input type="file" id="boqFile" accept=".xlsx,.xls" style="display:none" onchange="uploadBOQ(event)">
    <button class="btn btn-g" onclick="priceSingle()">💵 تسعير بند واحد</button>
    <button class="btn btn-r" onclick="clearBOQ()">🗑️ مسح</button>
  </div>
  <div id="pricingContent">
    <div class="empty">لم يتم رفع BOQ بعد. اضغط "رفع BOQ" لبدء التسعير.</div>
  </div>
</div>

<div class="page" id="page-pricedb">
  <div class="pricing-toolbar">
    <button class="btn btn-b" onclick="reloadEngine()">🔄 إعادة تحميل المحرك</button>
  </div>
  <div id="priceDbInfo" style="margin-bottom:12px;color:#8b949e;font-size:13px">جارٍ التحميل...</div>
  <div id="priceDbContent"></div>
</div>

<div class="page" id="page-models">
  <div style="margin-bottom:12px;display:flex;gap:8px">
    <div style="color:#c792ea;font-weight:bold;padding:10px;">✅ أنت تستخدم الآن ذكاء Groq الاصطناعي السحابي (لا حاجة لتحميل موديلات ثقيلة).</div>
  </div>
  <div class="models-grid" id="modelsGrid"></div>
</div>

<div class="page" id="page-files">
  <div class="empty">لا توجد ملفات مرفوعة حالياً.</div>
</div>

<script>
var bz = false;

document.querySelectorAll('.tab').forEach(function(t) {
  t.onclick = function() {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('on'));
    document.querySelectorAll('.page').forEach(x => x.classList.remove('on'));
    t.classList.add('on');
    document.getElementById('page-' + t.dataset.page).classList.add('on');
    if (t.dataset.page === 'pricedb') loadPriceDb();
  };
});

function addMsg(type, text) {
  var d = document.createElement('div');
  d.className = 'msg ' + type;
  d.textContent = text;
  var box = document.getElementById('messages');
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
}

async function send() {
  if (bz) return;
  var inp = document.getElementById('userInput');
  var q = inp.value.trim();
  if (!q) return;
  inp.value = '';
  addMsg('user', q);
  bz = true;
  document.getElementById('sendBtn').disabled = true;
  try {
    var r = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query: q})
    });
    var d = await r.json();
    if (d.success) {
      if (d.tools) addMsg('tool', '🔧 الأدوات المستخدمة: ' + d.tools);
      addMsg('bot', d.answer);
    } else {
      addMsg('err', 'خطأ: ' + d.error);
    }
  } catch(e) {
    addMsg('err', 'خطأ في الاتصال: ' + e.message);
  }
  bz = false;
  document.getElementById('sendBtn').disabled = false;
  inp.focus();
}

document.getElementById('userInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && e.ctrlKey) {
    e.preventDefault();
    send();
  }
});

async function refreshStatus() {
  try {
    var r = await fetch('/status');
    var d = await r.json();
    document.getElementById('clips').textContent = d.clips_ready ? '✅' : '❌';
    document.getElementById('tablesCount').textContent = d.tables_count || 0;
    renderModels(d);
  } catch(e) {}
}

function renderModels(d) {
  var grid = document.getElementById('modelsGrid');
  if (!grid) return;
  grid.innerHTML = '';
  for (var k in d.models) {
    var m = d.models[k];
    var card = document.createElement('div');
    card.className = 'mcard' + (m.active ? ' act' : '');
    var tagClass = 't-' + m.type;
    card.innerHTML =
      '<span class="tag ' + tagClass + '">' + m.type + '</span>' +
      '<div class="nm">' + m.name + '</div>' +
      '<div class="meta">سحابي (Cloud)<br>جاهز للاستخدام</div>' +
      '<div class="btns"><button class="btn-p">★ نشط</button></div>';
    grid.appendChild(card);
  }
}

async function priceSingle() {
  var desc = prompt('وصف البند:');
  if (!desc) return;
  var size = prompt('القطر (3، 4، 6، 8):', '6');
  if (!size) return;
  var action = prompt('الإجراء:', 'توريد وتركيب');
  if (!action) return;
  var system = prompt('النظام (fire / sewage / general):', 'general');
  if (!system) return;
  var qty = prompt('الكمية:', '1');
  if (!qty) return;
  var tax = confirm('إضافة ضريبة 14%؟');
  var r = await fetch('/price_item', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({item_description: desc, size: size, action: action, system: system, quantity: parseFloat(qty), include_tax: tax})});
  var d = await r.json();
  if (d.success) {
    alert('نتيجة CLIPS:\n\nالنظام: ' + d.result.system + '\nالكود: ' + d.result.action_code + '\nسعر الوحدة: ' + d.result.unit_price + '\nالإجمالي: ' + d.result.grand_total + ' EGP\n\nالجدول: ' + d.result.price_table);
  } else {
    alert('خطأ: ' + d.error);
  }
}

async function reloadEngine() {
  var r = await fetch('/reload_engine', {method:'POST'});
  var d = await r.json();
  alert(d.success ? '✅ المحرك جاهز (' + d.tables_count + ' جدول)' : '❌ فشل');
  loadPriceDb();
  refreshStatus();
}

async function loadPriceDb() {
  try {
    var r = await fetch('/list_price_tables');
    var d = await r.json();
    var info = document.getElementById('priceDbInfo');
    var c = document.getElementById('priceDbContent');
    if (!d.success || d.rows.length === 0) {
      info.innerHTML = '⚠️ لا توجد أسعار بعد. تأكد من وجود ملف price_tables.json';
      c.innerHTML = '';
      return;
    }
    info.innerHTML = '<b style="color:#3fb950">✅ ' + d.count + ' جدول</b> مع ' + d.rows.length + ' سطر سعر';
    var html = '<div class="pricing-result"><table>';
    html += '<thead><tr><th>الجدول</th><th>القطر</th><th>توريد</th><th>تركيب</th><th>اختبار</th><th>سعر الوحدة</th></tr></thead><tbody>';
    for (var i = 0; i < d.rows.length; i++) {
      var r = d.rows[i];
      var comp = r.components;
      var s = comp.supply_price || 0;
      var ins = comp.install_price || 0;
      var t = comp.test_price || 0;
      html += '<tr><td>' + r.table + '</td><td>' + r.size + '</td><td>' + (s ? s.toFixed(2) : '-') + '</td><td>' + (ins ? ins.toFixed(2) : '-') + '</td><td>' + (t ? t.toFixed(2) : '-') + '</td><td><b>' + (s+ins+t).toFixed(2) + '</b></td></tr>';
    }
    html += '</tbody></table></div>';
    c.innerHTML = html;
  } catch(e) {}
}

addMsg('sys', 'جاهز. اكتب طلبك وسيقوم Groq بتحليله ثم يحسبه محرك CLIPS.');
setInterval(refreshStatus, 4000);
refreshStatus();
loadPriceDb();
</script>
</body>
</html>
"""

# ============================================================
# Routes
# ============================================================
@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/status')
def status_route():
    s = mm.status()
    s['clips_ready'] = (pricing_engine is not None and pricing_engine.env is not None)
    s['tables_count'] = (len(pricing_engine.price_tables) if pricing_engine else 0)
    return jsonify(s)

@app.route('/chat', methods=['POST'])
def chat_route():
    d = request.json or {}
    q = (d.get('query') or '').strip()
    if not q:
        return jsonify({'success': False, 'error': 'empty query'})
    
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return jsonify({'success': False, 'error': 'مفتاح Groq API غير موجود. يرجى إضافته في ملف .env'})

    try:
        client = Groq(api_key=api_key)
        prompt = f"""
        You are an expert construction quantity surveyor.
        Extract construction item details from this text: "{q}"
        Return ONLY a valid JSON object with these exact keys:
        - "item_name" (string, in Arabic)
        - "size" (string, e.g., "3", "4", "6" for inches)
        - "connection" (string, choose from: "Grooved", "Welded", "Solvent Welded", or "General")
        - "action" (string, extract the actions in Arabic or English, e.g., "توريد وتركيب")
        - "quantity" (number)
        """
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"} 
        )
        
        data = json.loads(response.choices[0].message.content)
        
        if pricing_engine:
            result = pricing_engine.price_item(
                item_description=data.get("item_name", ""),
                size=data.get("size", ""),
                connection=data.get("connection", "Grooved"),
                action_code=None,
                quantity=float(data.get("quantity", 0)),
                include_tax=True
            )
            
            if result.get('success'):
                answer = f"✅ تم التسعير بنجاح بواسطة CLIPS:\n\n"
                answer += f"البند: {result['item']}\n"
                answer += f"القطر: {result['size']}\"\n"
                answer += f"الكمية: {result['quantity']}\n"
                answer += f"سعر الوحدة: {result['unit_price']} EGP\n"
                answer += f"الإجمالي (مع الضريبة والخصم): {result['grand_total']} EGP\n"
                return jsonify({'success': True, 'answer': answer, 'tools': 'Groq + CLIPS'})
            else:
                return jsonify({'success': False, 'error': f"CLIPS Error: {result.get('error')}"})
        else:
            return jsonify({'success': False, 'error': 'محرك CLIPS غير متاح'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/price_item', methods=['POST'])
def price_item_route():
    d = request.json or {}
    if pricing_engine:
        r = pricing_engine.price_item(
            d.get('item_description', ''),
            d.get('size', ''),
            connection=d.get('connection', 'Grooved'),
            action_code=d.get('action', ''),
            quantity=d.get('quantity', 0),
            include_tax=d.get('include_tax', False),
        )
        r['system'] = d.get('system', 'general')
        if r.get('success'):
            return jsonify({'success': True, 'result': r})
        return jsonify({'success': False, 'error': r.get('error', '?')})
    return jsonify({'success': False, 'error': 'محرك CLIPS غير متاح'})

@app.route('/reload_engine', methods=['POST'])
def reload_engine_route():
    if pricing_engine is None:
        return jsonify({'success': False, 'error': 'محرك CLIPS غير متاح'})
    ok = pricing_engine.reload()
    return jsonify({'success': ok, 'tables_count': len(pricing_engine.price_tables)})

@app.route('/list_price_tables')
def list_price_tables_route():
    if pricing_engine is None:
        return jsonify({'success': False, 'tables': [], 'rows': [], 'count': 0})
    summary = []
    for name, sizes in pricing_engine.price_tables.items():
        for size, comps in sizes.items():
            summary.append({'table': name, 'size': size, 'components': comps})
    return jsonify({'success': True, 'count': len(pricing_engine.price_tables), 'rows': summary})

@app.route('/clear_boq', methods=['POST'])
def clear_boq_route():
    return jsonify({'success': True})

@app.route('/upload_boq', methods=['POST'])
def upload_boq_route():
    return jsonify({'success': False, 'error': 'ميزة رفع BOQ غير مفعلة في هذه النسخة السريعة.'})

# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    def ob():
        time.sleep(1.5)
        try: webbrowser.open('http://127.0.0.1:5000')
        except Exception: pass

    print("=" * 60)
    print("AI MEP Estimator Web — http://127.0.0.1:5000")
    print("=" * 60)
    threading.Thread(target=ob, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)