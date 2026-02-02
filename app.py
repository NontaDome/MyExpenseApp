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

# การตั้งค่า OAuth (อ่านจาก secrets)
CLIENT_CONFIG = {
    "web": {
        "client_id": st.secrets["web"]["client_id"],
        "client_secret": st.secrets["web"]["client_secret"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}
# ต้องแก้ Redirect URI ให้ตรงกับที่รันอยู่ (localhost หรือ cloud)
REDIRECT_URI = st.secrets["web"]["redirect_uri"] 
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]

# ฟังก์ชันจัดการ Login
def check_login():
    # 1. เช็คว่ามี Token ใน Session หรือยัง (Login ค้างไว้ไหม)
    if 'creds' not in st.session_state:
        # ถ้ายังไม่มี ให้ดูว่า URL มี code ส่งกลับมาไหม (กลับมาจาก Google)
        if "code" in st.query_params:
            code = st.query_params["code"]
            
            # แลก Code เป็น Token
            flow = Flow.from_client_config(
                CLIENT_CONFIG,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI
            )
            flow.fetch_token(code=code)
            st.session_state['creds'] = flow.credentials
            
            # เคลียร์ URL ให้สวยงาม (ลบ code ออก)
            st.query_params.clear()
            st.rerun()
        else:
            # ถ้าไม่มี Code และไม่มี Token -> แสดงปุ่ม Login
            return False
    return True

# --- เริ่มต้นการทำงาน ---
if not check_login():
    st.title("🔒 กรุณาล็อกอิน")
    st.write("แอปนี้ใช้ Google Account ของคุณในการบันทึกข้อมูล (ข้อมูลเป็นส่วนตัว 100%)")
    
    # สร้างลิงก์ Login
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    
    st.link_button("Sign in with Google", auth_url, type="primary")
    st.stop() # หยุดทำงานแค่นี้ รอ User ล็อกอิน

# -------------------------------------------------------
# 2. เชื่อมต่อ Google Sheets (ในนามของผู้ใช้)
# -------------------------------------------------------
try:
    # ใช้ Credential ของผู้ใช้ที่ล็อกอินเข้ามา
    creds = st.session_state['creds']
    gc = gspread.authorize(creds)

    st.sidebar.success("✅ ล็อกอินแล้ว")
    if st.sidebar.button("Logout"):
        del st.session_state['creds']
        st.rerun()

    # ให้ผู้ใช้ใส่ลิงก์ Sheet ของตัวเอง (เหมือนเดิม แต่ไม่ต้องแชร์ให้ใครแล้ว!)
    if 'sheet_url' not in st.session_state:
        st.session_state['sheet_url'] = ''
    
    st.info("กรุณาสร้าง Google Sheet ของคุณเอง แล้วนำลิงก์มาวางด้านล่าง (ไม่ต้องแชร์ให้ใคร)")
    user_sheet_url = st.text_input("🔗 วางลิงก์ Google Sheets ของคุณ", value=st.session_state['sheet_url'])
    
    if user_sheet_url:
        st.session_state['sheet_url'] = user_sheet_url
        sh = gc.open_by_url(user_sheet_url)
        worksheet = sh.sheet1
    else:
        st.stop()

except Exception as e:
    st.error(f"เกิดข้อผิดพลาด: {e}")
    st.stop()

# -------------------------------------------------------
# 3. ส่วนโปรแกรมเดิม (วางต่อจากนี้ได้เลย)
# -------------------------------------------------------
# ... (วางโค้ด def load_data, highlight_rows และ UI เดิมต่อตรงนี้)

# -------------------------------------------------------
# 2. ส่วนหน้าจอแอป
# -------------------------------------------------------
st.title("💰 บันทึกรายรับ-รายจ่าย (Color Version)")

tab1, tab2 = st.tabs(["📝 บันทึกข้อมูล", "📊 วิเคราะห์แดชบอร์ด"])

# ================= แท็บ 1: บันทึกข้อมูล =================
with tab1:
    with st.form("expense_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1: date_input = st.date_input("วันที่", datetime.date.today())
        with c2: time_input = st.time_input("เวลา", value=datetime.datetime.now().time(), step=60)
        with c3: t_type = st.radio("ประเภท", ["รายจ่าย", "รายรับ"], horizontal=True)

        c4, c5 = st.columns(2)
        with c4: account = st.selectbox("บัญชี", ["บัญชีออมทรัพย์", "บัญชีเงินฝากดอกเบี้ยสูง", "เงินสด", "บัตรเครดิต", "อื่นๆ"])
        with c5: amount = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, step=1.0)

        c6, c7 = st.columns(2)
        with c6: source = st.text_input("ต้นทาง", placeholder="เช่น ชื่อคนโอน")
        with c7: destination = st.text_input("ปลายทาง", placeholder="เช่น ร้านค้า")

        c8, c9 = st.columns(2)
        with c8: channel = st.selectbox("ช่องทาง", ["App ธนาคาร", "เงินสด", "Scan QR", "บัตรเครดิต"])
        with c9: note = st.text_input("หมายเหตุ")
        
        submitted = st.form_submit_button("บันทึกข้อมูล ✅", use_container_width=True)

        if submitted:
            date_str = date_input.strftime("%Y-%m-%d")
            time_str = time_input.strftime("%H:%M:%S")
            row_data = [date_str, time_str, t_type, account, source, destination, channel, amount, note]
            worksheet.append_row(row_data)
            st.success("บันทึกเรียบร้อย!")
            st.cache_data.clear()

    st.divider()
    st.subheader("📋 ประวัติล่าสุด")
    df_history = load_data()
    if not df_history.empty:
        st.dataframe(
            df_history.tail(5).sort_index(ascending=False).style.applymap(highlight_rows), 
            use_container_width=True
        )

# ================= แท็บ 2: แดชบอร์ด =================
with tab2:
    st.header("📈 สรุปผลการเงิน")
    df = load_data()

    if not df.empty:
        df['Year'] = df['Date'].dt.year
        df['Month'] = df['Date'].dt.strftime('%Y-%m (เดือน)')
        df['Week'] = df['Date'].dt.strftime('%Y-W%U (สัปดาห์)')
        df['Day'] = df['Date'].dt.strftime('%Y-%m-%d')

        subtab1, subtab2, subtab3, subtab4 = st.tabs(["📅 รายวัน", "🗓️ รายสัปดาห์", "📆 รายเดือน", "📅 รายปี"])

        def show_summary(dataframe, group_col, title):
            summary = dataframe.groupby([group_col, 'Type'])['Amount'].sum().reset_index()
            pivot_df = summary.pivot(index=group_col, columns='Type', values='Amount').fillna(0)
            
            if 'รายรับ' not in pivot_df.columns: pivot_df['รายรับ'] = 0
            if 'รายจ่าย' not in pivot_df.columns: pivot_df['รายจ่าย'] = 0
            
            pivot_df['คงเหลือสุทธิ'] = pivot_df['รายรับ'] - pivot_df['รายจ่าย']
            pivot_df = pivot_df.sort_index(ascending=False)

            st.subheader(f"กราฟเปรียบเทียบ {title}")
            fig = px.bar(summary, x=group_col, y='Amount', color='Type', barmode='group',
                         color_discrete_map={'รายรับ':'#28a745', 'รายจ่าย':'#dc3545'}) 
            st.plotly_chart(fig, use_container_width=True)

            st.subheader(f"ตารางสรุป {title}")
            
            # 🛠️ แก้ไขสีตรงนี้ครับ: 
            # เปลี่ยนจาก 'color: blue' เป็น 'color: #00d4ff' (สีฟ้าสว่าง/Cyan) หรือ 'white' เพื่อให้อ่านง่าย
            styled_df = pivot_df.style.format("{:,.2f}") \
                .applymap(lambda x: 'color: #28a745; font-weight: bold', subset=['รายรับ']) \
                .applymap(lambda x: 'color: #dc3545; font-weight: bold', subset=['รายจ่าย']) \
                .applymap(lambda x: 'color: #00d4ff; font-weight: bold' if x > 0 else 'color: #ff4b4b; font-weight: bold', subset=['คงเหลือสุทธิ'])

            st.dataframe(styled_df, use_container_width=True)

        with subtab1: show_summary(df, 'Day', "รายวัน")
        with subtab2: show_summary(df, 'Week', "รายสัปดาห์")
        with subtab3: show_summary(df, 'Month', "รายเดือน")
        with subtab4: show_summary(df, 'Year', "รายปี")
            
        st.divider()
        with st.expander("🔎 ดูข้อมูลดิบทั้งหมด"):
            st.dataframe(df.sort_values(by='Date', ascending=False).style.applymap(highlight_rows), use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลในระบบ")