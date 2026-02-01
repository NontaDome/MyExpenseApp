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
secrets = st.secrets["gcp_service_account"]
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(secrets, scopes=scopes)
gc = gspread.authorize(creds)

# URL ของ Google Sheets (ใช้ลิงก์เดิมของคุณได้เลย)
sheet_url = "https://docs.google.com/spreadsheets/d/xxxxxxxxxxxxxxxxxxxx/edit" 
# *** อย่าลืมเอาลิงก์ Google Sheets ของคุณมาใส่แทน xxxxx ด้านบน ***

try:
    sh = gc.open_by_url(sheet_url)
    worksheet = sh.sheet1
except Exception as e:
    st.error(f"เชื่อมต่อ Google Sheets ไม่ได้: {e}")
    st.stop()

# -------------------------------------------------------
# 2. ส่วนหน้าจอแอป
# -------------------------------------------------------
st.title("💰 บันทึกรายรับ-รายจ่าย (ฉบับสมบูรณ์)")

tab1, tab2 = st.tabs(["📝 บันทึกข้อมูล", "📊 วิเคราะห์แดชบอร์ด"])

# ================= แท็บ 1: บันทึกข้อมูล =================
with tab1:
    with st.form("expense_form", clear_on_submit=True):
        # แถวที่ 1
        c1, c2, c3 = st.columns(3)
        with c1: date_input = st.date_input("วันที่", datetime.date.today())
        with c2: time_input = st.time_input("เวลา", datetime.datetime.now().time())
        with c3: t_type = st.radio("ประเภท", ["รายจ่าย", "รายรับ"], horizontal=True)

        # แถวที่ 2
        c4, c5 = st.columns(2)
        with c4: 
            # ปรับชื่อบัญชีตามที่คุณต้องการ
            account = st.selectbox("บัญชีที่เกี่ยวข้อง", 
                                   ["บัญชีออมทรัพย์", "บัญชีเงินฝากดอกเบี้ยสูง", "เงินสด", "บัตรเครดิต", "อื่นๆ"])
        with c5: 
            amount = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, step=1.0)

        # แถวที่ 3 (เพิ่มใหม่: ต้นทาง/ปลายทาง)
        c6, c7 = st.columns(2)
        with c6: source = st.text_input("ต้นทาง (From)", placeholder="เช่น ชื่อคนโอน, ธนาคารต้นทาง")
        with c7: destination = st.text_input("ปลายทาง (To)", placeholder="เช่น ชื่อคนรับ, ร้านค้า")

        # แถวที่ 4
        c8, c9 = st.columns(2)
        with c8: channel = st.selectbox("ช่องทาง", ["App ธนาคาร", "เงินสด", "Scan QR", "บัตรเครดิต"])
        with c9: note = st.text_input("หมายเหตุ", placeholder="รายละเอียดเพิ่มเติม")
        
        submitted = st.form_submit_button("บันทึกข้อมูล ✅", use_container_width=True)

        if submitted:
            date_str = date_input.strftime("%Y-%m-%d")
            time_str = time_input.strftime("%H:%M:%S")
            
            # เรียงข้อมูลให้ตรงกับหัวตารางใน Google Sheets
            # Date, Time, Type, Account, Source, Destination, Channel, Amount, Note
            row_data = [date_str, time_str, t_type, account, source, destination, channel, amount, note]
            
            worksheet.append_row(row_data)
            st.success("บันทึกข้อมูลสำเร็จ!")
            st.cache_data.clear()

    # แสดงประวัติล่าสุด
    st.divider()
    st.subheader("📋 ประวัติล่าสุด")
    try:
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            # แสดงเฉพาะคอลัมน์ที่สำคัญ
            st.dataframe(df.tail(5).sort_index(ascending=False), use_container_width=True)
    except:
        st.info("ยังไม่มีข้อมูล")

# ================= แท็บ 2: แดชบอร์ด =================
with tab2:
    st.header("ภาพรวมการเงิน")
    try:
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
            
            # สรุปยอด
            inc = df[df['Type'] == 'รายรับ']['Amount'].sum()
            exp = df[df['Type'] == 'รายจ่าย']['Amount'].sum()
            
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("รายรับ", f"{inc:,.2f} ฿")
            kpi2.metric("รายจ่าย", f"{exp:,.2f} ฿")
            kpi3.metric("คงเหลือ", f"{inc - exp:,.2f} ฿")
            
            st.divider()
            
            # กราฟวงกลม
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader("สัดส่วน รายรับ-รายจ่าย")
                fig1 = px.pie(df, names='Type', values='Amount', color='Type', 
                              color_discrete_map={'รายรับ':'#66BB6A', 'รายจ่าย':'#EF5350'})
                st.plotly_chart(fig1, use_container_width=True)
                
            with col_g2:
                st.subheader("แยกตามบัญชี")
                fig2 = px.bar(df, x='Account', y='Amount', color='Type', barmode='group')
                st.plotly_chart(fig2, use_container_width=True)

            # ตารางค้นหาละเอียด
            with st.expander("ดูข้อมูลแบบละเอียด (ค้นหาได้)"):
                st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.info(f"รอข้อมูล... (ถ้าเพิ่งแก้หัวตาราง ให้ลองกด Refresh หน้าเว็บ 1 ทีครับ)")