import streamlit as st
import pandas as pd
import gspread
import datetime
import plotly.express as px
import os

# --- ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ระบบบัญชี Cloud", page_icon="💸", layout="wide")

# --- ฟังก์ชันเชื่อมต่อ Google Sheets (ฉบับใหม่ล่าสุด) ---
def get_worksheet():
    # วิธีใหม่: ใช้ gspread.service_account() โดยตรง ไม่ผ่าน oauth2client
    try:
        # 1. ลองหาไฟล์ credentials.json ในเครื่องก่อน
        if os.path.exists("credentials.json"):
            gc = gspread.service_account(filename="credentials.json")
        
        # 2. ถ้าไม่เจอ ให้ลองหาจาก Secrets (สำหรับ Cloud)
        elif "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            gc = gspread.service_account_from_dict(creds_dict)
            
        else:
            st.error("❌ ไม่พบไฟล์ credentials.json กรุณาเช็คว่าไฟล์อยู่ในโฟลเดอร์เดียวกับ app.py หรือไม่")
            st.stop()

        # เชื่อมต่อกับ Sheet
        # -------------------------------------------------------
        # เอาลิงก์ Google Sheets ของคุณ มาวางแทนที่ตรง xxxxx ด้านล่างนี้
        # อย่าลืมคงเครื่องหมายฟันหนู " " เอาไว้หัวท้ายนะครับ
        sheet_url = "https://docs.google.com/spreadsheets/d/1FbKe-hHVNi7Suo_XlP06qa8kcItPAoQzNNOFvsK38Ss/edit?gid=0#gid=0" 
        # -------------------------------------------------------
        
        return gc.open_by_url(sheet_url).sheet1
        
    except Exception as e:
        st.error(f"❌ เชื่อมต่อไม่ได้: {e}")
        st.info("💡 คำแนะนำ: ลองเช็คว่าชื่อไฟล์ Google Sheets คือ 'ExpenseData' หรือไม่ และแชร์ให้ Bot หรือยัง")
        st.stop()

# --- เริ่มดึงข้อมูล ---
sheet = get_worksheet()
try:
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
except Exception as e:
    # กรณี Sheet ว่างเปล่าหรือหัวตารางผิด
    st.warning("⚠️ ดึงข้อมูลไม่ได้ อาจเพราะตารางยังว่างเปล่า")
    df = pd.DataFrame(columns=["Date", "Time", "Type", "Account", "Channel", "Amount", "Note"])

# ================= ส่วนหน้าจอ (Frontend) =================

st.title("💸 ระบบบัญชีออนไลน์ (Sync Real-time)")

# --- 1. ส่วนกรอกข้อมูล (Sidebar) ---
st.sidebar.header("📝 เพิ่มรายการใหม่")
with st.sidebar.form("expense_form", clear_on_submit=True):
    date_val = st.date_input("วันที่", datetime.datetime.now())
    
    col_h, col_m = st.columns(2)
    now = datetime.datetime.now()
    with col_h: hour = st.number_input("ชั่วโมง", 0, 23, now.hour)
    with col_m: minute = st.number_input("นาที", 0, 59, now.minute)
    
    tx_type = st.radio("ประเภท", ["รายจ่าย", "รายรับ"], horizontal=True)
    account = st.selectbox("บัญชี", ["บัญชีใช้จ่าย", "เงินเก็บ", "บัตรเครดิต"])
    channel = st.selectbox("ช่องทาง", ["K PLUS", "SCB Easy", "Scan QR", "เงินสด", "บัตรเครดิต"])
    
    amount = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, format="%.2f")
    note = st.text_input("หมายเหตุ")
    
    submitted = st.form_submit_button("💾 บันทึกข้อมูล")
    
    if submitted:
        dt_str = date_val.strftime("%Y-%m-%d")
        tm_str = f"{hour:02}:{minute:02}:00"
        
        # ส่งข้อมูลเข้า Google Sheets
        try:
            sheet.append_row([dt_str, tm_str, tx_type, account, channel, amount, note])
            st.success("✅ บันทึกเสร็จสิ้น!")
            # หน่วงเวลาเล็กน้อยเพื่อให้ Google Update ทัน แล้วค่อยโหลดหน้าใหม่
            import time
            time.sleep(1) 
            st.rerun()
        except Exception as e:
            st.error(f"บันทึกไม่สำเร็จ: {e}")

# --- 2. ส่วนแสดงผล Dashboard ---
if not df.empty and 'Amount' in df.columns:
    # แปลงข้อมูลตัวเลขให้ถูกต้อง
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    
    inc = df[df['Type'] == 'รายรับ']['Amount'].sum()
    exp = df[df['Type'] == 'รายจ่าย']['Amount'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("รายรับรวม", f"{inc:,.2f} ฿", delta="รายรับ")
    c2.metric("รายจ่ายรวม", f"{exp:,.2f} ฿", delta="-รายจ่าย", delta_color="inverse")
    c3.metric("คงเหลือ", f"{inc - exp:,.2f} ฿")
    
    st.divider()
    
    col_chart1, col_chart2 = st.columns([2, 1])
    with col_chart1:
        st.subheader("📊 กราฟสรุปรายวัน")
        if not df.empty:
            daily = df.groupby(['Date', 'Type'])['Amount'].sum().reset_index()
            fig = px.bar(daily, x='Date', y='Amount', color='Type', 
                         color_discrete_map={'รายรับ':'#4CAF50', 'รายจ่าย':'#EF5350'}, barmode='group')
            st.plotly_chart(fig, use_container_width=True)
            
    with col_chart2:
        st.subheader("📋 รายการล่าสุด")
        st.dataframe(df.sort_index(ascending=False).head(10), use_container_width=True)

else:
    st.info("👋 ยินดีต้อนรับ! เริ่มต้นด้วยการเพิ่มรายการแรกที่เมนูซ้ายมือได้เลยครับ")