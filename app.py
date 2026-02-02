import streamlit as st
import gspread
import pandas as pd
import datetime
import plotly.express as px
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials as UserCredentials

# -------------------------------------------------------
# 1. ตั้งค่าและระบบ Login (OAuth 2.0)
# -------------------------------------------------------
st.set_page_config(page_title="My Expense App", page_icon="💰", layout="wide")

# ตรวจสอบ Secrets
try:
    CLIENT_CONFIG = {
        "web": {
            "client_id": st.secrets["web"]["client_id"],
            "client_secret": st.secrets["web"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    REDIRECT_URI = st.secrets["web"]["redirect_uri"]
except:
    st.error("❌ ไม่พบการตั้งค่า Secrets! กรุณาตรวจสอบเมนู Settings > Secrets บน Streamlit Cloud")
    st.stop()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]

def check_login():
    if 'creds' not in st.session_state:
        if "code" in st.query_params:
            code = st.query_params["code"]
            try:
                flow = Flow.from_client_config(
                    CLIENT_CONFIG,
                    scopes=SCOPES,
                    redirect_uri=REDIRECT_URI
                )
                flow.fetch_token(code=code)
                st.session_state['creds'] = flow.credentials
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Login Error: {e}")
                st.stop()
        else:
            return False
    return True

# --- เริ่มต้น Login Check ---
if not check_login():
    st.title("🔒 กรุณาล็อกอิน")
    st.write("เข้าสู่ระบบด้วย Google Account เพื่อบันทึกรายรับ-รายจ่ายส่วนตัว")
    
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    
    st.link_button("Sign in with Google", auth_url, type="primary")
    st.stop() 

# -------------------------------------------------------
# 2. เชื่อมต่อ Google Sheets
# -------------------------------------------------------
try:
    creds = st.session_state['creds']
    gc = gspread.authorize(creds)

    with st.sidebar:
        st.success(f"✅ ล็อกอินแล้ว")
        if st.button("Logout", type="secondary"):
            del st.session_state['creds']
            if 'sheet_url' in st.session_state:
                del st.session_state['sheet_url']
            st.rerun()
        st.divider()
        
    # เช็ค URL Sheet
    if 'sheet_url' not in st.session_state:
        st.session_state['sheet_url'] = ''

    if not st.session_state['sheet_url']:
        st.info("👋 ยินดีต้อนรับ! กรุณาสร้าง Google Sheet ใหม่ แล้วนำ URL มาวางที่นี่")
        st.markdown("""
        **วิธีเตรียม Google Sheet:**
        1. สร้าง Sheet ใหม่
        2. แถวแรก (Row 1) ตั้งชื่อหัวตารางตามนี้: `Date`, `Time`, `Type`, `Category`, `Amount`, `Note`
        """)
        user_sheet_url = st.text_input("🔗 วางลิงก์ Google Sheets ของคุณ")
        
        if user_sheet_url:
            st.session_state['sheet_url'] = user_sheet_url
            st.rerun()
        else:
            st.stop()

    # เชื่อมต่อ Worksheet
    sh = gc.open_by_url(st.session_state['sheet_url'])
    worksheet = sh.sheet1

except Exception as e:
    st.error(f"❌ เชื่อมต่อไม่ได้ หรือ ลิงก์ผิด: {e}")
    if st.button("กรอกลิงก์ใหม่"):
        st.session_state['sheet_url'] = ''
        st.rerun()
    st.stop()

# -------------------------------------------------------
# 3. ส่วนการทำงานหลัก (นิยามฟังก์ชันก่อนเรียกใช้เสมอ)
# -------------------------------------------------------

# 1. นิยามฟังก์ชันโหลดข้อมูล (ต้องอยู่ตรงนี้ ก่อนจะถูกเรียกใช้)
def load_data():
    try:
        all_records = worksheet.get_all_records()
        if not all_records:
            return pd.DataFrame(columns=["Date", "Time", "Type", "Category", "Amount", "Note"])
        return pd.DataFrame(all_records)
    except:
        return pd.DataFrame(columns=["Date", "Time", "Type", "Category", "Amount", "Note"])

# 2. เรียกใช้ฟังก์ชัน
df = load_data()

# 3. สร้างหน้าจอ UI
tab1, tab2, tab3 = st.tabs(["📝 บันทึกรายการ", "📊 แดชบอร์ด", "📋 ประวัติทั้งหมด"])

# --- Tab 1: บันทึก ---
with tab1:
    st.header("จดบันทึก")
    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date_input = st.date_input("วันที่", value=datetime.date.today())
            time_input = st.time_input("เวลา", value=datetime.datetime.now().time())
        with col2:
            type_input = st.selectbox("ประเภท", ["รายจ่าย", "รายรับ"])
            amount_input = st.number_input("จำนวนเงิน", min_value=0.0, step=10.0)

        category_input