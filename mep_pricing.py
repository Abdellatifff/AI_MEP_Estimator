import os
import sys
import re
import pandas as pd
from thefuzz import process, fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier

def load_prices_database():
    db_file = "prices_database.xlsx"
    if not os.path.exists(db_file):
        print(f"❌ لم يتم العثور على ملف قاعدة بيانات الأسعار '{db_file}'")
        return None
    df = pd.read_excel(db_file)
    df.columns = df.columns.str.strip()
    df['material'] = df['material'].fillna('').astype(str)
    df['size'] = df['size'].fillna('').astype(str)
    df['connection'] = df['connection'].fillna('').astype(str)
    df['search_tag'] = df['material'] + " " + df['connection']
    return df

def extract_size_strictly(item_description):
    desc = str(item_description).lower().strip()
    clean_desc = re.sub(r'(جدول|schedule)\s*\d+', '', desc)
    size_match = re.search(r'(\d+)\s*(?:بوصة|بوصه|مقاس|\")|(?:مقاس|قطر)\s*(\d+)', clean_desc)
    if size_match:
        return str(size_match.group(1) or size_match.group(2)).strip()
    return None

def match_item_with_ai(item_description, prices_df):
    desc = str(item_description).lower().strip()
    
    clean_desc_for_size = re.sub(r'جدول\s*\d+', '', desc)
    clean_desc_for_size = re.sub(r'schedule\s*\d+', '', clean_desc_for_size)
    
    size_match = re.search(r'(\d+)\s*(?:بوصة|بوصه|مقاس|\")|(?:مقاس|قطر)\s*(\d+)', clean_desc_for_size)
    
    detected_size = None
    if size_match:
        detected_size = str(size_match.group(1) or size_match.group(2))
        filtered_df = prices_df[prices_df['size'].astype(str).str.strip() == detected_size.strip()]
    else:
        filtered_df = prices_df

    if filtered_df.empty:
        filtered_df = prices_df

    choices = filtered_df['search_tag'].tolist()
    best_match, score = process.extractOne(desc, choices, scorer=fuzz.partial_ratio)
    
    # تم التصحيح هنا ليعيد صف مالي حقيقي متوافق مع pandas
    matched_row = filtered_df[filtered_df['search_tag'] == best_match].iloc[0]
    return matched_row, score

class MyCustomMEPAI:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        self.model = RandomForestClassifier(n_estimators=50, random_state=42)
        
    def train_my_brain(self):
        training_data = [
            ("توريد مواسير شراء خامات خامه سابلاي supply material محابس قطع غيار", "supply_price"),
            ("تركيب مصنعيات مصنعية تركيبات عمالة عمال تنفيذ بالموقع installation labor", "installation_price"),
            ("لحام جروفد توصيل ربط جوينت قلاووظ welding grooving threading coupling connections", "welding_or_grooving"),
            ("دهان برايمر عزل عزل حراري دهانات وجه تحضيري حماية ضد الصدأ painting primer insulation", "painting_price"),
            ("تعاليق مثبتات حامل مواسير زوايا حديد أفيز كليب تيش كابولي supports hangers clamps", "supports_and_hangers"),
            ("اختبار شبكة غسيل مواسير كبس اختبار ضغط تشغيل تجريبي تسليم استشاري testing commissioning", "testing_and_commissioning"),
            ("ضريبة ضريبه القيمة المضافة شامل الضريبة والضريبه tax vat", "tax")
        ]
        
        texts = [item[0] for item in training_data]
        labels = [item[1] for item in training_data]
        
        X = self.vectorizer.fit_transform(texts)
        self.model.fit(X, labels)
        print("🧠 [العقل الخاص بك]: تم الانتهاء من التدريب الذاتي وفهم المصطلحات الهندسية محلياً!")

    def predict_required_columns(self, item_text):
        desc = str(item_text).lower()
        decisions = {
            "supply_price": False, "installation_price": False, "welding_or_grooving": False,
            "painting_price": False, "supports_and_hangers": False, "testing_and_commissioning": False, "tax": False
        }
        
        words = desc.split()
        for word in words:
            if len(word) < 3: continue
            try:
                X_word = self.vectorizer.transform([word])
                probabilities = self.model.predict_proba(X_word)
                classes = self.model.classes_
                
                for idx, cls in enumerate(classes):
                    if probabilities[0][idx] > 0.15:
                        decisions[cls] = True
            except:
                pass
                
        if not any(decisions.values()):
            decisions["supply_price"] = True
            decisions["installation_price"] = True
            
        return decisions

def calculate_custom_ai_price(matched_row, ai_decisions):
    total_cost = 0.0
    available_columns = list(matched_row.index)
    
    for column, is_required in ai_decisions.items():
        if column != 'tax' and column in available_columns and is_required:
            try: 
                total_cost += float(matched_row[column])
            except: 
                pass
            
    tax = 0.0
    if ai_decisions.get('tax', False):
        if 'ضريبه' in available_columns:
            try: tax = float(matched_row['ضريبه'])
            except: pass
        elif 'ضريبة' in available_columns:
            try: tax = float(matched_row['ضريبة'])
            except: pass

    return round(total_cost + tax, 2)

def run_pricing():
    print("🔄 جاري قراءة قاعدة البيانات المحلية...")
    prices_db = load_prices_database()
    if prices_db is None: return

    my_ai = MyCustomMEPAI()
    my_ai.train_my_brain()

    boq_file = "boq.xlsx"
    if not os.path.exists(boq_file):
        print(f"⚠️ يرجى التأكد من وجود ملف المقايسة باسم '{boq_file}'")
        return

    boq_df = pd.read_excel(boq_file)
    boq_df.columns = boq_df.columns.str.strip()
    
    unit_rates, total_prices, pricing_status = [], [], []
    
    print("🚀 جاري فك وتسعير بنود المقايسة بالعقل الاصطناعي الخاص بك...")
    for idx, row in boq_df.iterrows():
        original_item_text = row['Item_Description']
        
        if pd.isna(original_item_text):
            unit_rates.append(0.0); total_prices.append(0.0); pricing_status.append("Empty Row")
            continue
            
        matched_data, confidence_score = match_item_with_ai(original_item_text, prices_db)
        
        if confidence_score >= 50:
            ai_decisions = my_ai.predict_required_columns(original_item_text)
            rate = calculate_custom_ai_price(matched_data, ai_decisions)
            
            try:
                qty_val = row['Quantity']
                qty = float(qty_val) if not pd.isna(qty_val) else 0.0
            except:
                qty = 0.0
                
            total = round(rate * qty, 2)
            status = f"Priced by My AI - ({confidence_score}%)"
        else:
            rate, total, status = 0.0, 0.0, f"Not Found - ({confidence_score}%)"
            
        unit_rates.append(rate); total_prices.append(total); pricing_status.append(status)
        
    boq_df['Unit_Rate_EGP'] = unit_rates
    boq_df['Total_Price_EGP'] = total_prices
    boq_df['Pricing_Status'] = pricing_status
    
    output_filename = "boq_priced_final.xlsx"
    try:
        boq_df.to_excel(output_filename, index=False)
        print(f"\n✨ مبروك! نجح تشغيل العقل الخاص بك بالكامل بنجاح أوفلاين.")
        print(f"📁 الملف الجاهز للمراجعة الفورية: {output_filename}")
    except PermissionError:
        print(f"\n⚠️ يرجى إغلاق ملف الإكسيل المفتوح أولاً ثم أعد التشغيل!")

if __name__ == "__main__":
    run_pricing()
