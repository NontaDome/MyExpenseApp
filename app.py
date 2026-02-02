import streamlit as st
import gspread
import pandas as pd
import datetime
import plotly.express as px
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials as UserCredentials

# -------------------------------------------------------
# 1. ตั้งค่าพื้นฐาน (ต้องอยู่บรรทัดแรกๆ)
# -------------------------------------------------------
st.set_page_config(page_title="My Expense App", page_icon="💰", layout="wide")

# อ่านค่า Secrets
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
    st.error("❌ ไม่พบการตั้งค่า Secrets กรุณาเช็คที่ Streamlit Cloud")
    st.stop()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]

# -------------------------------------------------------
# 2. ฟังก์ชันระบบ Login (ต้องประกาศก่อนเรียกใช้)
# -------------------------------------------------------
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
                st.error(f"Login ผิดพลาด: {e}")
                st.stop()
        else:
            return False
    return True

# เรียกใช้ฟังก์ชัน Login
if not check_login():
    st.title("🔒 กรุณาล็อกอิน")
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    st.link_button("Sign in with Google", auth_url, type="primary")
    st.stop() 

# -------------------------------------------------------
# 3. เชื่อมต่อ Google Sheets
# -------------------------------------------------------
try:
    creds = st.session_state['creds']
    gc = gspread.authorize(creds)
    
    # Sidebar: ปุ่ม Logout
    with st.sidebar:
        st.success(f"✅ ล็อกอินสำเร็จ")
        if st.button("Logout", type="secondary"):
            del st.session_state['creds']
            if 'sheet_url' in st.session_state:
                del st.session_state['sheet_url']
            st.rerun()
        st.divider()

    # ตรวจสอบ URL Sheet
    if 'sheet_url' not in st.session_state:
        st.session_state['sheet_url'] = ''

    if not st.session_state['sheet_url']:
        st.info("👋 ยินดีต้อนรับ! กรุณาวางลิงก์ Google Sheet ของคุณ")
        user_sheet_url = st.text_input("🔗 วางลิงก์ที่นี่ (ต้องมีหัวตาราง Date, Time, Type, Category, Amount, Note)")
        if user_sheet_url:
            st.session_state['sheet_url'] = user_sheet_url
            st.rerun()
        else:
            st.stop()

    # เปิด Sheet
    sh = gc.open_by_url(st.session_state['sheet_url'])
    worksheet = sh.sheet1

except Exception as e:
    st.error(f"❌ เชื่อมต่อไม่ได้: {e}")
    if st.button("กรอกลิงก์ใหม่"):
        st.session_state['sheet_url'] = ''
        st.rerun()
    st.stop()

# -------------------------------------------------------
# 4. โหลดข้อมูลและแสดงผล (ส่วนหลัก)
# -------------------------------------------------------

# ฟังก์ชันโหลดข้อมูล
def load_data():
    try:
        data = worksheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=["Date", "Time", "Type", "Category", "Amount", "Note"])
        return pd.DataFrame(data)
    except:
        return pd.DataFrame(columns=["Date", "Time", "Type", "Category", "Amount", "Note"])

# โหลดข้อมูลจริง
df = load_data()

# สร้าง Tabs
tab1, tab2, tab3 = st.tabs(["📝 บันทึก", "📊 สรุปผล", "📋 ประวัติ"])

# --- Tab 1: ฟอร์มบันทึก ---
with tab1:
    st.header("บันทึกรายรับ-รายจ่าย")
    # สำคัญ: ทุกอย่างใน Form ต้องย่อหน้าเข้าไป
    with st.form("expense_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            date_in = st.date_input("วันที่", value=datetime.date.today())
            time_in = st.time_input("เวลา", value=datetime.datetime.now().time())
        with c2:
            type_in = st.selectbox("ประเภท", ["รายจ่าย", "รายรับ"])
            amount_in = st.number_input("จำนวนเงิน", min_value=0.0, step=10.0)
            
        category_in = st.text_input("หมวดหมู่", placeholder="เช่น อาหาร, เดินทาง")
        note_in = st.text_input("โน้ต", placeholder="กันลืม")
        
        # ปุ่ม Submit ต้องอยู่ใน block ของ with st.form
        submitted = st.form_submit_button("💾 บันทึกข้อมูล", use_container_width=True)
        
        if submitted:
            if amount_in > 0:
                worksheet.append_row([
                    str(date_in), str(time_in), type_in, 
                    category_in, amount_in, note_in
                ])
                st.success("บันทึกเรียบร้อย!")
                st.rerun()
            else:
                st.warning("กรุณาระบุจำนวนเงิน")

# --- Tab 2: Dashboard ---
with tab2:
    st.header("ภาพรวมการเงิน")
    if not df.empty:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        
        # คำนวณยอด
        income = df[df['Type'] == 'รายรับ']['Amount'].sum()
        expense = df[df['Type'] == 'รายจ่าย']['Amount'].sum()
        balance = income - expense
        
        # แสดง Card
        c1, c2, c3 = st.columns(3)
        c1.metric("รายรับ", f"{income:,.0f}")
        c2.metric("รายจ่าย", f"{expense:,.0f}")
        c3.metric("คงเหลือ", f"{balance:,.0f}")
        
        # กราฟ Pie
        exp_data = df[df['Type'] == 'รายจ่าย']
        if not exp_data.empty:
            fig = px.pie(exp_data, values='Amount', names='Category', title='สัดส่วนรายจ่าย')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลให้แสดง")

# --- Tab 3: Table ---
with tab3:
    st.header("ประวัติรายการ")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.write("ว่างเปล่า...")