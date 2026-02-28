import streamlit as st
import gspread
import pandas as pd
import datetime
import plotly.express as px
import extra_streamlit_components as stx 
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials as UserCredentials

# ==========================================
# 🔐 ตั้งค่ารหัส PIN (เปลี่ยนได้ที่นี่)
# ==========================================
USER_PIN = "123456" 
# ==========================================

st.set_page_config(page_title="My Expense App", page_icon="💰", layout="wide")

# CSS แต่งหน้าจอ
st.markdown("""
    <style>
    .stButton>button { border-radius: 20px; height: 50px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------
# 1. ระบบจัดการ Cookie & PIN
# -------------------------------------------------------
cookie_manager = stx.CookieManager()

if 'locked' not in st.session_state:
    st.session_state['locked'] = True 

def verify_pin():
    if st.session_state.pin_input == USER_PIN:
        st.session_state['locked'] = False
        st.session_state.pin_input = ""
    else:
        st.error("❌ รหัส PIN ไม่ถูกต้อง")

def lock_app():
    st.session_state['locked'] = True
    st.rerun()

# -------------------------------------------------------
# 2. ระบบ Login (Auto-Login 10 ปี)
# -------------------------------------------------------
def get_google_auth_config():
    return {
        "web": {
            "client_id": st.secrets["web"]["client_id"],
            "client_secret": st.secrets["web"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

def check_login():
    if 'creds' in st.session_state:
        return True

    refresh_token = cookie_manager.get(cookie="google_refresh_token")
    
    if refresh_token:
        try:
            client_config = get_google_auth_config()
            creds = UserCredentials(
                None, 
                refresh_token=refresh_token,
                token_uri=client_config["web"]["token_uri"],
                client_id=client_config["web"]["client_id"],
                client_secret=client_config["web"]["client_secret"]
            )
            st.session_state['creds'] = creds
            return True
        except Exception as e:
            st.warning("Session หมดอายุ กรุณาล็อกอินใหม่")
            return False

    if "code" in st.query_params:
        code = st.query_params["code"]
        try:
            client_config = get_google_auth_config()
            flow = Flow.from_client_config(
                client_config,
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"],
                redirect_uri=st.secrets["web"]["redirect_uri"]
            )
            flow.fetch_token(code=code)
            st.session_state['creds'] = flow.credentials
            
            expires = datetime.datetime.now() + datetime.timedelta(days=3650)
            cookie_manager.set("google_refresh_token", flow.credentials.refresh_token, expires_at=expires)
            
            st.query_params.clear()
            return True
        except Exception as e:
            st.error(f"Login Error: {e}")
            st.stop()
    
    return False

if not check_login():
    st.title("🔒 Security Check")
    st.info("กรุณาล็อกอิน Google ครั้งแรก (ระบบจะจำไว้ 10 ปี)")
    try:
        flow = Flow.from_client_config(
            get_google_auth_config(),
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"],
            redirect_uri=st.secrets["web"]["redirect_uri"]
        )
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        st.link_button("🔐 เข้าสู่ระบบด้วย Google", auth_url, type="primary", use_container_width=True)
    except:
        st.error("⚠️ ไม่พบ Secrets")
    st.stop()

if st.session_state['locked']:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🔑 กรุณาใส่ PIN")
        st.write(f"สวัสดีครับ! ระบบจำการล็อกอิน Google ไว้แล้ว")
        st.text_input("ใส่รหัส 6 หลักเพื่อปลดล็อก", type="password", key="pin_input", on_change=verify_pin)
        st.caption(f"Default PIN: {USER_PIN}")
    st.stop()

# -------------------------------------------------------
# 3. เชื่อมต่อ Google Sheets (จำลิงก์ 10 ปี)
# -------------------------------------------------------
try:
    creds = st.session_state['creds']
    gc = gspread.authorize(creds)
    
    with st.sidebar:
        st.success("✅ สถานะ: พร้อมใช้งาน")
        if st.button("🔒 ล็อกหน้าจอ", type="primary"):
            lock_app()
        st.divider()
        if st.button("🔄 อัปเดตข้อมูลล่าสุด", use_container_width=True):
            st.rerun()
            
        if st.button("✏️ เปลี่ยนลิงก์ Google Sheet", use_container_width=True):
            cookie_manager.delete("user_sheet_url")
            st.session_state['sheet_url'] = ''
            st.rerun()
            
        if st.button("ออกจากระบบ (ล้างค่าทั้งหมด)", type="secondary"):
            cookie_manager.delete("google_refresh_token")
            cookie_manager.delete("user_sheet_url")
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    saved_sheet_url = cookie_manager.get(cookie="user_sheet_url")
    if 'sheet_url' not in st.session_state: 
        st.session_state['sheet_url'] = saved_sheet_url if saved_sheet_url else ''

    if not st.session_state['sheet_url']:
        st.info("👋 ยินดีต้อนรับ! กรุณาวางลิงก์ Google Sheet (ระบบจะจำไว้ให้ 10 ปี)")
        url_input = st.text_input("🔗 วางลิงก์ Google Sheets ที่นี่")
        if url_input:
            st.session_state['sheet_url'] = url_input
            expires = datetime.datetime.now() + datetime.timedelta(days=3650)
            cookie_manager.set("user_sheet_url", url_input, expires_at=expires)
            st.rerun()
        else:
            st.stop()

    sh = gc.open_by_url(st.session_state['sheet_url'])
    worksheet = sh.sheet1

except Exception as e:
    st.error(f"❌ เชื่อมต่อไม่ได้ หรือลิงก์อาจไม่ถูกต้อง: {e}")
    if st.button("ใส่ลิงก์ใหม่"):
        cookie_manager.delete("user_sheet_url")
        st.session_state['sheet_url'] = ''
        st.rerun()
    st.stop()

# -------------------------------------------------------
# 4. โหลดข้อมูล & UI
# -------------------------------------------------------
def load_data_safe():
    COLUMNS = ["Date", "Time", "Type", "Account", "Source", "Destination", "Channel", "Amount", "Note"]
    try:
        data = worksheet.get_all_records()
        if not data: return pd.DataFrame(columns=COLUMNS)
        df = pd.DataFrame(data)
        for col in COLUMNS:
            if col not in df.columns: df[col] = "" 
        df = df[COLUMNS]
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Day'] = df['Date'].dt.strftime('%Y-%m-%d')
        df['Month'] = df['Date'].dt.strftime('%Y-%m')
        df['Year'] = df['Date'].dt.strftime('%Y')
        df['Week'] = df['Date'].dt.strftime('%Y-W%U')
        return df
    except: return pd.DataFrame(columns=COLUMNS)

df = load_data_safe()

st.title("💰 My Expense App")
tab1, tab2, tab3 = st.tabs(["📝 จดบันทึก", "📊 แดชบอร์ด", "📋 ประวัติ"])

with tab1:
    with st.container(border=True):
        st.subheader("ทำรายการใหม่")
        with st.form("expense_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: date_in = st.date_input("Date", value=datetime.date.today())
            with c2: time_in = st.time_input("Time", value=datetime.datetime.now().time())
            with c3: type_in = st.selectbox("Type", ["รายจ่าย", "รายรับ"])

            c4, c5 = st.columns(2)
            # แก้ไข: ย้ายมาอยู่ตรงนี้ (Account)
            with c4: account_in = st.selectbox("Account", ["บัญชีออมทรัพย์", "บัญชีเงินฝากดอกเบี้ยสูง", "เงินสด", "บัตรเครดิต", "อื่นๆ"])
            with c5: amount_in = st.number_input("Amount", min_value=0.0, step=10.0)

            c6, c7 = st.columns(2)
            with c6: source_in = st.text_input("Source")
            with c7: dest_in = st.text_input("Destination")

            c8, c9 = st.columns(2)
            # แก้ไข: เอาออกจากตรงนี้ (Channel) คืนค่าเดิม
            with c8: channel_in = st.selectbox("Channel", ["App ธนาคาร", "เงินสด", "Scan QR", "บัตรเครดิต"])
            with c9: note_in = st.text_input("Note")
            
            if st.form_submit_button("💾 ยืนยัน", use_container_width=True):
                if amount_in > 0:
                    try:
                        worksheet.append_row([str(date_in), str(time_in), type_in, account_in, source_in, dest_in, channel_in, amount_in, note_in])
                        st.success("บันทึกแล้ว!")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
                else: st.warning("ระบุยอดเงิน")

with tab2:
    if not df.empty and df['Amount'].sum() > 0:
        def show_summary(dataframe, group_col, title):
            summary = dataframe.groupby([group_col, 'Type'])['Amount'].sum().reset_index()
            fig = px.bar(summary, x=group_col, y='Amount', color='Type', barmode='group',
                         color_discrete_map={'รายรับ':'#28a745', 'รายจ่าย':'#dc3545'}, text_auto='.2s')
            st.plotly_chart(fig, use_container_width=True)
            pivot = summary.pivot(index=group_col, columns='Type', values='Amount').fillna(0)
            if 'รายรับ' not in pivot.columns: pivot['รายรับ'] = 0
            if 'รายจ่าย' not in pivot.columns: pivot['รายจ่าย'] = 0
            pivot['คงเหลือ'] = pivot['รายรับ'] - pivot['รายจ่าย']
            st.dataframe(pivot.sort_index(ascending=False).style.format("{:,.2f}"), use_container_width=True)

        t1, t2, t3, t4 = st.tabs(["รายวัน", "รายสัปดาห์", "รายเดือน", "รายปี"])
        with t1: show_summary(df, 'Day', "รายวัน")
        with t2: show_summary(df, 'Week', "รายสัปดาห์")
        with t3: show_summary(df, 'Month', "รายเดือน")
        with t4: show_summary(df, 'Year', "รายปี")
    else: st.info("ไม่มีข้อมูล")

with tab3:
    if not df.empty:
        st.dataframe(df.sort_values(by='Date', ascending=False), use_container_width=True)
    else: st.write("ว่างเปล่า")