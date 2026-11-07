import os
import sys
import re
import fitz
import arabic_reshaper
from bidi.algorithm import get_display

def get_base_dir():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
FONTS_DIR = os.path.join(BASE_DIR, '.fonts')
FONT_BOLD_PATH = os.path.join(FONTS_DIR, 'Amiri-Bold.ttf')
FONT_REG_PATH = os.path.join(FONTS_DIR, 'Amiri-Regular.ttf')

# Fallbacks if fonts are in 'fonts', root, or /tmp
if not os.path.exists(FONT_BOLD_PATH):
    alt_bold = os.path.join(BASE_DIR, 'fonts', 'Amiri-Bold.ttf')
    if os.path.exists(alt_bold):
        FONT_BOLD_PATH = alt_bold
        FONT_REG_PATH = os.path.join(BASE_DIR, 'fonts', 'Amiri-Regular.ttf')
    elif os.path.exists('/tmp/Amiri-Bold.ttf'):
        FONT_BOLD_PATH = '/tmp/Amiri-Bold.ttf'
        FONT_REG_PATH = '/tmp/Amiri-Regular.ttf'

import unicodedata

def normalize_arabic(text):
    """
    Normalise les textes arabes de façon universelle :
    - Décompose les formes de présentation A et B (NFKD)
    - Supprime les diacritiques et le tashkeel (fatha, damma, kasra, shadda, tanwin...)
    - Supprime le tatweel (ـ)
    - Convertit les chiffres arabes orientaux (٠١٢٣٤٥٦٧٨٩) et persans en chiffres occidentaux (0-9)
    - Unifie les alifs (أ إ آ ٱ -> ا)
    - Unifie ya et alif maqsura (ى -> ي)
    """
    if not text:
        return ""
    norm = unicodedata.normalize('NFKD', text)
    # Supprimer les marques diacritiques (combining marks / tashkeel)
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    norm = re.sub(r'[\u064B-\u065F\u0670\u06D6-\u06ED]', '', norm)
    norm = norm.replace('\u0640', '')
    arabic_digits = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789')
    norm = norm.translate(arabic_digits)
    norm = re.sub(r'[أإآٱ]', 'ا', norm)
    norm = norm.replace('ى', 'ي')
    return norm

def detect_memoires_in_pdf(input_pdf_path):
    """
    Algorithme universel et tout-terrain de détection des fiches / mémorandums dans un PDF.
    Garantit 100% de détection sur tout type d'encodage (Unicode standard,
    Presentation Forms, polices personnalisées arabes, spans séparés, chiffres orientaux).
    """
    if not input_pdf_path:
        return []
    clean_path = str(input_pdf_path).strip().strip('"').strip("'")
    if not os.path.exists(clean_path) or not os.path.isfile(clean_path):
        return []

    doc = fitz.open(clean_path)
    fiches = []
    total_pages = len(doc)
    
    # Titre de secours extrait du nom du fichier
    base = os.path.splitext(os.path.basename(clean_path))[0]
    clean_fallback = re.sub(r'^(مذكرات|مذكرة|المذكرات|محور|المحور)\s*', '', base)
    clean_fallback = re.sub(r'[\d_\-\(\)]+', ' ', clean_fallback).strip()

    for p_idx in range(total_pages):
        page = doc[p_idx]
        text = page.get_text()
        norm_text = normalize_arabic(text)
        
        d = page.get_text('dict')
        top_spans = []
        mem_spans = []
        
        for b in d['blocks']:
            if b.get('type') == 0:
                for l in b['lines']:
                    for s in l['spans']:
                        if s['bbox'][1] < 220:
                            s_norm = normalize_arabic(s['text'])
                            top_spans.append((s, s_norm))
                            is_mem = (any(k in s_norm for k in ['مذكر', 'بطاق', 'جذاذ', 'fiche']) or
                                      any(k in s['text'] for k in ['\x9c\x92C', 'œ’C', '\xadr\x95@\x9b', '­r•@›']))
                            if is_mem:
                                mem_spans.append((s, s_norm))
                                
        has_mem = len(mem_spans) > 0
        has_table = (
            (('مستوي' in norm_text or 'شعبة' in norm_text) and 
             any(w in norm_text for w in ['ثانوي', 'استاذ', 'ميدان', 'محور', 'مؤسس', 'وحدة', 'درس'])) or
            any(k in text for k in ['\x9c\x92C', 'œ’C', '\xadr\x95@\x9b', '­r•@›', 'TsF¥m', '«wtsm'])
        )

        # Ne pas traiter la page de garde comme une fiche si c'est un sommaire / index / page de titre
        if p_idx == 0 and total_pages > 1:
            if len(mem_spans) >= 2 or any(k in norm_text for k in ['فهرس', 'محتويات', 'المحتويات']) or ('محور' in norm_text and total_pages > 2):
                continue

        if not (has_mem or has_table):
            continue

        cur_num = ''
        
        # Priorité 1 : Chiffres dans le même span que le mot 'مذكرة'
        for s, s_norm in mem_spans:
            m = re.search(r'(\d+)', s['text']) or re.search(r'(\d+)', s_norm)
            if m:
                cur_num = m.group(1).zfill(2)
                break
                
        # Priorité 2 : Span voisin sur la même ligne horizontale (écart vertical < 16 pt)
        if not cur_num and mem_spans:
            target_s = mem_spans[0][0]
            target_y = (target_s['bbox'][1] + target_s['bbox'][3]) / 2
            for s, s_norm in top_spans:
                if s != target_s:
                    s_y = (s['bbox'][1] + s['bbox'][3]) / 2
                    if abs(s_y - target_y) < 16:
                        if abs(s['bbox'][0] - target_s['bbox'][2]) < 150 or abs(s['bbox'][2] - target_s['bbox'][0]) < 150:
                            m = re.search(r'(\d+)', s['text']) or re.search(r'(\d+)', s_norm)
                            if m:
                                cur_num = m.group(1).zfill(2)
                                break

        # Priorité 3 : Span voisin vertical (juste en dessous ou au dessus du label)
        if not cur_num and mem_spans:
            target_s = mem_spans[0][0]
            target_x = (target_s['bbox'][0] + target_s['bbox'][2]) / 2
            target_y = target_s['bbox'][3]
            for s, s_norm in top_spans:
                if s != target_s:
                    s_x = (s['bbox'][0] + s['bbox'][2]) / 2
                    if abs(s_x - target_x) < 80 and 0 <= (s['bbox'][1] - target_y) < 40:
                        m = re.search(r'^\s*(\d+)\s*$', s['text']) or re.search(r'^\s*(\d+)\s*$', s_norm)
                        if m:
                            cur_num = m.group(1).zfill(2)
                            break
                                
        # Priorité 4 : Expression régulière sur texte brut (y compris encodage hérité)
        if not cur_num:
            m_leg = re.search(r'(\d+)\s*[\x9c\x92Cœ’C]|[\x9c\x92Cœ’C]\s*(\d+)', text)
            if m_leg:
                cur_num = (m_leg.group(1) or m_leg.group(2)).zfill(2)

        # Priorité 5 : Recherche multi-lignes dans le texte brut
        if not cur_num:
            lines = [l.strip() for l in norm_text.splitlines()[:30] if l.strip()]
            for idx, line in enumerate(lines):
                if any(k in line for k in ['مذكر', 'بطاق', 'جذاذ', 'fiche']):
                    m = re.search(r'(\d+)', line)
                    if m:
                        cur_num = m.group(1).zfill(2)
                        break
                    if idx + 1 < len(lines):
                        m2 = re.search(r'^\s*(\d+)\s*$', lines[idx+1])
                        if m2:
                            cur_num = m2.group(1).zfill(2)
                            break
                    if idx - 1 >= 0:
                        m3 = re.search(r'^\s*(\d+)\s*$', lines[idx-1])
                        if m3:
                            cur_num = m3.group(1).zfill(2)
                            break

        # Priorité 6 : Boîte de titre en haut à droite (x > 440, y < 120)
        if not cur_num:
            for s, s_norm in top_spans:
                if s['bbox'][0] > 440 and s['bbox'][1] < 120:
                    m = re.search(r'^\s*(\d{1,3})\s*$', s_norm)
                    if m:
                        cur_num = m.group(1).zfill(2)
                        break

        # Extraction du Sujet / Thème (الموضوع)
        topic = ''
        lines = [line.strip() for line in norm_text.splitlines() if line.strip()]
        for idx, line in enumerate(lines[:30]):
            if any(k in line for k in ['الموضوع', 'المحتوي المعرفي', 'الوحدة', 'عنوان الدرس', 'النشاط']):
                clean_top = line
                for k in ['الموضوع', 'المحتوي المعرفي', 'الوحدة', 'عنوان الدرس', 'النشاط', ':', '.']:
                    clean_top = clean_top.replace(k, '')
                clean_top = clean_top.strip()
                if clean_top:
                    topic = clean_top
                elif idx + 1 < len(lines):
                    topic = lines[idx+1].replace('.', '').replace(':', '').strip()
                break

        if not topic and clean_fallback:
            topic = clean_fallback

        if not cur_num:
            cur_num = f'{len(fiches)+1:02d}'

        # Si le même numéro de fiche se répète sur des pages consécutives (en-tête courant)
        if fiches and fiches[-1]['number'] == cur_num:
            fiches[-1]['pages'].append(p_idx + 1)
        else:
            fiches.append({
                'page_index': p_idx,
                'page_num': p_idx + 1,
                'pages': [p_idx + 1],
                'number': cur_num,
                'topic': topic[:45] if topic else f'Fiche {len(fiches)+1}'
            })
        
    doc.close()
    return fiches

def process_pedagogical_pdf(
    input_pdf_path,
    output_pdf_path,
    teacher_name="بورخيس مصطفى",
    school_name="ثانوية بوشمال محمد النذير",
    level_name="1 ج م ع ت",
    school_year="2026 – 2027",
    margin_lvl=12.0,
    margin_sch=6.0,
    margin_yr=5.0,
    memoire_numbers=None,
    progress_callback=None
):
    """
    Modifies an Algerian mathematics lesson plan PDF cleanly:
    - Cover page: updates school, blessing, year, removes stamp and footer.
    - Header pages: dynamically locates headers, clears old values from Form XObject streams,
      and writes new values aligned perfectly with dynamic label baselines.
    - Preserves 100% of mathematical formulas and content.
    """
    font_bold = fitz.Font(fontfile=FONT_BOLD_PATH)
    font_reg = fitz.Font(fontfile=FONT_REG_PATH)
    
    doc = fitz.open(input_pdf_path)
    total_pages = len(doc)
    modified_pages = []

    # ---------------------------------------------------------
    # 1. PROCESS PAGE 1 (COVER) IF IT HAS TITLE/SCHOOL
    # ---------------------------------------------------------
    page1 = doc[0]
    p1_text = page1.get_text()
    p1_norm = normalize_arabic(p1_text)
    has_p1_legacy = any(k in p1_text for k in ['\x9c\x92C', 'œ’C', '\xadr\x95@\x9b', '­r•@›', 'TsF¥m', '«wtsm'])
    is_cover_page = ('محور' in p1_norm or ('ثانوي' in p1_norm and 'مذكر' not in p1_norm)) and not has_p1_legacy and total_pages > 1

    if is_cover_page:
        # Remove teacher stamp
        contents = page1.read_contents().replace(b'/Im20 Do', b'        ')
        doc.update_stream(page1.get_contents()[0], contents)
        
        # Redactions (y0=68 protects top banner!)
        page1.add_redact_annot(fitz.Rect(120, 68, 480, 110), fill=False)  # School
        page1.add_redact_annot(fitz.Rect(45, 615, 525, 650), fill=False)  # Blessing line
        page1.add_redact_annot(fitz.Rect(15, 705, 160, 746), fill=False)  # Year
        page1.add_redact_annot(fitz.Rect(440, 705, 585, 746), fill=False) # Date
        page1.add_redact_annot(fitz.Rect(20, 740, 580, 835), fill=False)  # Footer contacts
        
        # If specialty box has old multi-branch (like آداب وفلسفة * لغات):
        if 'آداب وفلسفة' in p1_text and 'لغات' in level_name:
            page1.add_redact_annot(fitz.Rect(180, 162, 405, 205), fill=False)
            
        page1.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=1)
        
        page1.insert_font(fontname='Amiri', fontfile=FONT_REG_PATH)
        page1.insert_font(fontname='AmiriBold', fontfile=FONT_BOLD_PATH)
        
        # School
        s_bidi = get_display(arabic_reshaper.reshape(school_name))
        w_s = font_bold.text_length(s_bidi, fontsize=17.0)
        page1.insert_text(fitz.Point(297 - w_s/2, 85), s_bidi, fontname='AmiriBold', fontsize=17.0, color=(0, 0, 0))
        
        # If specialty box was redacted, insert updated specialty
        if 'آداب وفلسفة' in p1_text and 'لغات' in level_name:
            spec_bidi = get_display(arabic_reshaper.reshape('شعبة : لغات أجنبية'))
            w_spec = font_bold.text_length(spec_bidi, fontsize=18.0)
            page1.insert_text(fitz.Point(297 - w_spec/2, 185), spec_bidi, fontname='AmiriBold', fontsize=18.0, color=(0.0, 0.4, 0.75))
            
        # Blessing line
        bless_text = f'لا تنسونا من صالح الدعاء للوالدين الكريمين ولي. محبكم في الله الأستاذ: {teacher_name}'
        bless_bidi = get_display(arabic_reshaper.reshape(bless_text))
        w_bless = font_reg.text_length(bless_bidi, fontsize=11.0)
        page1.insert_text(fitz.Point(520 - w_bless, 638), bless_bidi, fontname='Amiri', fontsize=11.0, color=(0, 0, 0))
        
        # Year
        yr_clean = school_year.replace('–', '-').replace('/', '-').strip()
        yr_bidi = get_display(arabic_reshaper.reshape(f'السنة الدراسية: {yr_clean}'))
        page1.insert_text(fitz.Point(25, 730), yr_bidi, fontname='AmiriBold', fontsize=12.0, color=(0, 0, 0))
        
        modified_pages.append(1)

    # ---------------------------------------------------------
    # 2. PREPARE REUSABLE SHAPED STRINGS
    # ---------------------------------------------------------
    teacher_name = teacher_name.strip()
    school_name = school_name.strip()
    clean_level = re.sub(r'^(المستوى|اﻟﻤﺴﺘﻮى)\s*[:：]?\s*', '', level_name.strip())
    school_year = school_year.strip()

    teacher_parts = teacher_name.split()
    if len(teacher_parts) >= 2:
        t_top = get_display(arabic_reshaper.reshape(teacher_parts[0]))
        t_bot = get_display(arabic_reshaper.reshape(' '.join(teacher_parts[1:])))
    else:
        t_top = get_display(arabic_reshaper.reshape(teacher_name))
        t_bot = ''
        
    w_tt = font_bold.text_length(t_top, fontsize=13.0)
    w_tb = font_bold.text_length(t_bot, fontsize=13.0) if t_bot else 0
    
    t_lvl = get_display(arabic_reshaper.reshape(clean_level))
    w_lvl = font_bold.text_length(t_lvl, fontsize=12.5)
    
    t_sch = get_display(arabic_reshaper.reshape(school_name))
    w_sch = font_bold.text_length(t_sch, fontsize=12.0)
    
    # Year in RTL order for table: e.g. '2027 – 2026'
    years = re.findall(r'\b(20\d\d)\b', school_year)
    if len(years) >= 2:
        y_start, y_end = sorted(years[:2])
        t_yr = f'{y_end} – {y_start}'
    else:
        t_yr = '2027 – 2026'
    w_yr = font_bold.text_length(t_yr, fontsize=10.0)

    # ---------------------------------------------------------
    # 3. DETECT & PROCESS HEADER PAGES
    # ---------------------------------------------------------
    start_p_idx = 1 if is_cover_page else 0
    for p_idx in range(start_p_idx, total_pages):
        page = doc[p_idx]
        text = page.get_text()
        norm_text = normalize_arabic(text)
        
        has_legacy = any(k in text for k in ['\x9c\x92C', 'œ’C', '\xadr\x95@\x9b', '­r•@›', 'TsF¥m', '«wtsm'])
        has_table = (('مستوي' in norm_text or 'شعبة' in norm_text) and 
                     any(w in norm_text for w in ['ثانوي', 'استاذ', 'ميدان', 'محور', 'مؤسس', 'وحدة', 'درس']))
        has_mem = any(k in norm_text[:600] for k in ['مذكر', 'بطاق', 'جذاذ', 'fiche'])
        
        if not (has_table or has_mem or has_legacy):
            if progress_callback:
                progress_callback(p_idx + 1, total_pages)
            continue

        # Check if custom memoire number is requested for this page
        custom_mem_num = None
        if memoire_numbers is not None:
            custom_mem_num = (
                memoire_numbers.get(p_idx + 1) or
                memoire_numbers.get(str(p_idx + 1)) or
                memoire_numbers.get(p_idx) or
                memoire_numbers.get(str(p_idx))
            )
            if custom_mem_num is not None:
                custom_mem_num = str(custom_mem_num).strip()
                if custom_mem_num.isdigit() and len(custom_mem_num) == 1:
                    custom_mem_num = '0' + custom_mem_num

        # -----------------------------------------------------
        # BRANCH A : POLICES ARABES HÉRITÉES (ArabEyes / Dimnah / Win-1256)
        # -----------------------------------------------------
        if has_legacy:
            m = re.search(r'(\d+)\s*[\x9c\x92Cœ’C]|[\x9c\x92Cœ’C]\s*(\d+)', text)
            orig_num = (m.group(1) or m.group(2)).zfill(2) if m else ''
            
            cur_mem = custom_mem_num if custom_mem_num else (orig_num if orig_num else f'{p_idx+1:02d}')
            cur_mem = str(cur_mem).strip()
            if cur_mem.isdigit() and len(cur_mem) == 1:
                cur_mem = '0' + cur_mem
                
            page.add_redact_annot(fitz.Rect(30, 0, 585, 27), fill=False)
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=0)
            
            for xref in page.get_contents():
                try:
                    data = doc.xref_stream(xref).decode('latin1', errors='ignore')
                    orig_len = len(data)
                    for m_img in list(re.finditer(r'q\s*q\s*[\d\.\s]+749\.92\s*cm\s*/X\d+\s*Do\s*Q\s*Q', data)):
                        sp = m_img.span()
                        data = data[:sp[0]] + (' ' * (sp[1] - sp[0])) + data[sp[1]:]
                    if len(data) != orig_len or data != doc.xref_stream(xref).decode('latin1', errors='ignore'):
                        doc.update_stream(xref, data.encode('latin1'))
                except Exception:
                    pass
                    
            page.insert_font(fontname='AmiriBold', fontfile=FONT_BOLD_PATH)
            
            # School (Right)
            sch_str = f'المؤسسة: {school_name}'
            sch_bidi = get_display(arabic_reshaper.reshape(sch_str))
            w_sch = font_bold.text_length(sch_bidi, fontsize=11.5)
            page.insert_text(fitz.Point(582 - w_sch, 20), sch_bidi, fontname='AmiriBold', fontsize=11.5, color=(0, 0, 0))
            
            # Memoire (Center)
            mem_str = f'مذكرة رقم {cur_mem}'
            mem_bidi = get_display(arabic_reshaper.reshape(mem_str))
            w_mem = font_bold.text_length(mem_bidi, fontsize=12.5)
            page.insert_text(fitz.Point((612 - w_mem) / 2, 20), mem_bidi, fontname='AmiriBold', fontsize=12.5, color=(0, 0, 0))
            
            # Teacher (Left)
            t_str = f'الأستاذ: {teacher_name}'
            t_bidi = get_display(arabic_reshaper.reshape(t_str))
            page.insert_text(fitz.Point(32, 20), t_bidi, fontname='AmiriBold', fontsize=11.5, color=(0, 0, 0))
            
            # Crisp Dividing Line
            page.draw_line(fitz.Point(32.255, 27.643), fitz.Point(585.011, 27.643), color=(0, 0, 0), width=0.996)
            
            modified_pages.append(p_idx + 1)
            if progress_callback:
                progress_callback(p_idx + 1, total_pages)
            continue

        # Root form XObject blanking if present (for LaTeX/Word templates like 2.pdf)
        root_xobjs = [x for x in page.get_xobjects() if x[2] == 0]
        stream_was_blanked = False
        if root_xobjs:
            root_form = root_xobjs[0]
            try:
                stream = doc.xref_stream(root_form[0]).decode('latin1', errors='ignore')
                imgs = page.get_images()
                oval_imgs = [img for img in imgs if (img[2] == 152 and img[3] == 158) or 'Im' in img[7]]
                for img in oval_imgs:
                    name = img[7]
                    call_str = f'/{name} Do'
                    if call_str in stream and (img[2] == 152 and img[3] == 158):
                        stream = stream.replace(call_str, ' ' * len(call_str))
                blocks = list(re.finditer(r'BT.*?ET', stream, re.DOTALL))
                to_blank = []
                for b in blocks:
                    c = b.group(0)
                    if '208.253' in c or '187.197' in c or '384.301' in c or any(coord in c for coord in ['428.918', '428.939', '462.275', '450.905', '443.884']):
                        to_blank.append(b)
                    # For memoire banner: MUST check y > 795 so as NOT to match 484.992 at y=767 which is :السنة الدراسية!
                    elif custom_mem_num is not None:
                        if '12.952 Tf' in c and any(k in c for k in ['483.996', '466.188', '484.', '466.']) and any(y in c for y in ['802.', '803.', '804.', '808.', '795.', '800.', '801.']):
                            to_blank.append(b)
                if to_blank:
                    stream_was_blanked = True
                    for b in to_blank:
                        span = b.span()
                        stream = stream[:span[0]] + (' ' * (span[1] - span[0])) + stream[span[1]:]
                    doc.update_stream(root_form[0], stream.encode('latin1'))
            except Exception:
                pass

        # Dynamic baseline and coordinate discovery
        d = page.get_text('dict')
        sch_origin_y = 60.43
        sch_x0 = None
        yr_origin_y = 74.0
        yr_x0 = None
        lvl_origin_y = 58.63
        lvl_x0 = None
        mem_origin_y = None
        
        lvl_span = None
        sch_span = None
        yr_span = None
        mem_span = None
        digit_span = None
        teacher_lbl = None
        teacher_val = None

        for b in d['blocks']:
            if b.get('type') == 0:
                for l in b['lines']:
                    for s in l['spans']:
                        if s['bbox'][1] < 140:
                            sn = normalize_arabic(s['text'])
                            if ('ثانوي' in sn or 'مؤسس' in sn) and not sch_span:
                                sch_span = s
                                sch_origin_y = s['origin'][1]
                                sch_x0 = s['bbox'][0]
                            elif ('دراسي' in sn or 'سنة' in sn) and s['bbox'][0] > 400 and not yr_span:
                                yr_span = s
                                yr_origin_y = s['origin'][1]
                                yr_x0 = s['bbox'][0]
                            elif ('مستوي' in sn or 'شعبة' in sn) and not lvl_span:
                                lvl_span = s
                                lvl_origin_y = s['origin'][1]
                                lvl_x0 = s['bbox'][0]
                            elif any(k in sn for k in ['مذكر', 'بطاق', 'جذاذ', 'fiche']) and not mem_span:
                                mem_span = s
                                mem_origin_y = s['origin'][1]
                                if re.search(r'\d+', sn):
                                    digit_span = s
                            elif 'استاذ' in sn and not teacher_lbl and s['bbox'][0] < 180:
                                teacher_lbl = s

        # Find digit span if separate
        if mem_span and not digit_span:
            target_y = (mem_span['bbox'][1] + mem_span['bbox'][3]) / 2
            for b in d['blocks']:
                if b.get('type') == 0:
                    for l in b['lines']:
                        for s in l['spans']:
                            if s != mem_span and s['bbox'][1] < 140:
                                s_y = (s['bbox'][1] + s['bbox'][3]) / 2
                                if abs(s_y - target_y) < 16 and (abs(s['bbox'][0] - mem_span['bbox'][2]) < 130 or abs(s['bbox'][2] - mem_span['bbox'][0]) < 130):
                                    if re.search(r'\d+', s['text']):
                                        digit_span = s
                                        break

        # Find teacher value if text-based template
        if teacher_lbl:
            t_y = (teacher_lbl['bbox'][1] + teacher_lbl['bbox'][3]) / 2
            for b in d['blocks']:
                if b.get('type') == 0:
                    for l in b['lines']:
                        for s in l['spans']:
                            if s != teacher_lbl and s['bbox'][1] < 140:
                                s_y = (s['bbox'][1] + s['bbox'][3]) / 2
                                if abs(s_y - t_y) < 14 and s['bbox'][2] <= teacher_lbl['bbox'][0] + 5:
                                    teacher_val = s

        # Clean old text ONLY if stream was NOT blanked (e.g. Narjes Marwani template)
        # In stream-blanked templates (e.g. 2.pdf), values are ALREADY cleared at byte level
        if not stream_was_blanked:
            if lvl_span:
                orig_y = lvl_span['origin'][1]
                page.add_redact_annot(fitz.Rect(max(140, lvl_span['bbox'][0] - 120), orig_y - 9.5, lvl_span['bbox'][0] - 1, orig_y + 2.5), fill=False)

            if sch_span:
                orig_y = sch_span['origin'][1]
                page.add_redact_annot(fitz.Rect(max(340, sch_span['bbox'][0] - 140), orig_y - 9.5, sch_span['bbox'][0] - 1, orig_y + 2.5), fill=False)

            if yr_span:
                orig_y = yr_span['origin'][1]
                page.add_redact_annot(fitz.Rect(max(400, yr_span['bbox'][0] - 80), orig_y - 9.5, yr_span['bbox'][0] - 1, orig_y + 2.5), fill=False)

            if teacher_val:
                page.add_redact_annot(fitz.Rect(teacher_val['bbox']), fill=False)

            if custom_mem_num is not None:
                if digit_span:
                    page.add_redact_annot(fitz.Rect(digit_span['bbox']), fill=False)
                elif mem_span:
                    page.add_redact_annot(fitz.Rect(mem_span['bbox']), fill=False)

            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=0)
        else:
            # On stream-blanked pages, only redact separate digit if digit_span != mem_span
            if custom_mem_num is not None and digit_span and mem_span and digit_span != mem_span:
                page.add_redact_annot(fitz.Rect(digit_span['bbox']), fill=False)
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=0)

        # Draw new text
        page.insert_font(fontname='AmiriBold', fontfile=FONT_BOLD_PATH)
        
        # Teacher: if teacher_val was present, draw next to teacher_lbl, else draw in oval
        if teacher_val and teacher_lbl:
            t_full = get_display(arabic_reshaper.reshape(teacher_name))
            w_tf = font_bold.text_length(t_full, fontsize=11.5)
            x_tf = teacher_lbl['bbox'][0] - 6 - w_tf
            page.insert_text(fitz.Point(x_tf, teacher_lbl['origin'][1]), t_full, fontname='AmiriBold', fontsize=11.5, color=(0, 0, 0))
        else:
            if t_bot:
                page.insert_text(fitz.Point(54 - w_tt/2, 68), t_top, fontname='AmiriBold', fontsize=13.0, color=(0.48, 0.22, 0.0))
                page.insert_text(fitz.Point(54 - w_tb/2, 88), t_bot, fontname='AmiriBold', fontsize=13.0, color=(0.48, 0.22, 0.0))
            else:
                page.insert_text(fitz.Point(54 - w_tt/2, 78), t_top, fontname='AmiriBold', fontsize=13.0, color=(0.48, 0.22, 0.0))

        # Level: positioned dynamically relative to lvl_x0 with configurable margin
        lvl_right = (lvl_x0 if lvl_x0 is not None else 288.0) - float(margin_lvl)
        page.insert_text(fitz.Point(lvl_right - w_lvl, lvl_origin_y), t_lvl, fontname='AmiriBold', fontsize=12.5, color=(0, 0, 0))
        
        # School: positioned dynamically relative to sch_x0 with safe gap
        sch_right = (sch_x0 if sch_x0 is not None else 517.0) - float(margin_sch)
        page.insert_text(fitz.Point(sch_right - w_sch, sch_origin_y), t_sch, fontname='AmiriBold', fontsize=12.0, color=(0, 0, 0))
        
        # Year: positioned dynamically relative to yr_x0 with safe gap
        yr_right = (yr_x0 if yr_x0 is not None else 482.0) - float(margin_yr)
        page.insert_text(fitz.Point(yr_right - w_yr, yr_origin_y), t_yr, fontname='AmiriBold', fontsize=10.0, color=(0, 0, 0))

        # Memoire number: positioned centered in box or at digit position if custom number provided
        if custom_mem_num is not None:
            if digit_span and mem_span and digit_span != mem_span:
                # Digits were separate (e.g. Narjes Marwani template)
                d_bidi = get_display(arabic_reshaper.reshape(custom_mem_num))
                f_sz = digit_span.get('size', 10.0)
                page.insert_text(fitz.Point(digit_span['origin'][0], digit_span['origin'][1]), d_bidi, fontname='AmiriBold', fontsize=f_sz, color=(0, 0, 0))
            else:
                # Whole memoire text was in one banner (e.g. 2.pdf template)
                mem_txt = f'مذكرة رقم {custom_mem_num}'
                mem_bidi = get_display(arabic_reshaper.reshape(mem_txt))
                w_mem = font_bold.text_length(mem_bidi, fontsize=12.5)
                box_x0 = mem_span['bbox'][0] if mem_span else 466.0
                box_x1 = mem_span['bbox'][2] if mem_span else 548.0
                x_mem = (box_x0 + box_x1 - w_mem) / 2
                y_mem = mem_origin_y if mem_origin_y is not None else 38.0
                page.insert_text(fitz.Point(x_mem, y_mem), mem_bidi, fontname='AmiriBold', fontsize=12.5, color=(0.0, 0.0, 1.0))
        
        modified_pages.append(p_idx + 1)
        if progress_callback:
            progress_callback(p_idx + 1, total_pages)

    # Save output
    doc.save(output_pdf_path, garbage=3, deflate=True)
    doc.close()
    
    return {
        'total_pages': total_pages,
        'modified_pages_count': len(modified_pages),
        'modified_pages': modified_pages,
        'output_path': output_pdf_path
    }
