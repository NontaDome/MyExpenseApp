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
    # ตรวจสอบ Session State
    if 'creds' not in st.session_state:
        # ถ้าไม่มี Token ให้เช็คว่ามี Code ส่งกลับมาจาก Google ไหม
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
                # ล้าง URL ให้สะอาด แต่ไม่สั่ง Rerun เพื่อไม่ให้ Loop
                st.query_params.clear()
            except Exception as e:
                st.error(f"Login Error: {e}")
                st.stop()
        else:
            return False
    return True

if not check_login():
    st.title("🔒 กรุณาล็อกอิน")
    st.write("เข้าสู่ระบบเพื่อใช้งาน (ระบบจะจดจำการล็อกอินไว้ชั่วคราว)")
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
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
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
        st.success("✅ สถานะ: ออนไลน์")
        if st.button("ออกจากระบบ (Logout)", type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        st.divider()

    if 'sheet_url' not in st.session_state:
        st.session_state['sheet_url'] = ''

    if not st.session_state['sheet_url']:
        st.info("👋 ยินดีต้อนรับ! กรุณาวางลิงก์ Google Sheet")
        st.markdown("**ต้องการหัวตาราง 9 ช่อง:** `Date` | `Time` | `Type` | `Account` | `Source` | `Destination` | `Channel` | `Amount` | `Note`")
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
# 4. โหลดข้อมูล (9 Columns + Analysis Prep)
# -------------------------------------------------------
def load_data_safe():
    COLUMNS = ["Date", "Time", "Type", "Account", "Source", "Destination", "Channel", "Amount", "Note"]
    try:
        data = worksheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=COLUMNS)
        
        df = pd.DataFrame(data)
        
        # เติมคอลัมน์ที่ขาด
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = "" 
        
        # คัดเลือกเฉพาะ 9 คอลัมน์หลัก
        df = df[COLUMNS]

        # แปลงข้อมูลเพื่อการวิเคราะห์ (Analysis Features)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # สร้างคอลัมน์ช่วยวิเคราะห์ (Day, Month, Year, Week)
        df['Day'] = df['Date'].dt.strftime('%Y-%m-%d')
        df['Month'] = df['Date'].dt.strftime('%Y-%m')
        df['Year'] = df['Date'].dt.strftime('%Y')
        df['Week'] = df['Date'].dt.strftime('%Y-W%U')

        return df
        
    except Exception as e:
        return pd.DataFrame(columns=COLUMNS)

df = load_data_safe()

# -------------------------------------------------------
# 5. UI Application
# -------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📝 บันทึกรายการ", "📊 วิเคราะห์แดชบอร์ด", "📋 ประวัติทั้งหมด"])

# --- Tab 1: ฟอร์มบันทึก (9 ช่อง) ---
with tab1:
    st.header("บันทึกรายรับ-รายจ่าย")
    with st.form("expense_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1: date_in = st.date_input("Date (วันที่)", value=datetime.date.today())
        with c2: time_in = st.time_input("Time (เวลา)", value=datetime.datetime.now().time())
        with c3: type_in = st.selectbox("Type (ประเภท)", ["รายจ่าย", "รายรับ"])

        c4, c5 = st.columns(2)
        with c4: account_in = st.selectbox("Account (บัญชี)", ["บัญชีออมทรัพย์", "บัญชีเงินฝากดอกเบี้ยสูง", "เงินสด", "บัตรเครดิต", "อื่นๆ"])
        with c5: amount_in = st.number_input("Amount (จำนวนเงิน)", min_value=0.0, step=10.0)

        c6, c7 = st.columns(2)
        with c6: source_in = st.text_input("Source (ต้นทาง)")
        with c7: dest_in = st.text_input("Destination (ปลายทาง)")

        c8, c9 = st.columns(2)
        with c8: channel_in = st.selectbox("Channel (ช่องทาง)", ["App ธนาคาร", "เงินสด", "Scan QR", "บัตรเครดิต"])
        with c9: note_in = st.text_input("Note (หมายเหตุ)")
        
        if st.form_submit_button("💾 บันทึกข้อมูล", use_container_width=True):
            if amount_in > 0:
                try:
                    row_data = [
                        str(date_in), str(time_in), type_in, account_in, 
                        source_in, dest_in, channel_in, amount_in, note_in
                    ]
                    worksheet.append_row(row_data)
                    st.success("บันทึกเรียบร้อย!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("กรุณาระบุจำนวนเงิน")

# --- Tab 2: Dashboard (ฟีเจอร์ที่หายไป กลับมาแล้ว!) ---
with tab2:
    st.header("📈 วิเคราะห์รายรับ-รายจ่าย")
    
    if not df.empty and df['Amount'].sum() > 0:
        # ฟังก์ชันช่วยสร้างกราฟและตาราง
        def show_summary(dataframe, group_col, title):
            # Group ข้อมูล
            summary = dataframe.groupby([group_col, 'Type'])['Amount'].sum().reset_index()
            
            # Pivot เพื่อทำตารางสรุป
            pivot_df = summary.pivot(index=group_col, columns='Type', values='Amount').fillna(0)
            if 'รายรับ' not in pivot_df.columns: pivot_df['รายรับ'] = 0
            if 'รายจ่าย' not in pivot_df.columns: pivot_df['รายจ่าย'] = 0
            pivot_df['คงเหลือสุทธิ'] = pivot_df['รายรับ'] - pivot_df['รายจ่าย']
            pivot_df = pivot_df.sort_index(ascending=False) # เรียงใหม่ไปเก่า

            st.subheader(f"📊 กราฟ {title}")
            # กราฟแท่ง แยกสี เขียว/แดง
            fig = px.bar(summary, x=group_col, y='Amount', color='Type', barmode='group',
                         color_discrete_map={'รายรับ':'#28a745', 'รายจ่าย':'#dc3545'},
                         text_auto='.2s')
            st.plotly_chart(fig, use_container_width=True)

            st.subheader(f"📋 ตาราง {title}")
            # จัดรูปแบบตัวเลขทศนิยม และใส่สีในตาราง
            st.dataframe(
                pivot_df.style.format("{:,.2f}")
                .applymap(lambda x: 'color: #28a745; font-weight: bold', subset=['รายรับ'])
                .applymap(lambda x: 'color: #dc3545; font-weight: bold', subset=['รายจ่าย'])
                .applymap(lambda x: 'color: #00d4ff; font-weight: bold' if x > 0 else 'color: #ff4b4b; font-weight: bold', subset=['คงเหลือสุทธิ']),
                use_container_width=True
            )
            st.divider()

        # สร้าง Tabs ย่อย 4 แบบตามที่ขอ
        sub1, sub2, sub3, sub4 = st.tabs(["📅 รายวัน", "🗓️ รายสัปดาห์", "📆 รายเดือน", "📅 รายปี"])
        
        with sub1: show_summary(df, 'Day', "รายวัน")
        with sub2: show_summary(df, 'Week', "รายสัปดาห์")
        with sub3: show_summary(df, 'Month', "รายเดือน")
        with sub4: show_summary(df, 'Year', "รายปี")
            
    else:
        st.info("ยังไม่มีข้อมูลเพียงพอสำหรับการวิเคราะห์")

# --- Tab 3: History ---
with tab3:
    st.header("ประวัติรายการทั้งหมด")
    if not df.empty:
        # แสดงข้อมูลดิบ (ไม่รวมคอลัมน์ที่สร้างมาคำนวณ)
        display_cols = ["Date", "Time", "Type", "Account", "Source", "Destination", "Channel", "Amount", "Note"]
        
        # ฟังก์ชันใส่สีบรรทัด (ตามที่เคยขอไว้)
        def highlight_rows(val):
            if val == 'รายรับ': return 'color: #28a745; font-weight: bold'
            elif val == 'รายจ่าย': return 'color: #dc3545; font-weight: bold'
            return ''

        st.dataframe(
            df[display_cols].sort_values(by='Date', ascending=False)
            .style.applymap(highlight_rows, subset=['Type'])
            .format({"Amount": "{:,.2f}"}),
            use_container_width=True
        )
    else:
        st.write("ยังไม่มีรายการบันทึก")