import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import plotly.express as px

# -------------------------------------------------------
# 1. เชื่อมต่อ Google Sheets
# -------------------------------------------------------
st.set_page_config(page_title="My Expense App", page_icon="💰", layout="wide")

try:
    secrets = st.secrets["gcp_service_account"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(secrets, scopes=scopes)
    gc = gspread.authorize(creds)
    
    # *** อย่าลืมแก้ลิงก์ Google Sheets ตรงนี้เหมือนเดิมนะครับ ***
    sheet_url = "https://docs.google.com/spreadsheets/d/1FbKe-hHVNi7Suo_XlP06qa8kcItPAoQzNNOFvsK38Ss/edit?gid=0#gid=0" 
    sh = gc.open_by_url(sheet_url)
    worksheet = sh.sheet1
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")
    st.stop()

# ฟังก์ชันโหลดข้อมูล
def load_data():
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    return pd.DataFrame()

# 🎨 ฟังก์ชันสำหรับใส่สีในตาราง (ข้อมูลดิบ)
def highlight_rows(val):
    if val == 'รายรับ':
        return 'color: #28a745; font-weight: bold' # เขียว
    elif val == 'รายจ่าย':
        return 'color: #dc3545; font-weight: bold' # แดง
    elif val == 'บัญชีออมทรัพย์':
        return 'color: #00d4ff; font-weight: bold' # ฟ้าสว่าง (แก้จากน้ำเงิน)
    elif val == 'บัญชีเงินฝากดอกเบี้ยสูง':
        return 'color: #fd7e14; font-weight: bold' # ส้ม
    return ''

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