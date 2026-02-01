import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
import plotly.express as px  # เรียกใช้ไลบรารีกราฟ

# -------------------------------------------------------
# 1. เชื่อมต่อ Google Sheets
# -------------------------------------------------------
st.set_page_config(page_title="My Expense App", page_icon="💰")

# โหลด Secrets จาก Streamlit Cloud
secrets = st.secrets["gcp_service_account"]

# สร้าง Credentials
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(secrets, scopes=scopes)
gc = gspread.authorize(creds)

# เปิดไฟล์ Google Sheets (แก้ตรงนี้ให้เป็นลิงก์ของคุณถ้าจำเป็น)
sheet_url = "https://docs.google.com/spreadsheets/d/1FbKe-hHVNi7Suo_XlP06qa8kcItPAoQzNNOFvsK38Ss/edit?gid=0#gid=0" 
# *** อย่าลืมเอาลิงก์ Google Sheets ของคุณมาใส่แทน xxxxx ด้านบนนะครับ ***

try:
    sh = gc.open_by_url(sheet_url)
    worksheet = sh.sheet1
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ Google Sheets: {e}")
    st.stop()

# -------------------------------------------------------
# 2. ส่วนหัวของแอป
# -------------------------------------------------------
st.title("💰 บันทึกรายรับ-รายจ่าย")

# สร้างแท็บ 2 หน้า
tab1, tab2 = st.tabs(["📝 บันทึกข้อมูล", "📊 วิเคราะห์แดชบอร์ด"])

# =======================================================
# แท็บที่ 1: หน้าบันทึกข้อมูล (CODE เดิม)
# =======================================================
with tab1:
    with st.form("expense_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date_input = st.date_input("วันที่", datetime.date.today())
            t_type = st.radio("ประเภท", ["รายจ่าย", "รายรับ"], horizontal=True)
            account = st.selectbox("บัญชี/กระเป๋า", ["เงินสด", "K-Bank", "SCB", "TrueWallet", "เงินเก็บ"])
        
        with col2:
            time_input = st.time_input("เวลา", datetime.datetime.now().time())
            amount = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, step=1.0)
            channel = st.selectbox("ช่องทาง", ["เงินสด", "App ธนาคาร", "บัตรเครดิต", "QR Code"])
        
        note = st.text_input("หมายเหตุ (เช่น ค่าข้าว, ค่ารถ)")
        
        submitted = st.form_submit_button("บันทึกข้อมูล ✅")

        if submitted:
            # เตรียมข้อมูล
            date_str = date_input.strftime("%Y-%m-%d")
            time_str = time_input.strftime("%H:%M:%S")
            row_data = [date_str, time_str, t_type, account, channel, amount, note]
            
            # บันทึกลง Sheets
            worksheet.append_row(row_data)
            st.success("บันทึกข้อมูลเรียบร้อยแล้ว!")
            st.cache_data.clear() # ล้าง Cache เพื่อให้ข้อมูลอัปเดตทันที

    # แสดงประวัติล่าสุด 5 รายการ
    st.subheader("📋 ประวัติล่าสุด")
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df.tail(5).sort_index(ascending=False), use_container_width=True)

# =======================================================
# แท็บที่ 2: หน้าวิเคราะห์ข้อมูล (ส่วนที่เพิ่มใหม่)
# =======================================================
with tab2:
    st.header("ภาพรวมการเงินของคุณ")
    
    # ดึงข้อมูลมาคำนวณ
    data = worksheet.get_all_records()
    
    if data:
        df = pd.DataFrame(data)
        
        # แปลงข้อมูลตัวเลขและวันที่ให้คำนวณได้
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['Date'] = pd.to_datetime(df['Date'])
        
        # 1. การ์ดสรุปยอดเงิน (KPI)
        total_income = df[df['Type'] == 'รายรับ']['Amount'].sum()
        total_expense = df[df['Type'] == 'รายจ่าย']['Amount'].sum()
        balance = total_income - total_expense
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("รายรับรวม", f"{total_income:,.2f} ฿", delta_color="normal")
        col_b.metric("รายจ่ายรวม", f"{total_expense:,.2f} ฿", delta_color="inverse")
        col_c.metric("คงเหลือสุทธิ", f"{balance:,.2f} ฿")
        
        st.divider() # เส้นขีดคั่น

        # 2. กราฟวงกลม: สัดส่วน รายรับ vs รายจ่าย
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("สัดส่วน รายรับ vs รายจ่าย")
            fig_pie = px.pie(df, names='Type', values='Amount', color='Type',
                             color_discrete_map={'รายรับ':'#4CAF50', 'รายจ่าย':'#FF5252'})
            st.plotly_chart(fig_pie, use_container_width=True)

        # 3. กราฟแท่ง: รายจ่ายแยกตามบัญชี (ดูว่าเงินไหลออกจากไหนเยอะสุด)
        with col_chart2:
            st.subheader("รายจ่ายแยกตามบัญชี")
            expense_df = df[df['Type'] == 'รายจ่าย']
            if not expense_df.empty:
                fig_bar = px.bar(expense_df, x='Account', y='Amount', color='Account',
                                 title="ใช้เงินจากบัญชีไหนเยอะสุด?")
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลรายจ่าย")

        # 4. กราฟเส้น: แนวโน้มการใช้เงินรายวัน
        st.subheader("📅 แนวโน้มการใช้จ่าย (Timeline)")
        # รวมยอดเงินตามวันและประเภท
        daily_df = df.groupby(['Date', 'Type'])['Amount'].sum().reset_index()
        fig_line = px.line(daily_df, x='Date', y='Amount', color='Type', 
                           markers=True, title="รายรับ-รายจ่าย ในแต่ละวัน")
        st.plotly_chart(fig_line, use_container_width=True)
        
        # 5. ตารางข้อมูลทั้งหมด (ค้นหาได้)
        with st.expander("🔎 ดูข้อมูลทั้งหมดแบบละเอียด"):
            st.dataframe(df.sort_values(by='Date', ascending=False), use_container_width=True)

    else:
        st.info("ยังไม่มีข้อมูลในระบบ ให้เริ่มบันทึกที่แท็บแรกก่อนนะครับ")