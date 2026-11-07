import streamlit as st
import os
import fitz
from pdf_processor import process_pedagogical_pdf, detect_memoires_in_pdf

st.set_page_config(
    page_title="محرر المذكرات البيداغوجية",
    page_icon="📚",
    layout="wide"
)

st.markdown("""
<style>
    .stApp {
        background-color: #F1F5F9;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        text-align: center;
        margin-bottom: 5px;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #334155;
        text-align: center;
        margin-bottom: 25px;
        font-weight: 600;
    }
    /* Labels ultra visibles */
    label, .stTextInput > label, .stSlider > label, .stSelectbox > label, .stRadio > label {
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        color: #0F172A !important;
    }
    /* Champs de saisie */
    .stTextInput input, .stSelectbox select {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        font-weight: 600 !important;
        border: 2px solid #CBD5E1 !important;
        border-radius: 6px !important;
    }
    /* Bouton principal */
    .stButton > button {
        background-color: #1D4ED8 !important;
        color: #FFFFFF !important;
        font-size: 1.15rem !important;
        font-weight: 800 !important;
        padding: 0.6rem 1.2rem !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }
    .stButton > button:hover {
        background-color: #1E40AF !important;
        color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">محرر المذكرات البيداغوجية في الرياضيات</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Personnalisation automatique et sans décalage des fiches de cours</div>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1. Choisir le document")
    
    # List PDFs in directory
    workdir = "/Users/studio/Documents/MUSTAPHA"
    local_pdfs = [f for f in os.listdir(workdir) if f.endswith(".pdf") and not f.startswith(".")]
    
    source_choice = st.radio("Source du document :", ["Choisir un fichier du dossier", "Téléverser un nouveau PDF"], horizontal=True)
    
    selected_pdf_path = None
    if source_choice == "Choisir un fichier du dossier":
        selected_file = st.selectbox("Sélectionnez le fichier :", local_pdfs)
        if selected_file:
            selected_pdf_path = os.path.join(workdir, selected_file)
    else:
        uploaded_file = st.file_uploader("Glissez votre fichier PDF ici :", type=["pdf"])
        if uploaded_file:
            temp_path = os.path.join("/tmp", uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            selected_pdf_path = temp_path

    st.subheader("2. Informations de l'enseignant")
    teacher = st.text_input("الأستاذ (Nom de l'enseignant) :", value="بورخيس مصطفى")
    school = st.text_input("المؤسسة / الثانوية (Établissement) :", value="ثانوية بوشمال محمد النذير")
    level = st.text_input("المستوى (Niveau) :", value="1 ج م ع ت")
    year = st.text_input("السنة الدراسية (Année scolaire) :", value="2026 – 2027")

    margin_lvl = st.slider(
        "هامش المستوى (Marge entre ':المستوى' et le texte en points) :",
        min_value=0,
        max_value=40,
        value=12,
        step=1,
        help="Ajustez cette marge pour éloigner le texte du titre ':المستوى' et éliminer tout chevauchement."
    )

    # 3. Détection et modification des numéros de fiches
    memoire_custom = {}
    if selected_pdf_path and os.path.exists(selected_pdf_path):
        fiches = detect_memoires_in_pdf(selected_pdf_path)
        if fiches:
            st.subheader(f"3. أرقام المذكرات ({len(fiches)} مذكرة مكتشفة)")
            auto_seq = st.checkbox("🔄 تطبيق ترقيم تسلسلي تلقائي", value=False)
            start_seq = 1
            if auto_seq:
                start_seq = st.number_input("الترقيم يبدأ من :", min_value=1, value=1, step=1)
            
            with st.expander("📑 عرض وتعديل أرقام المذكرات لكل صفحة", expanded=True):
                for i, fiche in enumerate(fiches):
                    p_num = fiche['page_num']
                    pages = fiche.get('pages', [p_num])
                    def_val = f"{(start_seq + i):02d}" if auto_seq else fiche['number']
                    c_p, c_t, c_n = st.columns([1, 2, 1])
                    with c_p:
                        p_label = f"ص {pages[0]}-{pages[-1]}" if len(pages) > 1 else f"صفحة {p_num}"
                        st.write(f"📄 **{p_label}**")
                    with c_t:
                        st.caption(f"{fiche['topic']}")
                    with c_n:
                        user_n = st.text_input(f"الرقم (P.{p_num})", value=def_val, key=f"mem_{p_num}", label_visibility="collapsed")
                        for p in pages:
                            memoire_custom[p] = user_n

with col2:
    st.subheader("4. Traitement & Aperçu")
    
    if selected_pdf_path and os.path.exists(selected_pdf_path):
        doc_info = fitz.open(selected_pdf_path)
        st.info(f"📄 **Document sélectionné :** `{os.path.basename(selected_pdf_path)}`  \n📑 **Nombre de pages :** {len(doc_info)} pages")
        doc_info.close()
        
        btn_process = st.button("🚀 Personnaliser le PDF maintenant", type="primary", use_container_width=True)
        
        if btn_process:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(curr, total):
                percent = int((curr / total) * 100)
                progress_bar.progress(percent)
                status_text.text(f"Traitement en cours... Page {curr}/{total}")

            # Define output path
            base_name = os.path.splitext(os.path.basename(selected_pdf_path))[0]
            clean_name = f"{base_name}_شخصي.pdf"
            output_path = os.path.join(workdir, clean_name)
            
            with st.spinner("Application des modifications sans décalage..."):
                result = process_pedagogical_pdf(
                    input_pdf_path=selected_pdf_path,
                    output_pdf_path=output_path,
                    teacher_name=teacher,
                    school_name=school,
                    level_name=level,
                    school_year=year,
                    margin_lvl=margin_lvl,
                    memoire_numbers=memoire_custom,
                    progress_callback=update_progress
                )
                
            progress_bar.progress(100)
            status_text.text("Terminé avec succès !")
            st.success(f"✅ **Document modifié avec succès !** ({result['modified_pages_count']} pages d'en-tête mises à jour)")
            
            # Show preview
            st.subheader("Aperçu du résultat")
            res_doc = fitz.open(output_path)
            tab1, tab2 = st.tabs(["Page de Garde", "Première Fiche"])
            with tab1:
                pix1 = res_doc[0].get_pixmap(dpi=130)
                st.image(pix1.tobytes("png"), caption="Page 1 (Page de garde)", use_container_width=True)
            with tab2:
                if len(res_doc) > 1:
                    pix2 = res_doc[1].get_pixmap(dpi=130)
                    st.image(pix2.tobytes("png"), caption="Page 2 (En-tête pédagogique)", use_container_width=True)
            res_doc.close()
            
            # Download button
            with open(output_path, "rb") as f:
                pdf_data = f.read()
            st.download_button(
                label="📥 Télécharger le PDF final",
                data=pdf_data,
                file_name=clean_name,
                mime="application/pdf",
                use_container_width=True
            )
            
            if st.button("📂 Ouvrir le dossier dans le Finder"):
                os.system(f'open "{workdir}"')
    else:
        st.write("Veuillez sélectionner un document PDF pour commencer.")
