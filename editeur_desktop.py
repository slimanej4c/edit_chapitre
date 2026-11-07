import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from pdf_processor import process_pedagogical_pdf, detect_memoires_in_pdf

# -------------------------------------------------------------
# PALETTE DE COULEURS HAUTE VISIBILITÉ (HIGH CONTRAST)
# -------------------------------------------------------------
COLOR_BG_ROOT       = "#F1F5F9"  # Fond de la fenêtre (Gris ardoise clair)
COLOR_CARD_BG       = "#FFFFFF"  # Fond des blocs (Blanc pur)
COLOR_BORDER        = "#CBD5E1"  # Bordure des blocs (Gris clair net)
COLOR_TEXT_MAIN     = "#0F172A"  # Texte principal (Noir ardoise profond, très lisible)
COLOR_TEXT_MUTED    = "#334155"  # Texte secondaire (Gris foncé ardoise)
COLOR_TEXT_HEADER   = "#1D4ED8"  # Titres de sections (Bleu vif contrasté)

COLOR_INPUT_BG      = "#F8FAFC"  # Fond des champs de saisie
COLOR_INPUT_FG      = "#0F172A"  # Couleur du texte saisi (Noir profond)
COLOR_INPUT_BORDER  = "#94A3B8"  # Bordure des champs

COLOR_BTN_PRIMARY   = "#1D4ED8"  # Bouton d'action principal (Bleu royal éclatant)
COLOR_BTN_HOVER     = "#1E40AF"  # Bouton au survol
COLOR_BTN_ACTIVE    = "#172554"  # Bouton au clic
COLOR_BTN_TEXT      = "#FFFFFF"  # Texte du bouton (Blanc pur très contrasté)

COLOR_BTN_SEC_BG    = "#E2E8F0"  # Bouton secondaire (Parcourir...)
COLOR_BTN_SEC_HOVER = "#CBD5E1"
COLOR_BTN_SEC_TEXT  = "#0F172A"  # Texte noir sur bouton gris clair

COLOR_BADGE_BG      = "#DBEAFE"  # Badge de la marge
COLOR_BADGE_FG      = "#1E40AF"  # Texte du badge
COLOR_HINT_TEXT     = "#047857"  # Astuce verte foncée


class ModernButton(tk.Label):
    """
    Bouton personnalisé garantissant une couleur de fond et un texte 100% visibles
    sur macOS et Windows indépendamment du mode sombre.
    """
    def __init__(self, master, text, command=None, bg=COLOR_BTN_PRIMARY, fg=COLOR_BTN_TEXT,
                 hover_bg=COLOR_BTN_HOVER, active_bg=COLOR_BTN_ACTIVE,
                 font=("Arial", 11, "bold"), padx=14, pady=6, **kwargs):
        super().__init__(
            master, text=text, bg=bg, fg=fg, font=font,
            padx=padx, pady=pady, cursor="pointinghand",
            relief=tk.RAISED, bd=1, **kwargs
        )
        self.command = command
        self.default_bg = bg
        self.default_fg = fg
        self.hover_bg = hover_bg
        self.active_bg = active_bg
        self.is_disabled = False

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, e):
        if not self.is_disabled:
            self.configure(bg=self.hover_bg)

    def _on_leave(self, e):
        if not self.is_disabled:
            self.configure(bg=self.default_bg)

    def _on_press(self, e):
        if not self.is_disabled:
            self.configure(bg=self.active_bg, relief=tk.SUNKEN)

    def _on_release(self, e):
        if not self.is_disabled:
            self.configure(bg=self.hover_bg, relief=tk.RAISED)
            if self.command:
                self.command()

    def set_state(self, state):
        if state == tk.DISABLED or state == "disabled":
            self.is_disabled = True
            self.configure(bg="#94A3B8", fg="#F8FAFC", cursor="arrow", relief=tk.FLAT)
        else:
            self.is_disabled = False
            self.configure(bg=self.default_bg, fg=self.default_fg, cursor="pointinghand", relief=tk.RAISED)


class PDFEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("محرر المذكرات البيداغوجية - Éditeur de Fiches Pédagogiques")
        self.root.geometry("730x780")
        self.root.minsize(680, 680)
        self.root.configure(bg=COLOR_BG_ROOT)

        # Style pour widgets natifs
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TProgressbar', background=COLOR_BTN_PRIMARY, troughcolor=COLOR_CARD_BG)
        style.configure('Horizontal.TScale', background=COLOR_CARD_BG, troughcolor=COLOR_BG_ROOT)

        self.detected_fiches = []
        self.memoire_entries = {}

        # Conteneur principal
        main_frame = tk.Frame(root, bg=COLOR_BG_ROOT, padx=14, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # En-tête titre principal
        title_label = tk.Label(
            main_frame,
            text="محرر المذكرات البيداغوجية في الرياضيات",
            font=("Arial", 17, "bold"),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_BG_ROOT
        )
        title_label.pack(pady=(0, 2))

        sub_label = tk.Label(
            main_frame,
            text="Personnalisation des informations, des marges et des numéros de fiches",
            font=("Arial", 10, "bold"),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG_ROOT
        )
        sub_label.pack(pady=(0, 8))

        # -------------------------------------------------------------
        # 1. FICHIER PDF
        # -------------------------------------------------------------
        card_file = tk.Frame(main_frame, bg=COLOR_CARD_BG, bd=1, relief=tk.SOLID, padx=10, pady=8)
        card_file.pack(fill=tk.X, pady=(0, 8))

        lbl_sec1 = tk.Label(
            card_file,
            text="📁 1. Document PDF à modifier",
            font=("Arial", 11, "bold"),
            fg=COLOR_TEXT_HEADER,
            bg=COLOR_CARD_BG
        )
        lbl_sec1.pack(anchor="w", pady=(0, 4))

        file_row = tk.Frame(card_file, bg=COLOR_CARD_BG)
        file_row.pack(fill=tk.X)

        self.file_path_var = tk.StringVar(value="")
        self._last_loaded_path = ""
        self.file_entry = tk.Entry(
            file_row,
            textvariable=self.file_path_var,
            font=("Arial", 10),
            bg=COLOR_INPUT_BG,
            fg=COLOR_INPUT_FG,
            insertbackground=COLOR_INPUT_FG,
            relief=tk.SOLID,
            bd=1
        )
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=4)

        browse_btn = ModernButton(
            file_row,
            text="Parcourir...",
            command=self.browse_file,
            bg=COLOR_BTN_SEC_BG,
            fg=COLOR_BTN_SEC_TEXT,
            hover_bg=COLOR_BTN_SEC_HOVER,
            active_bg="#94A3B8",
            font=("Arial", 10, "bold"),
            padx=12,
            pady=4
        )
        browse_btn.pack(side=tk.RIGHT, padx=(0, 4))

        refresh_btn = ModernButton(
            file_row,
            text="🔄 فحص وتحديث",
            command=self.refresh_memoires,
            bg=COLOR_BTN_SEC_BG,
            fg=COLOR_BTN_SEC_TEXT,
            hover_bg=COLOR_BTN_SEC_HOVER,
            active_bg="#94A3B8",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=4
        )
        refresh_btn.pack(side=tk.RIGHT, padx=(0, 4))

        # Surveiller tout changement de chemin (saisie, collage, ou bouton Parcourir)
        self.file_path_var.trace_add("write", self._on_file_path_changed)

        # -------------------------------------------------------------
        # 2. INFORMATIONS EN ARABE
        # -------------------------------------------------------------
        card_info = tk.Frame(main_frame, bg=COLOR_CARD_BG, bd=1, relief=tk.SOLID, padx=10, pady=8)
        card_info.pack(fill=tk.X, pady=(0, 8))

        lbl_sec2 = tk.Label(
            card_info,
            text="📝 2. Vos Informations (Arabe)",
            font=("Arial", 11, "bold"),
            fg=COLOR_TEXT_HEADER,
            bg=COLOR_CARD_BG
        )
        lbl_sec2.pack(anchor="w", pady=(0, 4))

        fields = [
            ("الأستاذ (Nom de l'enseignant) :", "teacher", "بورخيس مصطفى"),
            ("المؤسسة (Établissement) :", "school", "ثانوية بوشمال محمد النذير"),
            ("المستوى (Niveau) :", "level", "1 ج م ع ت"),
            ("السنة الدراسية (Année scolaire) :", "year", "2026 – 2027")
        ]

        self.entries = {}
        for idx, (label_text, key, default_val) in enumerate(fields):
            row_frame = tk.Frame(card_info, bg=COLOR_CARD_BG)
            row_frame.pack(fill=tk.X, pady=2)

            lbl = tk.Label(
                row_frame,
                text=label_text,
                font=("Arial", 10, "bold"),
                fg=COLOR_TEXT_MAIN,
                bg=COLOR_CARD_BG,
                anchor="w"
            )
            lbl.pack(side=tk.LEFT)

            entry = tk.Entry(
                row_frame,
                font=("Arial", 10, "bold"),
                bg=COLOR_INPUT_BG,
                fg=COLOR_INPUT_FG,
                insertbackground=COLOR_INPUT_FG,
                relief=tk.SOLID,
                bd=1,
                justify="right",
                width=28
            )
            entry.insert(0, default_val)
            entry.pack(side=tk.RIGHT, ipady=3)
            self.entries[key] = entry

        # -------------------------------------------------------------
        # 3. RÉGLAGE DE LA MARGE
        # -------------------------------------------------------------
        card_margin = tk.Frame(main_frame, bg=COLOR_CARD_BG, bd=1, relief=tk.SOLID, padx=10, pady=8)
        card_margin.pack(fill=tk.X, pady=(0, 8))

        m_row = tk.Frame(card_margin, bg=COLOR_CARD_BG)
        m_row.pack(fill=tk.X)

        lbl_margin_lvl = tk.Label(
            m_row,
            text="⚙️ 3. هامش المستوى (Marge ':المستوى' en pt) :",
            font=("Arial", 10, "bold"),
            fg=COLOR_TEXT_HEADER,
            bg=COLOR_CARD_BG,
            anchor="w"
        )
        lbl_margin_lvl.pack(side=tk.LEFT)

        self.margin_lvl_var = tk.DoubleVar(value=12.0)

        self.margin_badge = tk.Label(
            m_row,
            text="12 pt",
            font=("Arial", 10, "bold"),
            fg=COLOR_BADGE_FG,
            bg=COLOR_BADGE_BG,
            padx=8,
            pady=2,
            relief=tk.SOLID,
            bd=1
        )
        self.margin_badge.pack(side=tk.RIGHT)

        slider_lvl = ttk.Scale(
            m_row,
            from_=0,
            to=40,
            orient=tk.HORIZONTAL,
            variable=self.margin_lvl_var,
            command=self.on_margin_lvl_change,
            style='Horizontal.TScale'
        )
        slider_lvl.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)

        # -------------------------------------------------------------
        # 4. NUMÉROS DES FICHES / MÉMOIRES (DÉTECTION & ÉDITION)
        # -------------------------------------------------------------
        self.card_mem = tk.Frame(main_frame, bg=COLOR_CARD_BG, bd=1, relief=tk.SOLID, padx=10, pady=8)
        self.card_mem.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        mem_header_row = tk.Frame(self.card_mem, bg=COLOR_CARD_BG)
        mem_header_row.pack(fill=tk.X, pady=(0, 4))

        self.lbl_sec4 = tk.Label(
            mem_header_row,
            text="📑 4. أرقام المذكرات في الملف (Numéros des Fiches)",
            font=("Arial", 11, "bold"),
            fg=COLOR_TEXT_HEADER,
            bg=COLOR_CARD_BG
        )
        self.lbl_sec4.pack(side=tk.LEFT)

        # Outils de réindexation rapide
        tools_row = tk.Frame(self.card_mem, bg=COLOR_CARD_BG)
        tools_row.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            tools_row,
            text="ترقيم تسلسلي يبدأ من :",
            font=("Arial", 9, "bold"),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_CARD_BG
        ).pack(side=tk.LEFT, padx=(0, 4))

        self.start_num_entry = tk.Entry(
            tools_row,
            width=4,
            font=("Arial", 10, "bold"),
            justify="center",
            bg=COLOR_INPUT_BG,
            fg=COLOR_INPUT_FG,
            relief=tk.SOLID,
            bd=1
        )
        self.start_num_entry.insert(0, "1")
        self.start_num_entry.pack(side=tk.LEFT, padx=(0, 6), ipady=2)

        btn_apply_seq = ModernButton(
            tools_row,
            text="تطبيق الترقيم التلقائي",
            command=self.apply_auto_renumber,
            bg=COLOR_BTN_SEC_BG,
            fg=COLOR_BTN_SEC_TEXT,
            hover_bg=COLOR_BTN_SEC_HOVER,
            active_bg="#94A3B8",
            font=("Arial", 9, "bold"),
            padx=10,
            pady=3
        )
        btn_apply_seq.pack(side=tk.LEFT, padx=(0, 6))

        btn_reset_mem = ModernButton(
            tools_row,
            text="إعادة ضبط للأصل",
            command=self.reset_to_detected_numbers,
            bg=COLOR_BTN_SEC_BG,
            fg=COLOR_BTN_SEC_TEXT,
            hover_bg=COLOR_BTN_SEC_HOVER,
            active_bg="#94A3B8",
            font=("Arial", 9, "bold"),
            padx=10,
            pady=3
        )
        btn_reset_mem.pack(side=tk.LEFT)

        # Scrollable container for memoire rows
        self.mem_container = tk.Frame(self.card_mem, bg=COLOR_CARD_BG, bd=1, relief=tk.SOLID)
        self.mem_container.pack(fill=tk.BOTH, expand=True)

        self.mem_canvas = tk.Canvas(self.mem_container, bg=COLOR_CARD_BG, highlightthickness=0, height=130)
        self.mem_scrollbar = ttk.Scrollbar(self.mem_container, orient="vertical", command=self.mem_canvas.yview)
        self.scrollable_mem_frame = tk.Frame(self.mem_canvas, bg=COLOR_CARD_BG)

        self.scrollable_mem_frame.bind(
            "<Configure>",
            lambda e: self.mem_canvas.configure(scrollregion=self.mem_canvas.bbox("all"))
        )
        self.canvas_window = self.mem_canvas.create_window((0, 0), window=self.scrollable_mem_frame, anchor="nw")
        self.mem_canvas.bind("<Configure>", lambda e: self.mem_canvas.itemconfig(self.canvas_window, width=e.width))

        self.mem_canvas.configure(yscrollcommand=self.mem_scrollbar.set)
        self.mem_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.mem_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Message par défaut avant chargement
        self.empty_mem_label = tk.Label(
            self.scrollable_mem_frame,
            text="💡 يرجى اختيار ملف PDF أعلاه لكشف المذكرات وتعديل أرقامها تلقائياً.",
            font=("Arial", 10),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD_BG,
            pady=20
        )
        self.empty_mem_label.pack(fill=tk.X, expand=True)

        # -------------------------------------------------------------
        # 5. BOUTON D'ACTION & PROGRESSION
        # -------------------------------------------------------------
        self.btn_process = ModernButton(
            main_frame,
            text="🚀 Personnaliser le PDF maintenant",
            command=self.start_processing,
            bg=COLOR_BTN_PRIMARY,
            fg=COLOR_BTN_TEXT,
            hover_bg=COLOR_BTN_HOVER,
            active_bg=COLOR_BTN_ACTIVE,
            font=("Arial", 13, "bold"),
            pady=9
        )
        self.btn_process.pack(fill=tk.X, pady=(2, 6))

        self.progress = ttk.Progressbar(main_frame, mode='determinate', style='TProgressbar')
        self.progress.pack(fill=tk.X, pady=(0, 4))

        self.status_label = tk.Label(
            main_frame,
            text="Prêt",
            font=("Arial", 10, "bold"),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG_ROOT
        )
        self.status_label.pack()

        # Essayer de charger le premier PDF local s'il existe
        self._check_initial_file()

    def _check_initial_file(self):
        default_file = os.path.join(os.getcwd(), "مذكرات_محور_الأعداد_والحساب_سنة_اولى_ج_م_ع-Copy.pdf")
        if not os.path.exists(default_file):
            default_file = os.path.join(os.getcwd(), "2.pdf")
        if os.path.exists(default_file):
            self.file_path_var.set(default_file)
            self.load_memoires(default_file)

    def _on_file_path_changed(self, *args):
        """Déclenché automatiquement dès que le chemin change (saisie, collage, navigation)"""
        raw_path = self.file_path_var.get().strip().strip('"').strip("'")
        if raw_path and os.path.exists(raw_path) and os.path.isfile(raw_path) and raw_path.lower().endswith(".pdf"):
            if self._last_loaded_path != raw_path:
                self.load_memoires(raw_path)

    def refresh_memoires(self):
        """Force la ré-analyse du document actuellement sélectionné"""
        raw_path = self.file_path_var.get().strip().strip('"').strip("'")
        if not raw_path or not os.path.exists(raw_path) or not os.path.isfile(raw_path):
            messagebox.showwarning("تنبيه", "يرجى اختيار ملف PDF صالح أولاً.")
            return
        self.load_memoires(raw_path)

    def on_margin_lvl_change(self, val):
        v = int(round(float(val)))
        self.margin_badge.config(text=f"{v} pt")

    def browse_file(self):
        f = filedialog.askopenfilename(
            title="Choisir le fichier PDF",
            initialdir=os.getcwd(),
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if f:
            clean_f = f.strip().strip('"').strip("'")
            self.file_path_var.set(clean_f)
            self.status_label.config(text=f"Fichier sélectionné : {os.path.basename(clean_f)}", fg=COLOR_TEXT_MAIN)
            self.load_memoires(clean_f)

    def load_memoires(self, pdf_path):
        """Scanne le PDF et génère la liste des mémorandums avec champs éditables"""
        pdf_path = str(pdf_path).strip().strip('"').strip("'")
        self._last_loaded_path = pdf_path

        # Effacer les lignes précédentes
        for widget in self.scrollable_mem_frame.winfo_children():
            widget.destroy()
        self.memoire_entries.clear()

        if not os.path.exists(pdf_path) or not os.path.isfile(pdf_path):
            lbl = tk.Label(
                self.scrollable_mem_frame,
                text="⚠️ المسار غير موجود أو لا يشير إلى ملف PDF صالح.",
                font=("Arial", 10, "bold"),
                fg="#DC2626",
                bg=COLOR_CARD_BG,
                pady=15
            )
            lbl.pack(fill=tk.X)
            self.lbl_sec4.config(text="📑 4. أرقام المذكرات في الملف")
            return

        try:
            self.detected_fiches = detect_memoires_in_pdf(pdf_path)
            if not self.detected_fiches:
                lbl = tk.Label(
                    self.scrollable_mem_frame,
                    text="ℹ️ لم يتم العثور على مذكرات داخل هذا الملف.\n(تأكد من أن الملف يحتوي على صفحات مذكرات بيداغوجية)",
                    font=("Arial", 10),
                    fg=COLOR_TEXT_MUTED,
                    bg=COLOR_CARD_BG,
                    pady=15
                )
                lbl.pack(fill=tk.X)
                self.lbl_sec4.config(text="📑 4. أرقام المذكرات في الملف (0 مذكرة مكتشفة)")
                return

            self.lbl_sec4.config(text=f"📑 4. أرقام المذكرات المكتشفة ({len(self.detected_fiches)} مذكرة)")

            for idx, fiche in enumerate(self.detected_fiches):
                p_num = fiche['page_num']
                orig_num = fiche['number']
                topic = fiche['topic']

                bg_row = COLOR_CARD_BG if idx % 2 == 0 else "#F8FAFC"
                row = tk.Frame(self.scrollable_mem_frame, bg=bg_row, pady=4, padx=8, bd=1, relief=tk.SOLID)
                row.pack(fill=tk.X, expand=True, pady=1)

                # Page tag
                pages = fiche.get('pages', [p_num])
                p_text = f"📄 ص {pages[0]}-{pages[-1]}" if len(pages) > 1 else f"📄 صفحة {p_num}"
                lbl_page = tk.Label(
                    row,
                    text=p_text,
                    font=("Arial", 10, "bold"),
                    fg="#1D4ED8",
                    bg=bg_row,
                    width=10,
                    anchor="w"
                )
                lbl_page.pack(side=tk.LEFT)

                # Topic / Subject
                lbl_top = tk.Label(
                    row,
                    text=f"الموضوع : {topic}",
                    font=("Arial", 9, "bold"),
                    fg=COLOR_TEXT_MAIN,
                    bg=bg_row,
                    anchor="w"
                )
                lbl_top.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

                # Entry for number
                e_num = tk.Entry(
                    row,
                    width=6,
                    font=("Arial", 11, "bold"),
                    justify="center",
                    bg="#FFFFFF",
                    fg="#1D4ED8",
                    insertbackground="#1D4ED8",
                    relief=tk.SOLID,
                    bd=1
                )
                e_num.insert(0, orig_num)
                e_num.pack(side=tk.RIGHT, padx=4, ipady=2)

                tk.Label(
                    row,
                    text="الرقم :",
                    font=("Arial", 9, "bold"),
                    fg=COLOR_TEXT_MUTED,
                    bg=bg_row
                ).pack(side=tk.RIGHT)

                self.memoire_entries[p_num] = e_num

            # Forcer le rafraîchissement immédiat de la zone de défilement
            self.scrollable_mem_frame.update_idletasks()
            self.mem_canvas.configure(scrollregion=self.mem_canvas.bbox("all"))
            self.mem_canvas.yview_moveto(0)

        except Exception as e:
            lbl_err = tk.Label(
                self.scrollable_mem_frame,
                text=f"خطأ أثناء فحص الملف: {e}",
                font=("Arial", 9, "bold"),
                fg="#DC2626",
                bg=COLOR_CARD_BG,
                pady=10
            )
            lbl_err.pack(pady=5)

    def apply_auto_renumber(self):
        """Applique une numérotation séquentielle automatique (ex: 01, 02, 03...)"""
        val_str = self.start_num_entry.get().strip()
        try:
            start_val = int(val_str)
        except ValueError:
            start_val = 1

        curr = start_val
        for p_num in sorted(self.memoire_entries.keys()):
            entry = self.memoire_entries[p_num]
            entry.delete(0, tk.END)
            entry.insert(0, f"{curr:02d}")
            curr += 1

    def reset_to_detected_numbers(self):
        """Réinitialise les champs aux numéros détectés d'origine dans le PDF"""
        for fiche in self.detected_fiches:
            p_num = fiche['page_num']
            if p_num in self.memoire_entries:
                entry = self.memoire_entries[p_num]
                entry.delete(0, tk.END)
                entry.insert(0, fiche['number'])

    def start_processing(self):
        input_pdf = self.file_path_var.get().strip().strip('"').strip("'")
        if not input_pdf or not os.path.exists(input_pdf) or not os.path.isfile(input_pdf):
            messagebox.showerror("Erreur", "Veuillez sélectionner un fichier PDF valide.")
            return

        self.btn_process.set_state(tk.DISABLED)
        self.status_label.config(text="Traitement en cours...", fg=COLOR_BTN_PRIMARY)
        self.progress['value'] = 0

        threading.Thread(target=self.run_process, args=(input_pdf,), daemon=True).start()

    def run_process(self, input_pdf):
        try:
            teacher = self.entries['teacher'].get().strip()
            school = self.entries['school'].get().strip()
            level = self.entries['level'].get().strip()
            year = self.entries['year'].get().strip()
            margin_lvl = float(self.margin_lvl_var.get())

            # Récupérer les numéros de mémoires personnalisés
            memoire_numbers = {}
            for fiche in self.detected_fiches:
                p_num = fiche['page_num']
                entry = self.memoire_entries.get(p_num)
                if entry:
                    val = entry.get().strip()
                    if val:
                        for p in fiche.get('pages', [p_num]):
                            memoire_numbers[p] = val

            dir_name = os.path.dirname(input_pdf)
            base_name = os.path.splitext(os.path.basename(input_pdf))[0]
            output_pdf = os.path.join(dir_name, f"{base_name}_شخصي.pdf")

            def update_progress(curr, total):
                val = int((curr / total) * 100)
                self.progress['value'] = val
                self.status_label.config(text=f"Traitement page {curr}/{total}...")
                self.root.update_idletasks()

            result = process_pedagogical_pdf(
                input_pdf_path=input_pdf,
                output_pdf_path=output_pdf,
                teacher_name=teacher,
                school_name=school,
                level_name=level,
                school_year=year,
                margin_lvl=margin_lvl,
                memoire_numbers=memoire_numbers,
                progress_callback=update_progress
            )

            self.progress['value'] = 100
            self.status_label.config(text="Terminé avec succès !", fg=COLOR_HINT_TEXT)

            msg = (
                f"Le document a été personnalisé avec succès !\n\n"
                f"• Pages modifiées : {result['modified_pages_count']}\n"
                f"• Marge appliquée : {int(margin_lvl)} pt\n"
                f"• Fiches numérotées : {len(memoire_numbers)}\n"
                f"• Enregistré sous :\n{os.path.basename(output_pdf)}"
            )

            if messagebox.askyesno("Succès", f"{msg}\n\nVoulez-vous ouvrir le dossier contenant le fichier ?"):
                import sys
                if sys.platform == 'win32':
                    norm_path = os.path.normpath(output_pdf)
                    os.system(f'explorer /select,"{norm_path}"')
                elif sys.platform == 'darwin':
                    os.system(f'open -R "{output_pdf}"')
                else:
                    os.system(f'xdg-open "{os.path.dirname(output_pdf)}"')

        except Exception as e:
            messagebox.showerror("Erreur lors du traitement", str(e))
            self.status_label.config(text="Erreur lors du traitement", fg="#DC2626")
        finally:
            self.btn_process.set_state(tk.NORMAL)


if __name__ == '__main__':
    root = tk.Tk()
    app = PDFEditorApp(root)
    root.mainloop()
