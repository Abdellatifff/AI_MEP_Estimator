import streamlit as st
import os
import json
import pandas as pd
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# 1. إعدادات الصفحة والتصميم الداكن
st.set_page_config(page_title="AI MEP Estimator", page_icon="🏗️", layout="wide")

st.markdown("""
<style>
    /* تصميم داكن احترافي مشابه للواجهة الأصلية */
    .stApp { background-color: #0a0e17; color: #c9d1d9; }
    .stTextArea textarea { background-color: #0d1117; color: #c9d1d9; border: 1px solid #21262d; }
    .stButton>button { background-color: #7b1fa2; color: white; border-radius: 6px; font-weight: bold; }
    .stButton>button:hover { background-color: #9c27b0; color: white; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; background-color: #0d1117; padding: 10px; border-radius: 8px; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; font-weight: bold; font-size: 16px; }
    .stTabs [aria-selected="true"] { color: #c792ea !important; border-bottom-color: #c792ea !important; }
    h1, h2, h3 { color: #c792ea !important; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d; }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ AI MEP Estimator")
st.markdown("نظام متكامل لاستخراج الكميات وتسعيرها (Groq AI + محرك الحسابات)")

# 2. تحميل قاعدة البيانات
@st.cache_data
def load_prices():
    try:
        with open('rules/price_tables.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"⚠️ خطأ في تحميل ملف الأسعار: {e}")
        return {}

prices_db = load_prices()

# 3. الشريط الجانبي
with st.sidebar:
    st.header("⚙️ الإعدادات")
    env_key = os.getenv("GROQ_API_KEY", "")
    try:
        if "GROQ_API_KEY" in st.secrets: env_key = st.secrets["GROQ_API_KEY"]
    except: pass
        
    api_key_input = st.text_input("مفتاح Groq API:", value=env_key, type="password")
    final_api_key = api_key_input.strip()
    
    if final_api_key: st.success("✅ المفتاح جاهز")
    else: st.warning("⚠️ أدخل المفتاح")
    
    st.info(f"📊 تم تحميل {len(prices_db)} جدول أسعار")

# 4. محرك التسعير (بديل CLIPS بلغة بايثون)
def calculate_pricing(item_name, size, action, quantity):
    # تحديد النظام (حريق، صرف، عام)
    system = "general"
    if "حريق" in item_name or "fire" in item_name.lower(): system = "fire"
    elif "صرف" in item_name or "sewage" in item_name.lower(): system = "sewage"
    
    # تحديد كود الإجراء (توريد، تركيب، اختبار)
    code = ""
    if "توريد" in action or "supply" in action.lower(): code += "S"
    if "تركيب" in action or "install" in action.lower(): code += "I"
    if "اختبار" in action or "test" in action.lower(): code += "T"
    if not code: code = "S" # افتراضي
    
    table_name = f"{system}_{code}"
    
    # إذا لم يوجد الجدول، نجرب الجدول الأساسي S
    if table_name not in prices_db:
        table_name = f"{system}_S"
        
    table = prices_db.get(table_name, {})
    size_data = table.get(str(size), {})
    
    if not size_data:
        return None
        
    # حساب السعر
    unit_price = sum(size_data.values())
    subtotal = unit_price * quantity
    tax = subtotal * 0.14 # ضريبة 14%
    before_discount = subtotal + tax
    
    discount = 0.0
    if quantity > 100:
        discount = before_discount * 0.05 # خصم 5%
        
    grand_total = before_discount - discount
    
    return {
        "table_used": table_name,
        "unit_price": unit_price,
        "subtotal": subtotal,
        "tax": tax,
        "discount": discount,
        "grand_total": grand_total
    }

# 5. إنشاء التبويبات (Tabs)
tab1, tab2 = st.tabs(["💬 المحادثة والتسعير", "💵 قاعدة الأسعار"])

# --- التبويب الأول ---
with tab1:
    with st.form("estimator_form"):
        project_description = st.text_area(
            "وصف البند:",
            height=100,
            placeholder="مثال: توريد وتركيب مواسير حريق 4 بوصة، الكمية 120"
        )
        submitted = st.form_submit_button("🚀 استخراج وتسعير")

    if submitted:
        if not final_api_key:
            st.error("⚠️ يرجى إدخال مفتاح Groq API.")
        elif not project_description.strip():
            st.warning("⚠️ الرجاء إدخال وصف المشروع.")
        else:
            with st.spinner("⏳ جاري تحليل النص بواسطة Groq وحساب التكلفة..."):
                try:
                    client = Groq(api_key=final_api_key)
                    prompt = f"""
                    Extract construction details from: "{project_description}"
                    Return ONLY a JSON object with these keys:
                    - "item_name" (string in Arabic)
                    - "size" (string, e.g., "3", "4", "6")
                    - "action" (string, e.g., "توريد وتركيب")
                    - "quantity" (number)
                    """
                    response = client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0,
                        response_format={"type": "json_object"} 
                    )
                    
                    data = json.loads(response.choices[0].message.content)
                    
                    result = calculate_pricing(
                        data.get("item_name", ""),
                        data.get("size", ""),
                        data.get("action", ""),
                        float(data.get("quantity", 0))
                    )
                    
                    if result:
                        st.success("✅ تم التسعير بنجاح!")
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("سعر الوحدة", f"{result['unit_price']:.2f} EGP")
                        col2.metric("الضريبة (14%)", f"{result['tax']:.2f} EGP")
                        col3.metric("الخصم", f"{result['discount']:.2f} EGP")
                        col4.metric("الإجمالي النهائي", f"{result['grand_total']:.2f} EGP")
                        
                        with st.expander("عرض تفاصيل الحساب (JSON)"):
                            st.json({"AI_Extracted": data, "Pricing_Engine": result})
                    else:
                        st.warning("⚠️ لم يتم العثور على سعر مطابق لهذا القطر في قاعدة البيانات.")
                        
                except Exception as e:
                    st.error(f"❌ حدث خطأ: {str(e)}")

# --- التبويب الثاني ---
with tab2:
    st.subheader("جداول الأسعار المتاحة")
    if prices_db:
        selected_table = st.selectbox("اختر جدولاً للعرض:", list(prices_db.keys()))
        if selected_table:
            df = pd.DataFrame.from_dict(prices_db[selected_table], orient='index')
            st.dataframe(df, use_container_width=True)
    else:
        st.warning("⚠️ قاعدة البيانات فارغة أو غير موجودة.")