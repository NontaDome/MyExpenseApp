import streamlit as st
import gspread
import pandas as pd
import datetime
import plotly.express as px
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials as UserCredentials

# -------------------------------------------------------
# 1. ตั้งค่าหน้าเว็บ
# -------------------------------------------------------
st.set_page_config(page_title="My Expense App", page_icon="💰", layout="wide")

# -------------------------------------------------------
# 2. ระบบ Login (OAuth 2.0)
# -------------------------------------------------------
def check_login():
    if 'creds' not in st.session_state:
        if "code" in st.query_params:
            code = st.query_params["code"]
            try:
                client_config = {
                    "web": {
                        "client_id": st.secrets["web"]["client_id"],
                        "client_secret": st.secrets["web"]["client_secret"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                }
                flow = Flow.from_client_config(
                    client_config,
                    scopes=[
                        "https://www.googleapis.com/auth/spreadsheets",
                        "https://www.googleapis.com/auth/drive.file"
                    ],
                    redirect_uri=st.secrets["web"]["redirect_uri"]
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

if not check_login():
    st.title("🔒 กรุณาล็อกอิน")
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": st.secrets["web"]["client_id"],
                    "client_secret": st.secrets["web"]["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive.file"
            ],
            redirect_uri=st.secrets["web"]["redirect_uri"]
        )
        auth_url, _ = flow.authorization_url(prompt='consent')
        st.link_button("Sign in with Google", auth_url, type="primary")
    except:
        st.error("⚠️ ไม่พบการตั้งค่า Secrets")
    st.stop()

# -------------------------------------------------------
# 3. เชื่อมต่อ Google Sheets
# -------------------------------------------------------
try:
    creds = st.session_state['creds']
    gc = gspread.authorize(creds)
    
    with st.sidebar:
        st.success("✅ เชื่อมต่อแล้ว")
        if st.button("Logout", type="secondary"):
            del st.session_state['creds']
            if 'sheet_url' in st.session_state:
                del st.session_state['sheet_url']
            st.rerun()
        st.divider()

    if 'sheet_url' not in st.session_state:
        st.session_state['sheet_url'] = ''

    if not st.session_state['sheet_url']:
        st.info("👋 ยินดีต้อนรับ! กรุณาวางลิงก์ Google Sheet")
        st.markdown("""
        **โครงสร้างหัวตาราง (Row 1):**
        `Date` | `Time` | `Type` | `Account` | `Source` | `Destination` | `Channel` | `Amount` | `Note`
        """)
        url_input = st.text_input("🔗 วางลิงก์ Google Sheets ที่นี่")
        if url_input:
            st.session_state['sheet_url'] = url_input
            st.rerun()
        else:
            st.stop()

    sh = gc.open_by_url(st.session_state['sheet_url'])
    worksheet = sh.sheet1

except Exception as e:
    st.error(f"❌ เชื่อมต่อไม่ได้: {e}")
    if st.button("ใส่ลิงก์ใหม่"):
        st.session_state['sheet_url'] = ''
        st.rerun()
    st.stop()

# -------------------------------------------------------
# 4. โหลดข้อมูล (แก้ไขให้รองรับ 9 คอลัมน์)
# -------------------------------------------------------
def load_data_safe():
    # กำหนดหัวตารางที่ถูกต้องตามที่คุณต้องการ
    COLUMNS = ["Date", "Time", "Type", "Account", "Source", "Destination", "Channel", "Amount", "Note"]
    
    try:
        data = worksheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=COLUMNS)
        
        df = pd.DataFrame(data)
        
        # ตรวจสอบว่าคอลัมน์ไหนขาดหายไป ให้เติมเข้าไป
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = "" 
                
        # เลือกมาเฉพาะคอลัมน์ที่ใช้งานจริง เพื่อจัดเรียงให้สวยงาม
        return df[COLUMNS]
        
    except Exception as e:
        return pd.DataFrame(columns=COLUMNS)

df = load_data_safe()

# -------------------------------------------------------
# 5. UI Application
# -------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📝 บันทึก", "📊 สรุปผล", "📋 ประวัติ"])

# --- Tab 1: ฟอร์มบันทึก (แก้ไขให้ครบ 9 ช่อง) ---
with tab1:
    st.header("บันทึกรายการ (แบบละเอียด)")
    with st.form("expense_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            date_in = st.date_input("Date (วันที่)", value=datetime.date.today())
        with c2:
            time_in = st.time_input("Time (เวลา)", value=datetime.datetime.now().time())
        with c3:
            type_in = st.selectbox("Type (ประเภท)", ["รายจ่าย", "รายรับ"])

        c4, c5 = st.columns(2)
        with c4:
            account_in = st.selectbox("Account (บัญชี)", ["บัญชีออมทรัพย์", "บัญชีเงินฝากดอกเบี้ยสูง", "เงินสด", "บัตรเครดิต", "อื่นๆ"])
        with c5:
            amount_in = st.number_input("Amount (จำนวนเงิน)", min_value=0.0, step=10.0)

        c6, c7 = st.columns(2)
        with c6:
            source_in = st.text_input("Source (ต้นทาง)", placeholder="เช่น ชื่อคนโอน")
        with c7:
            dest_in = st.text_input("Destination (ปลายทาง)", placeholder="เช่น ร้านป้าแจ่ม")

        c8, c9 = st.columns(2)
        with c8:
            channel_in = st.selectbox("Channel (ช่องทาง)", ["App ธนาคาร", "เงินสด", "Scan QR", "บัตรเครดิต"])
        with c9:
            note_in = st.text_input("Note (หมายเหตุ)", placeholder="บันทึกเพิ่มเติม")
        
        if st.form_submit_button("💾 บันทึกข้อมูล", use_container_width=True):
            if amount_in > 0:
                try:
                    # เรียงข้อมูลให้ตรงกับหัวตาราง 9 ช่อง
                    row_data = [
                        str(date_in), 
                        str(time_in), 
                        type_in, 
                        account_in, 
                        source_in, 
                        dest_in, 
                        channel_in, 
                        amount_in, 
                        note_in
                    ]
                    worksheet.append_row(row_data)
                    st.success("บันทึกเรียบร้อย!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("กรุณาระบุจำนวนเงิน")

# --- Tab 2: Dashboard ---
with tab2:
    st.header("ภาพรวมการเงิน")
    
    if not df.empty:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        
        income = df[df['Type'] == 'รายรับ']['Amount'].sum()
        expense = df[df['Type'] == 'รายจ่าย']['Amount'].sum()
        balance = income - expense
        
        col1, col2, col3 = st.columns(3)
        col1.metric("รายรับ", f"{income:,.0f}")
        col2.metric("รายจ่าย", f"{expense:,.0f}")
        col3.metric("คงเหลือ", f"{balance:,.0f}")
        
        st.divider()
        
        # กราฟแท่งเปรียบเทียบตามบัญชี (Account)
        try:
            st.subheader("ยอดเงินแยกตามบัญชี (Account)")
            acc_summary = df.groupby(['Account', 'Type'])['Amount'].sum().reset_index()
            if not acc_summary.empty:
                fig = px.bar(acc_summary, x='Account', y='Amount', color='Type', barmode='group',
                             color_discrete_map={'รายรับ':'#28a745', 'รายจ่าย':'#dc3545'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลบัญชี")
        except:
            st.warning("ยังไม่สามารถแสดงกราฟได้")
            
    else:
        st.info("ยังไม่มีข้อมูล")

# --- Tab 3: History ---
with tab3:
    st.header("ประวัติรายการทั้งหมด")
    st.dataframe(df, use_container_width=True)