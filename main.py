import streamlit as st
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
from matplotlib import gridspec
import io

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Credits Checker For DekPSU", page_icon="🎓", layout="wide")

# ---------------------------------------------------------
# 1. ฟังก์ชันโหลดข้อมูล
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def load_data():
    # ⚠️ ใส่ ID ของ Google Sheet ของคุณที่นี่
    sheet_id = "1E12HO-5bd85vjFHnfcxZCLcN4y2k_uQnRgjE8zeGAbI"
    
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="

    try:
        df_faculty = pd.read_csv(base_url + "Faculty")
        df_majors = pd.read_csv(base_url + "Majors")
        df_core = pd.read_csv(base_url + "Core")
        df_7group = pd.read_csv(base_url + "7group")
        df_elec = pd.read_csv(base_url + "Elective")
        df_free = pd.read_csv(base_url + "FreeElective")

        # Data Cleaning
        if 'is_major_elective' in df_core.columns:
            df_core['is_major_elective'] = df_core['is_major_elective'].astype(str).str.upper() == 'TRUE'
        else:
            df_core['is_major_elective'] = False

        for df in [df_majors, df_core, df_7group, df_elec, df_free]:
            if 'credits' in df.columns:
                df['credits'] = pd.to_numeric(df['credits'], errors='coerce').fillna(0)
        
        df_core['term'] = pd.to_numeric(df_core['term'], errors='coerce').fillna(0)

        return df_faculty, df_majors, df_core, df_7group, df_elec, df_free

    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_faculty, df_majors, df_core, df_7group, df_elec, df_free = load_data()

if df_faculty.empty:
    st.stop()

# ---------------------------------------------------------
# 2. UI Control Panel
# ---------------------------------------------------------
st.title("🎓 Credits Checker For DekPSU")
st.markdown("---")

col1, col2, col3 = st.columns([1, 2, 2])

# Col 1: ปี/เทอม
with col1:
    term_options = [1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2]
    selected_term = st.selectbox(
        "📅 ชั้นปีและเทอมปัจจุบัน", 
        term_options, 
        format_func=lambda x: f"ปี {int(x)} เทอม {int((x*10)%10)}"
    )

# Col 2: คณะ
with col2:
    if 'faculty_name' in df_faculty.columns:
        fac_options = df_faculty.apply(lambda x: f"{x['faculty_name']} ({x['major_count']} สาขา)", axis=1).tolist()
        selected_fac_display = st.selectbox("🏢 เลือกคณะ", fac_options)
        selected_fac_name = selected_fac_display.split(" (")[0]
    else:
        st.error("Data Error")
        st.stop()

# Col 3: สาขา
with col3:
    filtered_majors = df_majors[df_majors['faculty_ref'] == selected_fac_name]
    if filtered_majors.empty:
        st.warning("ไม่พบสาขา")
        st.stop()
    selected_major_name = st.selectbox("📚 เลือกสาขาวิชา", filtered_majors['major_name'])
    total_credits_goal = filtered_majors[filtered_majors['major_name'] == selected_major_name]['total_credits'].values[0]

# ---------------------------------------------------------
# 3. เตรียมข้อมูล
# ---------------------------------------------------------
all_major_courses = df_core[df_core['major_ref'] == selected_major_name]

# แยกกลุ่ม 1: วิชาแกน (False)
core_subjects = all_major_courses[all_major_courses['is_major_elective'] == False]
# แยกกลุ่ม 2: วิชาเลือกสาขา (True จาก Sheet Core)
major_electives_plan = all_major_courses[all_major_courses['is_major_elective'] == True]

total_earned = 0
earned_core = 0
earned_maj_plan = 0
earned_maj_pool = 0
earned_gen = 0
earned_free = 0

# ---------------------------------------------------------
# 4. Tabs Management (5 Tabs + Summary)
# ---------------------------------------------------------
tab_names = [
    "⚙️ 1. วิชาแกน", 
    "⚡ 2. วิชาเลือก (ตามแผน)", 
    "💻 3. วิชาเลือก (เพิ่มเติม)", 
    "📚 4. ศึกษาทั่วไป", 
    "🎨 5. เลือกเสรี", 
    "📊 สรุปผล"
]
tabs = st.tabs(tab_names)

# --- TAB 1: วิชาแกน (Core) ---
with tabs[0]:
    st.info(f"ระบบเลือกวิชาให้อัตโนมัติถึง **ปี {int(selected_term)} เทอม {int((selected_term*10)%10)}**")
    
    unique_terms = sorted(core_subjects['term'].unique())
    for t in unique_terms:
        # Auto Expand
        is_expanded = (t <= selected_term)
        t_label = f"ปี {int(t)} เทอม {int((t*10)%10)}"
        
        with st.expander(f"📍 {t_label}", expanded=is_expanded):
            subs = core_subjects[core_subjects['term'] == t]
            for idx, row in subs.iterrows():
                # Logic Auto Check
                is_checked = (t <= selected_term)
                # ใส่ selected_term ใน Key เพื่อบังคับ Reset ปุ่ม
                key_id = f"core_{row['subject_name']}_{idx}_{selected_term}"
                
                if st.checkbox(f"{row['subject_name']} ({row['credits']} นก.)", value=is_checked, key=key_id):
                    earned_core += row['credits']
    
    total_earned += earned_core
    st.write(f"**รวมวิชาแกน:** :green[{earned_core}]")

# --- TAB 2: วิชาเลือกสาขา (จาก Sheet Core เท่านั้น) ---
with tabs[1]:
    st.subheader("วิชาเลือกเฉพาะสาขา (ที่ระบุในแผนการเรียน)")
    
    if not major_electives_plan.empty:
        for idx, row in major_electives_plan.iterrows():
            # Checkbox ธรรมดา (User เลือกเอง)
            key_id = f"me_plan_{idx}"
            if st.checkbox(f"{row['subject_name']} ({row['credits']} นก.)", key=key_id):
                earned_maj_plan += row['credits']
    else:
        st.info("ไม่มีรายวิชาเลือกที่ระบุในแผนการเรียนสำหรับสาขานี้")
        
    total_earned += earned_maj_plan
    st.write(f"**รวมส่วนนี้:** :green[{earned_maj_plan}]")

# --- TAB 3: วิชาเลือกสาขา (จาก Sheet Elective Pool) ---
with tabs[2]:
    st.subheader("วิชาเลือกสาขา (เลือกเพิ่มเติมจาก Pool)")
    
    # Multiselect จาก Sheet Elective
    selected_pool = st.multiselect(
        "ค้นหาและเลือกรายวิชา", 
        df_elec['subject_name'], 
        key="me_pool_tab3"
    )
    
    for subj in selected_pool:
        c = df_elec[df_elec['subject_name'] == subj]['credits'].values[0]
        earned_maj_pool += c
    
    total_earned += earned_maj_pool
    st.write(f"**รวมส่วนนี้:** :green[{earned_maj_pool}]")

# --- TAB 4: ศึกษาทั่วไป ---
with tabs[3]:
    st.caption("หมวดวิชาศึกษาทั่วไป")
    cats = df_7group['category'].unique()
    for cat in cats:
        with st.expander(cat, expanded=False):
            subs = df_7group[df_7group['category'] == cat]
            for idx, row in subs.iterrows():
                if st.checkbox(f"{row['subject_name']} ({row['credits']})", key=f"gen_{idx}"):
                    earned_gen += row['credits']
    total_earned += earned_gen

# --- TAB 5: เลือกเสรี ---
with tabs[4]:
    st.caption("วิชาเลือกเสรี")
    sel_free = st.multiselect("เลือกวิชาเสรี", df_free['subject_name'], key="free_sel")
    for subj in sel_free:
        c = df_free[df_free['subject_name'] == subj]['credits'].values[0]
        earned_free += c
    total_earned += earned_free

# --- TAB 6: สรุปผล ---
with tabs[5]:
    remaining = max(total_credits_goal - total_earned, 0)
    percent = (total_earned / total_credits_goal) * 100
    if percent > 100: percent = 100

    # UI สรุป
    st.header("📊 สรุปผลการเรียน")
    m1, m2, m3 = st.columns(3)
    m1.metric("หน่วยกิตสะสม", f"{total_earned}", f"ขาดอีก {remaining}", delta_color="normal")
    m2.metric("เป้าหมาย", f"{total_credits_goal}")
    m3.metric("ความคืบหน้า", f"{percent:.1f}%")
    st.progress(percent/100)

    # รวมหน่วยกิตวิชาเลือกทั้ง 2 Tab เข้าด้วยกันเพื่อแสดงในกราฟ
    total_major_elec = earned_maj_plan + earned_maj_pool

    # Graph
    col_chart, col_detail = st.columns([1, 1.5])
    labels = ['Core', 'MajorElec', 'GenEd', 'FreeElec', 'Missing']
    values = [earned_core, total_major_elec, earned_gen, earned_free, remaining]
    colors = ['#4c78a8', '#e45756', '#f58518', '#72b7b2', '#bab0ac']

    with col_chart:
        df_pie = pd.DataFrame({'Category': labels, 'Val': values, 'Color': colors})
        pie = alt.Chart(df_pie).encode(theta=alt.Theta("Val", stack=True)).mark_arc(outerRadius=100, innerRadius=60).encode(
            color=alt.Color("Category", scale=alt.Scale(domain=labels, range=colors)),
            tooltip=["Category", "Val"]
        )
        st.altair_chart(pie, use_container_width=True)

    with col_detail:
        st.write("**รายละเอียด:**")
        st.write(f"- ⚙️ Core: {earned_core}")
        st.write(f"- ⚡ Major Elec (แผน): {earned_maj_plan}")
        st.write(f"- 💻 Major Elec (Pool): {earned_maj_pool}")
        st.write(f"- 📚 GenEd: {earned_gen}")
        st.write(f"- 🎨 Free Elec: {earned_free}")

    # Image Generator
    st.divider()
    if st.button("📸 สร้างรูปภาพสรุปผล"):
        fig = plt.figure(figsize=(10, 6))
        fig.patch.set_facecolor('white')
        gs = gridspec.GridSpec(2, 2, height_ratios=[0.3, 0.7], width_ratios=[1, 1.5])

        ax_top = plt.subplot(gs[0, :])
        ax_top.axis('off')
        ax_top.text(0.15, 0.5, "Earned", ha='center', color='gray')
        ax_top.text(0.15, 0.1, f"{total_earned}", ha='center', fontsize=22, fontweight='bold')
        ax_top.text(0.5, 0.5, "Goal", ha='center', color='gray')
        ax_top.text(0.5, 0.1, f"{total_credits_goal}", ha='center', fontsize=22, fontweight='bold')
        ax_top.text(0.85, 0.5, "Progress", ha='center', color='gray')
        ax_top.text(0.85, 0.1, f"{percent:.1f}%", ha='center', fontsize=22, fontweight='bold', color='#4c78a8')

        ax_pie = plt.subplot(gs[1, 0])
        ax_pie.pie(values, colors=colors, startangle=90, wedgeprops=dict(width=0.4, edgecolor='w'))
        ax_pie.text(0, 0, f"{int(percent)}%", ha='center', va='center', fontsize=16, fontweight='bold', color='#555')

        ax_bar = plt.subplot(gs[1, 1])
        ax_bar.axis('off')
        y_pos = 3.5
        items = [("Core", earned_core, colors[0]), 
                 ("Major", total_major_elec, colors[1]),
                 ("GenEd", earned_gen, colors[2]), 
                 ("Free", earned_free, colors[3])]
        
        for lb, val, c in items:
            ax_bar.text(0, y_pos, lb, fontweight='bold', color='#333')
            ax_bar.barh(y_pos-0.3, 100, height=0.15, color='#f0f0f0', left=0)
            p_bar = min((val/30)*100, 100) 
            ax_bar.barh(y_pos-0.3, p_bar, height=0.15, color=c, left=0)
            ax_bar.text(105, y_pos-0.3, f"{val}", va='center', color='#666')
            y_pos -= 1
        
        fig.text(0.5, 0.5, 'DekPSU Planner', fontsize=40, color='gray', alpha=0.1, ha='center', va='center', rotation=30)
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches='tight')
        buf.seek(0)
        st.download_button("⬇️ Download Image", buf, "summary.png", "image/png")

# Sidebar
with st.sidebar:
    st.header(f"สถานะ: {selected_fac_name}")
    st.write(f"สาขา: {selected_major_name}")
    st.progress(percent/100, f"{percent:.1f}%")
    if st.button("🔄 Reload Data"):
        load_data.clear()
        st.rerun()