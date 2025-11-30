import streamlit as st
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
from matplotlib import gridspec
import io
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------
# 2. ฟังก์ชันโหลดข้อมูล (แบบ Direct CSV )
# ---------------------------------------------------------
@st.cache_data
def load_data():
    # ID ของ Google Sheet
    sheet_id = "1E12HO-5bd85vjFHnfcxZCLcN4y2k_uQnRgjE8zeGAbI"
    
    # URL พิเศษสำหรับการดึงข้อมูลเป็น CSV
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="

    # อ่านข้อมูลทีละแท็บโดยเอา Base URL + ชื่อแท็บ
    # ถ้าชื่อแท็บใน Google Sheet เป็นภาษาไทย หรือมีเว้นวรรค ให้เปลี่ยนเป็นภาษาอังกฤษตัวติดกัน (Majors, CoreCourses...)
    majors_df = pd.read_csv(base_url + "Majors")
    core_courses_df = pd.read_csv(base_url + "CoreCourses")
    gen_ed_df = pd.read_csv(base_url + "GenEd")
    electives_df = pd.read_csv(base_url + "Electives")
    
    return majors_df, core_courses_df, gen_ed_df, electives_df

majors_df, core_courses_df, gen_ed_df, electives_df = load_data()

# ---------------------------------------------------------
# 3. User Interface
# ---------------------------------------------------------
st.title("🎓 Credits Checker For DekPSU")

# --- Control Panel ด้านบน ---
col1, col2 = st.columns(2)

with col1:
    selected_major_name = st.selectbox("เลือกสาขาวิชา", majors_df['major_name'])
    total_credits = majors_df[majors_df['major_name'] == selected_major_name]['total_credits'].values[0]

with col2:
    # เลือกชั้นปีเพื่อใช้เป็น "ค่าเริ่มต้น" ในการติ๊กวิชาแกน
    year_options = ['ปี 1', 'ปี 2', 'ปี 3', 'ปี 4']
    selected_year_str = st.selectbox("คุณกำลังศึกษาอยู่ชั้นปีที่", year_options)
    # แปลง "ปี 1" -> 1 (int) เพื่อใช้คำนวณ
    current_year_num = int(selected_year_str.split(" ")[1])

# ตัวแปรเก็บหน่วยกิตรวมทั้งหมด
total_credits_earned = 0

# สร้าง Tabs (เพิ่ม Tab ปรับแต่งเพิ่มเติม เป็น Tab แรก)
tab_core, tab_gen, tab_elec, tab_free, tab_summary = st.tabs([
    "⚙️ ปรับแต่งวิชาแกน", 
    "📚 วิชาศึกษาทั่วไป", 
    "💻 วิชาเลือกสาขา", 
    "🎨 วิชาเลือกเสรี", 
    "📊 สรุปผล"
])

# ---------------------------------------------------------
# TAB 1: ปรับแต่งวิชาแกน (Core Courses Customization)
# ---------------------------------------------------------
with tab_core:
    st.info(f"ระบบเลือกวิชาแกนให้อัตโนมัติสำหรับ **{selected_year_str}** (คุณสามารถติ๊กออกได้หากยังไม่ผ่าน)")
    
    core_credits_sum = 0
    
    # 🔴 เพิ่มบรรทัดนี้: กรองเอาเฉพาะวิชาของสาขาที่เลือก (selected_major_name)
    # สมมติชื่อคอลัมน์ใน Sheet คือ 'major'
    major_core_courses = core_courses_df[core_courses_df['major'] == selected_major_name]
    
    # วนลูปสร้าง Section ตามชั้นปี 1-4
    for y in [1, 2, 3, 4]:
        # เปลี่ยนจาก core_courses_df เป็น major_core_courses (ที่กรองแล้ว)
        subjects_in_year = major_core_courses[major_core_courses['year'] == y]
        
        if not subjects_in_year.empty:
            with st.expander(f"วิชาแกน ปี {y}", expanded=(y <= current_year_num)):
                for idx, row in subjects_in_year.iterrows():
                    # Logic: ถ้าวิชาอยู่ปีต่ำกว่าหรือเท่ากับปีปัจจุบัน ให้ Default เป็น True (ติ๊กถูก)
                    is_default_checked = (y <= current_year_num)
                    
                    # Checkbox
                    checked = st.checkbox(
                        f"{row['subject_name']} ({row['credits']} นก.)",
                        value=is_default_checked,
                        key=f"core_{row['subject_name']}_{current_year_num}"
                    )
                    
                    if checked:
                        core_credits_sum += row['credits']
    
    st.write(f"**รวมหน่วยกิตวิชาแกนที่เก็บได้: :green[{core_credits_sum}] หน่วยกิต**")
    total_credits_earned += core_credits_sum

# ---------------------------------------------------------
# TAB 2: วิชาศึกษาทั่วไป
# ---------------------------------------------------------
with tab_gen:
    st.subheader("หมวดวิชาศึกษาทั่วไป")
    gen_credits_sum = 0
    categories = gen_ed_df['category'].unique()
    
    for cat in categories:
        with st.expander(f"หมวด: {cat}"):
            subjects = gen_ed_df[gen_ed_df['category'] == cat]
            for idx, row in subjects.iterrows():
                if st.checkbox(f"{row['subject_name']} ({row['credits']})", key=f"gen_{idx}"):
                    gen_credits_sum += row['credits']
                    
    total_credits_earned += gen_credits_sum

# ---------------------------------------------------------
# TAB 3: วิชาเลือกสาขา
# ---------------------------------------------------------
with tab_elec:
    st.subheader("วิชาเลือก")
    selected_maj_elec = st.multiselect("เลือกวิชา", electives_df['subject_name'], key="maj_elec")
    
    maj_elec_sum = 0
    for subj in selected_maj_elec:
        c = electives_df[electives_df['subject_name'] == subj]['credits'].values[0]
        maj_elec_sum += c
        
    st.write(f"เลือกไป: {maj_elec_sum} หน่วยกิต")
    total_credits_earned += maj_elec_sum

# ---------------------------------------------------------
# TAB 4: วิชาเลือกเสรี
# ---------------------------------------------------------
with tab_free:
    st.subheader("วิชาเลือกเสรี")
    selected_free_elec = st.multiselect("เลือกวิชา", electives_df['subject_name'], key="free_elec")
    
    free_elec_sum = 0
    for subj in selected_free_elec:
        c = electives_df[electives_df['subject_name'] == subj]['credits'].values[0]
        free_elec_sum += c
        
    st.write(f"เลือกไป: {free_elec_sum} หน่วยกิต")
    total_credits_earned += free_elec_sum

remaining = max(total_credits - total_credits_earned, 0)
progress = min(total_credits_earned / total_credits, 1.0)
percent = progress * 100

# ---------------------------------------------------------
# ส่วนแสดงผลคงที่ (Persistent Display)
# ---------------------------------------------------------

# 1. SIDEBAR: สำหรับ Desktop (แสดงด้านซ้าย)
with st.sidebar:
    st.header("📊 สถานะปัจจุบัน")
    
    # แสดง Progress Bar
    st.progress(progress, text=f"คืบหน้า {percent:.1f}%")
    
    # แสดง Metric ตัวใหญ่
    st.metric(
        label="หน่วยกิตสะสม",
        value=f"{total_credits_earned}/{total_credits}",
        delta=f"เหลืออีก {remaining}",
        delta_color="inverse" # สีแดงถ้ายังเหลือเยอะ
    )
    
    st.divider()
    
    # สรุปย่อๆ ใน Sidebar
    st.caption("รายละเอียด")
    st.markdown(f"""
    - **วิชาแกน:** {core_credits_sum}
    - **ศึกษาทั่วไป:** {gen_credits_sum}
    - **เลือกสาขา:** {maj_elec_sum}
    - **เลือกเสรี:** {free_elec_sum}
    """)

    # 🔴 เพิ่มปุ่มรีโหลดตรงนี้ครับ
    if st.button("🔄 อัปเดตข้อมูลล่าสุด"):
        load_data.clear()  # สั่งล้าง Cache ของฟังก์ชัน load_data
        st.rerun()         # สั่งรันหน้าเว็บใหม่ทันที

    
# ---------------------------------------------------------
# TAB 5: สรุปผล (Dashboard & Export Image)
# ---------------------------------------------------------
with tab_summary:
    st.header("📊 สรุปผลการเรียนและหน่วยกิต")
    
    # --- ส่วนแสดงผลบนหน้าเว็บ (Web UI) ---
    col_sum1, col_sum2, col_sum3 = st.columns(3)
    with col_sum1:
        st.metric("หน่วยกิตที่เก็บได้", f"{total_credits_earned}", f"{total_credits_earned - total_credits} ขาดอีก", delta_color="normal")
    with col_sum2:
        st.metric("เป้าหมายหลักสูตร", f"{total_credits}", "หน่วยกิต")
    with col_sum3:
        percent = (total_credits_earned / total_credits) * 100
        st.metric("ความคืบหน้า", f"{percent:.1f}%")

    st.divider()

    col_chart, col_detail = st.columns([1, 1.5])
    
    # เตรียมข้อมูลสำหรับกราฟ
    summary_labels = ['Core', 'GenEd', 'Major', 'Free', 'Missing'] # ใช้ภาษาอังกฤษเพื่อกันสระลอยในรูปภาพ (ถ้าไม่มี Font ไทย)
    summary_values = [core_credits_sum, gen_credits_sum, maj_elec_sum, free_elec_sum, remaining]
    # สี: ฟ้า(แกน), ส้ม(GenEd), แดง(สาขา), เขียว(เสรี), เทา(ขาด)
    colors_list = ['#4c78a8', '#f58518', '#e45756', '#72b7b2', '#bab0ac'] 

    # 1. กราฟวงกลมบนหน้าเว็บ (Altair)
    with col_chart:
        st.caption("สัดส่วนหน่วยกิตของคุณ")
        df_chart = pd.DataFrame({'Category': summary_labels, 'Credits': summary_values, 'Color': colors_list})
        base = alt.Chart(df_chart).encode(theta=alt.Theta("Credits", stack=True))
        pie = base.mark_arc(outerRadius=100, innerRadius=60).encode(
            color=alt.Color("Category", scale=alt.Scale(domain=summary_labels, range=colors_list)),
            order=alt.Order("Credits", sort="descending"),
            tooltip=["Category", "Credits"]
        )
        st.altair_chart(pie, use_container_width=True)

    # 2. บาร์ชาร์ตบนหน้าเว็บ
    with col_detail:
        st.subheader("รายละเอียดรายหมวด")
        def progress_row(label, current, target, color_hex):
            st.write(f"**{label}**")
            cols = st.columns([3, 1])
            p_val = min(current/target if target > 0 else 0, 1.0)
            cols[0].progress(p_val)
            cols[1].caption(f"{current}/{target}")
        
        progress_row("วิชาแกน", core_credits_sum, 80, "#4c78a8")
        progress_row("ศึกษาทั่วไป", gen_credits_sum, 30, "#f58518")
        progress_row("เลือกสาขา", maj_elec_sum, 6, "#e45756")
        progress_row("เลือกเสรี", free_elec_sum, 6, "#72b7b2")

    st.divider()

    # ---------------------------------------------------------
    # ส่วนสร้างรูปภาพ (Image Generator) เลียนแบบ UI
    # ---------------------------------------------------------
    st.subheader("💾 บันทึกผลการเรียน")
    
    if st.button("📸 สร้างรูปภาพสรุปผล (พร้อมลายน้ำ)"):
        # 1. ตั้งค่า Canvas
        fig = plt.figure(figsize=(10, 6)) # ขนาดภาพแนวนอน
        fig.patch.set_facecolor('white')
        
        # ใช้ GridSpec แบ่งพื้นที่: บน (Metrics), ล่างซ้าย (Pie), ล่างขวา (Bars)
        gs = gridspec.GridSpec(2, 2, height_ratios=[0.3, 0.7], width_ratios=[1, 1.5])
        
        # --- A. ส่วน Header (Metrics) ---
        ax_top = plt.subplot(gs[0, :])
        ax_top.axis('off')
        
        # วาด Text จำลอง Metric
        # (x, y) คือพิกัดในกล่องข้อความ
        ax_top.text(0.15, 0.6, "Credits Earned", ha='center', fontsize=10, color='gray')
        ax_top.text(0.15, 0.3, f"{total_credits_earned}", ha='center', fontsize=24, fontweight='bold', color='#333')
        
        ax_top.text(0.5, 0.6, "Target Goal", ha='center', fontsize=10, color='gray')
        ax_top.text(0.5, 0.3, f"{total_credits}", ha='center', fontsize=24, fontweight='bold', color='#333')
        
        ax_top.text(0.85, 0.6, "Progress", ha='center', fontsize=10, color='gray')
        ax_top.text(0.85, 0.3, f"{percent:.1f}%", ha='center', fontsize=24, fontweight='bold', color='#4c78a8')
        
        # --- B. ส่วน Donut Chart (ล่างซ้าย) ---
        ax_pie = plt.subplot(gs[1, 0])
        # ข้อมูลสำหรับ Pie (ตัดส่วน 'Missing' ออกเพื่อให้สวยงามเหมือน Donut ปกติ)
        # หรือจะใส่ Missing ไปด้วยก็ได้แล้วแต่ชอบครับ อันนี้ผมใส่ครบตาม mockup
        wedges, texts = ax_pie.pie(summary_values, colors=colors_list, startangle=90, 
                                   wedgeprops=dict(width=0.4, edgecolor='w')) # width=0.4 ทำให้เป็น Donut
        ax_pie.text(0, 0, f"{total_credits_earned}", ha='center', va='center', fontsize=20, fontweight='bold', color='#555')
        
        # --- C. ส่วน Bar Chart (ล่างขวา) ---
        ax_bar = plt.subplot(gs[1, 1])
        ax_bar.axis('off') # ปิดแกน x, y
        
        # รายการที่จะวาด Bar
        bar_items = [
            ("Core Courses", core_credits_sum, 80, colors_list[0]),
            ("GenEd", gen_credits_sum, 30, colors_list[1]),
            ("Major Elec", maj_elec_sum, 6, colors_list[2]),
            ("Free Elec", free_elec_sum, 6, colors_list[3])
        ]
        
        # วาด Bar ทีละแถว (Manual Drawing เพื่อความสวยงาม)
        y_pos = 3.5 # ตำแหน่งเริ่มต้น (ไล่จากบนลงล่าง)
        for label, val, target, color in bar_items:
            # ชื่อหมวด
            ax_bar.text(0, y_pos, label, fontsize=12, fontweight='bold', color='#333')
            
            # หลอดพื้นหลัง (สีเทาจางๆ)
            ax_bar.barh(y_pos - 0.3, 100, height=0.15, color='#f0f0f0', align='center', left=0)
            
            # หลอดความคืบหน้า (สีจริง) คำนวณ % เทียบกับ 100
            p = min((val / target) * 100 if target > 0 else 0, 100)
            ax_bar.barh(y_pos - 0.3, p, height=0.15, color=color, align='center', left=0)
            
            # ตัวเลข 27/80
            ax_bar.text(105, y_pos - 0.3, f"{val}/{target}", va='center', fontsize=10, color='#666')
            
            y_pos -= 1 # ขยับลงบรรทัดถัดไป

        # --- D. ใส่ลายน้ำ (Watermark) ---
        fig.text(0.5, 0.5, 'Credit Planner (Mockup)', 
                 fontsize=40, color='gray', alpha=0.1, # alpha คือความจาง
                 ha='center', va='center', rotation=30) # เอียง 30 องศา

        plt.tight_layout()
        
        # แปลงเป็นไฟล์ให้โหลด
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches='tight')
        buf.seek(0)
        
        col_dl1, col_dl2 = st.columns([1, 2])
        with col_dl1:
            st.download_button(
                label="⬇️ ดาวน์โหลดรูปภาพ",
                data=buf,
                file_name="credit_summary_watermark.png",
                mime="image/png"
            )
        with col_dl2:
            st.success("สร้างรูปภาพเสร็จสิ้น!")
        
        st.image(buf, caption="ตัวอย่างรูปภาพที่จะได้รับ", width=500)  