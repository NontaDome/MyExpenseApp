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

# โหลด Secrets
try:
    secrets = st.secrets["gcp_service_account"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(secrets, scopes=scopes)
    gc = gspread.authorize(creds)
    
    # URL ของ Google Sheets (*** อย่าลืมแก้ลิงก์ตรงนี้นะครับ ***)
    sheet_url = "https://docs.google.com/spreadsheets/d/1FbKe-hHVNi7Suo_XlP06qa8kcItPAoQzNNOFvsK38Ss/edit?gid=0#gid=0" 
    sh = gc.open_by_url(sheet_url)
    worksheet = sh.sheet1
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")
    st.stop()

# ฟังก์ชันสำหรับโหลดข้อมูล
def load_data():
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        # แปลงตัวเลข
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        # แปลงวันที่
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    return pd.DataFrame()

# -------------------------------------------------------
# 2. ส่วนหน้าจอแอป
# -------------------------------------------------------
st.title("💰 บันทึกรายรับ-รายจ่าย (Pro Version)")

tab1, tab2 = st.tabs(["📝 บันทึกข้อมูล", "📊 วิเคราะห์แดชบอร์ด"])

# ================= แท็บ 1: บันทึกข้อมูล =================
with tab1:
    with st.form("expense_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1: 
            date_input = st.date_input("วันที่", datetime.date.today())
        with c2: 
            # 🛠️ แก้ไขตรงนี้: เพิ่ม step=1 เพื่อให้เลือกเวลาได้ละเอียดระดับวินาที
            # และใช้ value=... เพื่อให้ Default เป็นเวลาปัจจุบันเสมอ
            time_input = st.time_input("เวลา", value=datetime.datetime.now().time(), step=1)
        with c3: 
            t_type = st.radio("ประเภท", ["รายจ่าย", "รายรับ"], horizontal=True)

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

# ================= แท็บ 2: แดชบอร์ด =================
with tab2:
    st.header("📈 สรุปผลการเงิน (รายวัน/สัปดาห์/เดือน/ปี)")
    df = load_data()

    if not df.empty:
        # เตรียมข้อมูลสำหรับ Grouping
        df['Year'] = df['Date'].dt.year
        df['Month'] = df['Date'].dt.strftime('%Y-%m (เดือน)')
        df['Week'] = df['Date'].dt.strftime('%Y-W%U (สัปดาห์)')
        df['Day'] = df['Date'].dt.strftime('%Y-%m-%d')

        # สร้างแท็บย่อย 4 อัน
        subtab1, subtab2, subtab3, subtab4 = st.tabs(["📅 รายวัน", "🗓️ รายสัปดาห์", "📆 รายเดือน", "📅 รายปี"])

        # ฟังก์ชันวาดกราฟและตาราง
        def show_summary(dataframe, group_col, title):
            # 1. จัดกลุ่มข้อมูล
            summary = dataframe.groupby([group_col, 'Type'])['Amount'].sum().reset_index()
            
            # 2. ทำ Pivot เพื่อหา Net Balance
            pivot_df = summary.pivot(index=group_col, columns='Type', values='Amount').fillna(0)
            if 'รายรับ' not in pivot_df.columns: pivot_df['รายรับ'] = 0
            if 'รายจ่าย' not in pivot_df.columns: pivot_df['รายจ่าย'] = 0
            pivot_df['คงเหลือสุทธิ'] = pivot_df['รายรับ'] - pivot_df['รายจ่าย']
            pivot_df = pivot_df.sort_index(ascending=False)

            # 3. แสดงกราฟแท่ง
            st.subheader(f"กราฟเปรียบเทียบ {title}")
            fig = px.bar(summary, x=group_col, y='Amount', color='Type', barmode='group',
                         color_discrete_map={'รายรับ':'#66BB6A', 'รายจ่าย':'#EF5350'})
            st.plotly_chart(fig, use_container_width=True)

            # 4. แสดงตารางสรุป
            st.subheader(f"ตารางสรุป {title}")
            display_df = pivot_df.copy()
            display_df = display_df.applymap(lambda x: f"{x:,.2f}")
            st.dataframe(display_df, use_container_width=True)

        # --- แสดงผลในแต่ละแท็บ ---
        with subtab1: show_summary(df, 'Day', "รายวัน")
        with subtab2: show_summary(df, 'Week', "รายสัปดาห์")
        with subtab3: show_summary(df, 'Month', "รายเดือน")
        with subtab4: show_summary(df, 'Year', "รายปี")
            
        st.divider()
        with st.expander("🔎 ดูข้อมูลดิบทั้งหมด"):
            st.dataframe(df.sort_values(by='Date', ascending=False), use_container_width=True)

    else:
        st.info("ยังไม่มีข้อมูลในระบบ")