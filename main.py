import streamlit as st
import pandas as pd
import altair as alt

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Credits Checker For DekPSU", page_icon="🎓", layout="wide")

# ==========================================
# [NEW] First Time Tutorial Popup
# ==========================================
@st.dialog("ยินดีต้อนรับสู่ Credits Checker! 🎓")
def show_tutorial():
    st.write("ระบบช่วยตรวจสอบและวางแผนการเรียนสำหรับเด็ก ม.อ.")
    
    # ใช้ Tabs ใน Popup เพื่อแบ่งหัวข้อสอน
    tab1, tab2, tab3 = st.tabs(["1️⃣ ตั้งค่าข้อมูล", "2️⃣ เลือกวิชา", "3️⃣ ดูผลลัพธ์"])
    
    with tab1:
        st.info("ขั้นตอนแรก: เลือกข้อมูลส่วนตัวที่แถบด้านบน")
        st.markdown("""
        * 📅 **ปี/เทอม:** เลือกชั้นปีปัจจุบันของคุณ
        * 🏢 **คณะ/สาขา:** เลือกสาขาวิชาที่คุณเรียน
        * ระบบจะดึงหลักสูตรที่ตรงกับสาขามาให้ทันที
        """)
        # ใส่รูปภาพประกอบได้ (ถ้ามี)
        # st.image("https://example.com/step1.gif")

    with tab2:
        st.info("ขั้นตอนที่สอง: ติ๊กรายวิชาที่เรียนแล้ว")
        st.markdown("""
        * **Tab วิชาแกน:** ระบบจะ Auto-check วิชาตามชั้นปีให้ (แก้ได้)
        * **Tab อื่นๆ:** เลือกวิชาเลือก, สหกิจ, หรือวิชาเสรีที่เรียนไปแล้ว
        * ถ้าวิชามีกลุ่มย่อย สามารถกดขยายดูได้
        """)

    with tab3:
        st.info("ขั้นตอนสุดท้าย: ตรวจสอบหน่วยกิต")
        st.markdown("""
        * ดูสรุปหน่วยกิตคงเหลือที่ **Sidebar ด้านซ้าย**
        * กดปุ่ม **🖼️ Image** เพื่อโหลดรูปสรุปผลไปอวดเพื่อนได้เลย!
        """)

    if st.button("เริ่มใช้งานเลย! 🚀", type="primary", use_container_width=True):
        st.session_state["has_seen_tutorial"] = True
        st.rerun()

if "has_seen_tutorial" not in st.session_state:
    show_tutorial()

# ==========================================
# 1. Helper Functions
# ==========================================

def format_subject_label(row):
    return f"**{row['subject_id']} {row['subject_name_en']}** \n:gray[{row['subject_name_th']} | {int(row['credits'])} หน่วยกิต]"
def format_subject_label_for_multiple(row):
    return f"{row['subject_id']} {row['subject_name_en']} | {row['subject_name_th']} ({int(row['credits'])} หน่วยกิต)"

def check_major_match(major_ref_str, target_abbr):
    if pd.isna(major_ref_str): return False
    majors_list = [m.strip().upper() for m in str(major_ref_str).split(',')]
    return target_abbr.upper() in majors_list

def render_grouped_checkoxes(df_subjects, key_prefix, earned_counter_list, selected_subjects_data):
    """
    df_subjects: DataFrame ของวิชาที่จะแสดง
    key_prefix: ตัวหน้านำหน้า key (เช่น 'me_plan', 'pool')
    earned_counter_list: list ที่เก็บ [earned_credits] (ใช้ list เพื่อ pass by reference)
    selected_subjects_data: list เก็บข้อมูลวิชาที่เลือก
    """
    # -------------------------------------------------------
    # 🔴 ป้องกัน KeyError: ถ้าไม่มี column 'group' ให้สร้างหลอกๆ ขึ้นมา
    if 'group' not in df_subjects.columns:
        df_subjects = df_subjects.copy() # ป้องกัน SettingWithCopyWarning
        df_subjects['group'] = ''
    # -------------------------------------------------------
    
    # 1. แยกวิชาที่มีกลุ่ม และไม่มีกลุ่ม
    # ใช้ .copy() เพื่อป้องกัน Warning เวลา modify dataframe slice
    df_subjects = df_subjects.copy()
    df_subjects['group_str'] = df_subjects['group'].fillna('').astype(str)
    
    # แปลง 'nan' string ให้เป็น empty string (เผื่อหลุดมา)
    df_subjects.loc[df_subjects['group_str'] == 'nan', 'group_str'] = ''
    
    df_no_group = df_subjects[df_subjects['group_str'] == '']
    df_has_group = df_subjects[df_subjects['group_str'] != '']

    # 2. แสดงวิชาที่ไม่มีกลุ่มก่อน (ถ้ามี)
    if not df_no_group.empty:
        for idx, row in df_no_group.iterrows():
            key_id = f"{key_prefix}_{row['subject_id']}_{idx}_nogroup"
            if st.checkbox(format_subject_label(row), key=key_id):
                earned_counter_list[0] += row['credits']
                selected_subjects_data.append(row.to_dict())

    # 3. จัดการวิชาที่มีกลุ่ม
    if not df_has_group.empty:
        # เรียงลำดับตามชื่อกลุ่ม
        unique_groups = sorted(df_has_group['group_str'].unique())

        for group_name in unique_groups:
            subs_in_group = df_has_group[df_has_group['group_str'] == group_name]
            
            # Logic การแสดงผล Header vs Expander
            # ถ้าชื่อกลุ่มไม่มีจุด (.) เช่น "1 กลุ่มภาษา" -> Header
            # ถ้ามีจุด (.) เช่น "1.1 ภาษาอังกฤษ" -> Expander
            is_main_group = '.' not in group_name.split(' ')[0]
            
            if is_main_group:
                st.markdown(f"##### 📂 {group_name}")
                for idx, row in subs_in_group.iterrows():
                    key_id = f"{key_prefix}_{row['subject_id']}_{idx}_main_{group_name}"
                    if st.checkbox(format_subject_label(row), key=key_id):
                        earned_counter_list[0] += row['credits']
                        selected_subjects_data.append(row.to_dict())
            else:
                with st.expander(f"🔹 {group_name}", expanded=False):
                    for idx, row in subs_in_group.iterrows():
                        key_id = f"{key_prefix}_{row['subject_id']}_{idx}_sub_{group_name}"
                        if st.checkbox(format_subject_label(row), key=key_id):
                            earned_counter_list[0] += row['credits']
                            selected_subjects_data.append(row.to_dict())

# ---------------------------------------------------------
# 2. Load Data (Updated for 'group' column)
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def load_data():
    try:
        sheet_id = st.secrets["google_sheets"]["sheet_id"]
    except Exception:
        st.error("❌ ไม่พบ Sheet ID ใน .streamlit/secrets.toml")
        st.stop()
    
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="

    try:
        df_faculty = pd.read_csv(base_url + "Faculty")
        df_majors = pd.read_csv(base_url + "Majors")
        df_core = pd.read_csv(base_url + "Core")
        df_7group = pd.read_csv(base_url + "7group")
        df_elec = pd.read_csv(base_url + "Elective")
        df_free = pd.read_csv(base_url + "FreeElective")

        for df in [df_core]:
             df['subject_id'] = df['subject_id'].astype(str).str.strip()
             df['subject_name_th'] = df['subject_name_th'].astype(str).str.strip()
             df['subject_name_en'] = df['subject_name_en'].astype(str).str.strip()
             
             # [NEW] Handle 'group' column
             if 'group' in df.columns:
                 # แปลงเป็น string และจัดการ NaN
                 df['group'] = df['group'].astype(str).replace('nan', '')
             else:
                 df['group'] = '' # ถ้าไม่มี column นี้ ให้สร้างเป็นว่างๆ ไว้

        if 'major_abbreviation' in df_majors.columns:
            df_majors['major_abbreviation'] = df_majors['major_abbreviation'].astype(str).str.strip()
        else:
            df_majors['major_abbreviation'] = df_majors['major_name']

        if 'special_type' in df_core.columns:
            df_core['special_type'] = df_core['special_type'].astype(str).str.strip()
        else:
            df_core['special_type'] = 'Normal Subject'

        for df in [df_majors, df_core, df_7group, df_elec, df_free]:
            if 'credits' in df.columns:
                df['credits'] = pd.to_numeric(df['credits'], errors='coerce').fillna(0)
        
        df_core['term'] = pd.to_numeric(df_core['term'], errors='coerce').fillna(0)
        
        df_elec['display_label'] = df_elec.apply(format_subject_label_for_multiple, axis=1)
        df_free['display_label'] = df_free.apply(format_subject_label_for_multiple, axis=1)

        return df_faculty, df_majors, df_core, df_7group, df_elec, df_free

    except Exception as e:
        st.error(f"Error loading data: {e}")
        return (pd.DataFrame() for _ in range(6))

df_faculty, df_majors, df_core, df_7group, df_elec, df_free = load_data()

if df_faculty.empty:
    st.warning("⚠️ ไม่สามารถโหลดข้อมูลได้")
    st.stop()

# ---------------------------------------------------------
# 3. UI Setup
# ---------------------------------------------------------
st.title("🎓 Credits Checker For DekPSU")
st.markdown("---")

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    fac_options = df_faculty.apply(lambda x: f"{x['faculty_name']} ({x['major_count']} สาขา)", axis=1).tolist()
    selected_fac_display = st.selectbox("🏢 คณะ", fac_options)
    selected_fac_name = selected_fac_display.split(" (")[0]
with col2:
    filtered_majors = df_majors[df_majors['faculty_ref'] == selected_fac_name]
    if filtered_majors.empty: st.stop()
    selected_major_name = st.selectbox("📚 สาขาวิชา", filtered_majors['major_name'])
with col3:
    term_options = [1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2]
    selected_term = st.selectbox("📅 ปี/เทอม", term_options, format_func=lambda x: f"ปี {int(x)} เทอม {int((x*10)%10)}")
    
    row_major = filtered_majors[filtered_majors['major_name'] == selected_major_name].iloc[0]
    total_credits_goal = row_major['total_credits']
    selected_major_abbr = row_major['major_abbreviation']

# ---------------------------------------------------------
# 4. Filter Data
# ---------------------------------------------------------
all_major_courses = df_core[df_core['major_ref'].apply(lambda x: check_major_match(x, selected_major_abbr))]
core_subjects = all_major_courses[all_major_courses['special_type'] == 'Normal Subject']
major_electives_plan = all_major_courses[all_major_courses['special_type'] == 'Major Elective Subject']
capstone_subjects = all_major_courses[all_major_courses['special_type'].isin(['Cooperative Education', 'Major Project'])]

# Variables to track credits
earned_core_list = [0]
earned_maj_plan_list = [0]
earned_maj_pool_list = [0]
earned_capstone_list = [0]
earned_gen_list = [0]
earned_free_list = [0]
selected_subjects_data = [] 

# ---------------------------------------------------------
# 5. Tabs Content
# ---------------------------------------------------------
tabs = st.tabs(["⚙️ วิชาสาขา", "⚡ วิชาเลือกภายในสาขา", "💻 วิชาเลือก", "📚 ศึกษาทั่วไป", "🎨 เลือกเสรี", "📊 สรุปผล"])

# --- TAB 1: Core ---
with tabs[0]:
    st.info(f"Auto-check: {selected_major_abbr} (ถึงปี {int(selected_term)} เทอม {int((selected_term*10)%10)})")
    unique_terms = sorted(core_subjects['term'].unique())
    for t in unique_terms:
        is_expanded = (t <= selected_term)
        with st.expander(f"📍 ปี {int(t)} เทอม {int((t*10)%10)}", expanded=is_expanded):
            subs = core_subjects[core_subjects['term'] == t]
            for idx, row in subs.iterrows():
                is_checked = (t <= selected_term)
                key_id = f"core_{row['subject_id']}_{selected_term}_{selected_major_abbr}"
                if st.checkbox(format_subject_label(row), value=is_checked, key=key_id):
                    earned_core_list[0] += row['credits']
                    selected_subjects_data.append(row.to_dict())
    
    if not capstone_subjects.empty:
        coop = capstone_subjects[capstone_subjects['special_type'] == 'Cooperative Education']
        proj = capstone_subjects[capstone_subjects['special_type'] == 'Major Project']
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🏢 สหกิจ")
            for idx, row in coop.iterrows():
                if st.checkbox(format_subject_label(row), key=f"coop_{idx}_{selected_major_abbr}"): 
                    earned_capstone_list[0] += row['credits']
                    selected_subjects_data.append(row.to_dict())
        with c2:
            st.markdown("### 🛠️ โครงงาน")
            for idx, row in proj.iterrows():
                if st.checkbox(format_subject_label(row), key=f"proj_{idx}_{selected_major_abbr}"): 
                    earned_capstone_list[0] += row['credits']
                    selected_subjects_data.append(row.to_dict())

# --- TAB 2: Major Elective (Plan) [UPDATED WITH GROUP] ---
with tabs[1]:
    if not major_electives_plan.empty:
        # ใช้ฟังก์ชันใหม่ render_grouped_checkoxes แทน loop เดิม
        render_grouped_checkoxes(
            major_electives_plan, 
            f"me_plan_{selected_major_abbr}", 
            earned_maj_plan_list, 
            selected_subjects_data
        )
    else:
        st.info("ไม่มีวิชาเลือกในแผน")

# --- TAB 4: Pool [UPDATED WITH GROUP] ---
with tabs[2]:
    selected_pool_labels = st.multiselect("ค้นหา...", df_elec['display_label'].tolist(), key="me_pool_ms")
    for label in selected_pool_labels:
        row = df_elec[df_elec['display_label'] == label].iloc[0]
        earned_maj_pool_list[0] += row['credits']
        selected_subjects_data.append(row.to_dict())

# --- TAB 5: GenEd [UPDATED WITH GROUP] ---
with tabs[3]:
    cats = df_7group['category'].unique()
    for cat in cats:
        with st.expander(f"📚 {cat}", expanded=False):
            subs = df_7group[df_7group['category'] == cat]
            # ใช้ render group ภายใน category อีกที (ถ้ามี sub-group 1.1, 1.2)
            render_grouped_checkoxes(subs, f"gen_{cat}", earned_gen_list, selected_subjects_data)

# --- TAB 6: Free Elective ---
with tabs[4]:
    selected_free = st.multiselect("เลือกวิชาเสรี", df_free['display_label'].tolist(), key="free")
    for label in selected_free:
        row = df_free[df_free['display_label'] == label].iloc[0]
        earned_free_list[0] += row['credits']
        selected_subjects_data.append(row.to_dict())

# ---------------------------------------------------------
# 6. Summary & Sidebar
# ---------------------------------------------------------
# ดึงค่าจาก list (เพราะ pass by reference)
earned_core = earned_core_list[0]
earned_maj_plan = earned_maj_plan_list[0]
earned_maj_pool = earned_maj_pool_list[0]
earned_capstone = earned_capstone_list[0]
earned_gen = earned_gen_list[0]
earned_free = earned_free_list[0]

total_earned = earned_core + earned_maj_plan + earned_maj_pool + earned_capstone + earned_gen + earned_free
remaining = max(total_credits_goal - total_earned, 0)
percent_val = min(total_earned / total_credits_goal, 1.0)

# --- TAB 7: Summary ---
with tabs[5]:
    st.metric("รวมหน่วยกิต", f"{total_earned}/{total_credits_goal}", f"ขาด {remaining}")
    st.progress(percent_val)
    
    data = pd.DataFrame({
        'Category': ['Core', 'Maj.Elec', 'Capstone', 'GenEd', 'Free', 'Missing'],
        'Credits': [earned_core, earned_maj_plan + earned_maj_pool, earned_capstone, earned_gen, earned_free, remaining]
    })
    c = alt.Chart(data).mark_arc(innerRadius=60).encode(
        theta=alt.Theta("Credits", stack=True),
        color=alt.Color("Category", scale=alt.Scale(range=['#006064', '#E65100', '#1B5E20', '#0D47A1', '#4A148C', '#B0BEC5'])),
        tooltip=["Category", "Credits"]
    )
    st.altair_chart(c, use_container_width=True)

# --- Sidebar ---
with st.sidebar:
    st.header(f"📌 {selected_major_abbr}")
    st.caption(f"{selected_major_name}")
    st.write(f"**{selected_fac_name}**")
    st.divider()

    col_sb1, col_sb2 = st.columns(2)
    with col_sb1: st.metric("Earned", f"{total_earned}")
    with col_sb2: st.metric("Total", f"{total_credits_goal}")
    st.progress(percent_val)
    st.divider()

    st.subheader("📊 Breakdown")
    st.write(f"⚙️ Core: **{earned_core}**")
    st.write(f"⚡  Major Elec: **{earned_maj_plan + earned_maj_pool}**")
    st.write(f"🎓 Capstone: **{earned_capstone}**")
    st.write(f"📚 GenEd: **{earned_gen}**")
    st.write(f"🎨 Free Elec: **{earned_free}**")
    st.divider()

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Reload", use_container_width=True):
            load_data.clear()
            st.rerun()
