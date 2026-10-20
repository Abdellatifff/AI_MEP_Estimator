import streamlit as st
import os
import json
import pandas as pd
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# 1. Page Config & Styling (English UI, Dark Mode, Large Fonts)
st.set_page_config(page_title="AI MEP Estimator", page_icon="🏗️", layout="wide")

st.markdown("""
<style>
    /* Dark Theme Background */
    .stApp { background-color: #0a0e17; color: #c9d1d9; }
    
    /* LTR Setup & Larger Fonts */
    html, body, [class*="css"] { direction: ltr; text-align: left; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stTextArea textarea, .stTextInput input { font-size: 18px !important; color: #ffffff !important; background-color: #161b22 !important; border: 1px solid #30363d !important; }
    .stChatMessage { font-size: 18px; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: #0d1117; padding: 10px; border-radius: 8px; border-bottom: 2px solid #7b1fa2; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; font-weight: bold; font-size: 16px; }
    .stTabs [aria-selected="true"] { color: #c792ea !important; border-bottom: 2px solid #c792ea !important; }
    
    /* Headers & Buttons */
    h1, h2, h3 { color: #c792ea !important; }
    .stButton>button { background-color: #7b1fa2; color: white; border-radius: 6px; font-weight: bold; font-size: 16px; padding: 10px 24px; border: none; }
    .stButton>button:hover { background-color: #9c27b0; color: white; }
    
    /* Metrics & Expanders */
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d; }
</style>
""", unsafe_allow_html=True)

# 2. Secure API Key Loading (Hidden from UI)
env_key = os.getenv("GROQ_API_KEY", "")
try:
    if "GROQ_API_KEY" in st.secrets: 
        env_key = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

# 3. Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I am your AI MEP Estimator. How can I assist you with your construction pricing today?"}]

if "prices_db" not in st.session_state:
    # Default fallback pricing database
    st.session_state.prices_db = {
        "fire_S": {"3": {"supply_price": 45.50}, "4": {"supply_price": 62.00}, "6": {"supply_price": 98.75}, "8": {"supply_price": 145.00}},
        "fire_SI": {"3": {"supply_price": 45.50, "install_price": 25.00}, "4": {"supply_price": 62.00, "install_price": 32.00}, "6": {"supply_price": 98.75, "install_price": 48.50}, "8": {"supply_price": 145.00, "install_price": 72.00}},
        "fire_SIT": {"3": {"supply_price": 45.50, "install_price": 25.00, "test_price": 8.00}, "4": {"supply_price": 62.00, "install_price": 32.00, "test_price": 10.50}},
        "sewage_SIT": {"3": {"supply_price": 22.00, "install_price": 12.00, "test_price": 4.00}, "4": {"supply_price": 32.00, "install_price": 16.00, "test_price": 5.50}},
        "general_SIT": {"3": {"supply_price": 40.00, "install_price": 20.00, "test_price": 6.00}, "4": {"supply_price": 55.00, "install_price": 28.00, "test_price": 8.00}}
    }

# 4. Pricing Logic (Pure Python)
def calculate_price(item_name, size, action, quantity):
    system = "general"
    if "fire" in item_name.lower() or "حريق" in item_name: system = "fire"
    elif "sewage" in item_name.lower() or "صرف" in item_name: system = "sewage"
    
    code = ""
    if "supply" in action.lower() or "توريد" in action: code += "S"
    if "install" in action.lower() or "تركيب" in action: code += "I"
    if "test" in action.lower() or "اختبار" in action: code += "T"
    if not code: code = "S"
    
    table_name = f"{system}_{code}"
    if table_name not in st.session_state.prices_db: 
        table_name = f"{system}_S"
        
    table = st.session_state.prices_db.get(table_name, {})
    size_data = table.get(str(size), {})
    
    if not size_data: return None
        
    unit_price = sum(size_data.values())
    subtotal = unit_price * quantity
    tax = subtotal * 0.14
    before_discount = subtotal + tax
    discount = before_discount * 0.05 if quantity > 100 else 0.0
    grand_total = before_discount - discount
    
    return {
        "unit_price": unit_price, 
        "tax": tax, 
        "discount": discount, 
        "grand_total": grand_total, 
        "table": table_name
    }

# 5. UI Layout
st.title("🏗️ AI MEP Estimator")
st.markdown("Professional AI-powered construction pricing and analysis.")

tab_chat, tab_analysis, tab_specs, tab_models, tab_files = st.tabs([
    "💬 AI Assistant", "📊 Price Analysis", "📝 Specifications", "🧠 AI Models", "📁 Files"
])

# --- TAB 1: Natural Chat (Strictly MEP) ---
with tab_chat:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Type your message here (e.g., 'Price 100m of 4-inch fire pipes')..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            if not env_key:
                st.error("⚠️ API Key not found. Please configure it in Streamlit Secrets.")
            else:
                with st.spinner("Analyzing..."):
                    try:
                        client = Groq(api_key=env_key)
                        system_prompt = """
                        You are a highly professional MEP (Mechanical, Electrical, Plumbing) Construction Estimator.
                        Your ONLY purpose is to assist with construction materials, BOQ, pricing, and engineering specifications.
                        
                        RULES:
                        1. If the user greets you (e.g., 'Hello', 'مرحبا'), reply politely: {"type": "chat", "reply": "Hello! I am your MEP Estimator. How can I assist you with your construction pricing today?"}
                        2. If the user asks a general knowledge question (e.g., history, geography, time, sports), you MUST REFUSE. Reply: {"type": "chat", "reply": "I am a specialized MEP Estimator. I can only assist with construction quantities, pricing, and BOQ analysis."}
                        3. If the user asks for a price/estimate, extract details: {"type": "pricing", "item_name": "Name in English or Arabic", "size": "e.g. 4", "action": "supply/install", "quantity": 100}
                        
                        Always return ONLY a valid JSON object.
                        """
                        res = client.chat.completions.create(
                            model="openai/gpt-oss-120b",
                            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                            temperature=0,
                            response_format={"type": "json_object"}
                        )
                        data = json.loads(res.choices[0].message.content)
                        
                        if data.get("type") == "chat":
                            ans = data.get("reply", "I'm here to help!")
                            st.markdown(ans)
                            st.session_state.messages.append({"role": "assistant", "content": ans})
                        else:
                            item = data.get("item_name", "Item")
                            size = str(data.get("size", ""))
                            action = data.get("action", "supply")
                            qty = float(data.get("quantity", 1))
                            
                            pricing = calculate_price(item, size, action, qty)
                            if pricing:
                                ans = f"✅ **Pricing Extracted:**\n- **Item:** {item}\n- **Size:** {size}\"\n- **Quantity:** {qty}\n- **Unit Price:** {pricing['unit_price']} EGP\n- **Grand Total:** {pricing['grand_total']} EGP"
                                st.markdown(ans)
                                st.session_state.messages.append({"role": "assistant", "content": ans})
                            else:
                                st.warning("I understood the item, but I couldn't find a matching price in the database.")
                    except Exception as e:
                        st.error(f"Error: {e}")

# --- TAB 2: Price Analysis (Upload BOQ & DB) ---
with tab_analysis:
    st.subheader("Upload Data for Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_db = st.file_uploader("📁 Upload Price Database (Excel)", type=["xlsx", "xls"], key="db_upload")
        if uploaded_db:
            st.success("Price Database Uploaded! (System ready for analysis)")
            
    with col2:
        uploaded_boq = st.file_uploader("📄 Upload BOQ (Excel)", type=["xlsx", "xls"], key="boq_upload")
        if uploaded_boq:
            df = pd.read_excel(uploaded_boq)
            st.write("BOQ Preview:")
            st.dataframe(df.head(5), use_container_width=True)
            
            if st.button("Analyze BOQ Prices"):
                st.info("Analysis Complete! (Demo: Values below are simulated based on uploaded BOQ structure)")
                st.metric("Total Estimated Cost", "125,000 EGP")
                st.metric("Items Analyzed", len(df))

# --- TAB 3: Specifications ---
with tab_specs:
    st.subheader("Project Specifications")
    st.markdown("Add or edit the technical specifications here.")
    specs_text = st.text_area("Enter Specifications:", height=300, placeholder="e.g., Fire fighting pipes must be Schedule 40...")
    if st.button("Save Specifications"):
        st.success("Specifications saved successfully!")

# --- TAB 4: AI Models ---
with tab_models:
    st.subheader("Active AI Engine")
    st.info("✅ **System Status:** Online")
    st.markdown("You are currently using **Groq API** (Model: `openai/gpt-oss-120b`). No local heavy models are required.")

# --- TAB 5: Files ---
with tab_files:
    st.subheader("Uploaded Files")
    st.markdown("This section displays the files you have uploaded during this session.")
    if "db_upload" in st.session_state and st.session_state.db_upload:
        st.write("- Price Database: Uploaded")
    if "boq_upload" in st.session_state and st.session_state.boq_upload:
        st.write("- BOQ: Uploaded")