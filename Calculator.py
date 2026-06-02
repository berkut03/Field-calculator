import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import os

def resource_path(relative_path):
    """ PyInstaller로 빌드된 환경과 일반 파이썬 환경 모두에서 절대 경로를 찾아주는 함수 """
    try:
        # PyInstaller가 만든 임시 폴더 경로
        base_path = sys._MEIPASS
    except Exception:
        # 일반 파이썬으로 실행할 때의 원래 경로
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        
        # 툴팁 표시 위치 설정 (마우스 커서보다 살짝 아래/오른쪽)
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True) # 윈도우 테두리 제거
        tw.wm_geometry(f"+{x}+{y}")

        # 💡 [핵심] 윈도우 배경을 '마젠타(자홍색)'로 칠하고, 윈도우에서 마젠타색을 투명하게 뚫어버립니다.
        try:
            tw.wm_attributes("-transparentcolor", "magenta")
        except Exception:
            pass # 혹시 윈도우 환경이 아닐 경우 뻗지 않도록 예외 처리

        # 텍스트 크기를 미리 계산해서 말풍선 크기(w, h) 정하기
        temp_label = tk.Label(tw, text=self.text, font=("Arial", 9), justify=tk.LEFT)
        temp_label.update_idletasks()
        w = temp_label.winfo_reqwidth() + 24  # 좌우 넉넉한 여백
        h = temp_label.winfo_reqheight() + 16 # 상하 넉넉한 여백
        temp_label.destroy()

        # 투명해질 마젠타색 배경을 가진 도화지(Canvas) 깔기
        canvas = tk.Canvas(tw, width=w, height=h, bg="magenta", highlightthickness=0)
        canvas.pack()

        # --- 동글동글한 모서리 모양 만들기 ---
        d = 24 # 모서리의 둥근 정도 (숫자가 클수록 더 둥글어짐)
        x1, y1 = 1, 1
        x2, y2 = w - 1, h - 1
        bg_color = "#FFFFE0"  # 부드러운 연노랑색
        
        # 1. 네 모서리에 동그라미 그리기
        canvas.create_oval(x1, y1, x1+d, y1+d, fill=bg_color, outline=bg_color)
        canvas.create_oval(x2-d, y1, x2, y1+d, fill=bg_color, outline=bg_color)
        canvas.create_oval(x1, y2-d, x1+d, y2, fill=bg_color, outline=bg_color)
        canvas.create_oval(x2-d, y2-d, x2, y2, fill=bg_color, outline=bg_color)
        
        # 2. 가운데 빈 공간을 직사각형 2개(십자가 모양)로 채워서 하나의 둥근 상자로 합치기
        canvas.create_rectangle(x1+d/2, y1, x2-d/2, y2, fill=bg_color, outline=bg_color)
        canvas.create_rectangle(x1, y1+d/2, x2, y2-d/2, fill=bg_color, outline=bg_color)

        # 3. 완성된 둥근 상자 정중앙에 텍스트 얹기
        canvas.create_text(w/2, h/2, text=self.text, font=("Arial", 9), justify=tk.LEFT, fill="#333333")

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class OpticalCalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("R-Guide 및 레티클 설계 계산기 (SolidWorks 연동형)")
        
        try:
            icon_path = resource_path("icon2.ico")
            self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"아이콘 로드 실패: {e}")
            pass

        self.root.geometry("1150x720")
    
        # 저장 폴더 설정
        self.save_dir = "Saved_Models"
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        # 데이터 변수 초기화
        self.vars = {
            'collimatorEfl': tk.StringVar(value=""),
            'pixelSizeUm': tk.StringVar(value=""),
            'roiWidth': tk.StringVar(value="640.0"),
            'roiHeight': tk.StringVar(value="480.0"),
            'imageCircle': tk.StringVar(value=""),
            'eflTele': tk.StringVar(value=""),
            'fovTele': tk.StringVar(value=""),
            'enableTele': tk.BooleanVar(value=True),
            'enableMid': tk.BooleanVar(value=False),
            'eflMid': tk.StringVar(value=""),
            'fovMid': tk.StringVar(value=""),
            'enableWide': tk.BooleanVar(value=False),
            'eflWide': tk.StringVar(value=""),
            'fovWide': tk.StringVar(value=""),
        }

        # TELE/MID/WIDE 입력 필드 참조 저장
        self.lens_entries = {'Tele': [], 'Mid': [], 'Wide': []}

        #필드별 태그 저장용 변수
        self.field_tags = {}
        self.tree_tooltip = None
        self.current_hover_item = None

        # 입력값이 바뀔 때마다 자동 계산 및 체크박스 상태 감지 - 자동 계산 기능 삭제 
        for key, var in self.vars.items():
           # var.trace_add("write", lambda *args: self.calculate())
            if key in ['enableTele', 'enableMid', 'enableWide']:
                var.trace_add("write", lambda *args: self.toggle_inputs())

        self.current_file = None

        self.create_ui()
        self.refresh_list()

        self.toggle_inputs()  # 초기 상태에 맞게 입력 필드 활성화/비활성화
       # self.calculate()

    def create_ui(self):
        # 버튼 스타일
        style = ttk.Style()
        style.configure("Center.TButton", justify="center")

        # 좌측: 파일 및 내보내기 관리 패널
        left_frame = ttk.Frame(self.root, width=220, padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(left_frame, text="저장된 모델 목록", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        # 검색어 입력창 (실시간 분류)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_list())
        search_entry = ttk.Entry(left_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, pady=(0, 5))

        if 'ToolTip' in globals():
            ToolTip(search_entry, "모델 이름의 일부를 입력하면\n해당 모델만 필터링 됩니다.")
        
        #정렬 방식 콤보박스
        self.sort_var = tk.StringVar()
        sort_combo = ttk.Combobox(left_frame, textvariable=self.sort_var, state="readonly")
        sort_combo['values'] = ("이름 오름차순 (A-Z)", "이름 내림차순 (Z-A)", "최신 수정순", "오래된 순")
        sort_combo.current(0)
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_list())
        sort_combo.pack(fill=tk.X, pady=(0, 10))

        #리스트 박스
        self.listbox = tk.Listbox(left_frame, width=25, height=15)
        self.listbox.pack(fill=tk.Y, expand=False, pady=(0, 10))
        self.listbox.bind('<<ListboxSelect>>', self.on_list_select)
        
        # 데이터 관리 버튼군
        ttk.Button(left_frame, text="새로 만들기", command=self.new_file).pack(fill=tk.X, pady=2)
        ttk.Button(left_frame, text="저장 (수정)", command=self.save_file).pack(fill=tk.X, pady=2)
        ttk.Button(left_frame, text="다른 이름 저장 (복사)", command=self.save_as_file).pack(fill=tk.X, pady=2)
        ttk.Button(left_frame, text="삭제", command=self.delete_file).pack(fill=tk.X, pady=(2, 20))
        
        # 솔리드웍스 연동 섹션
        sw_frame = ttk.LabelFrame(left_frame, text="SolidWorks 연동", padding=10)
        sw_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
        self.btn_export = ttk.Button(sw_frame, text="수식파일 내보내기\n(.txt)", style="Center.TButton", command=self.export_to_solidworks)
        self.btn_export.pack(fill=tk.X, ipady=5)

        # 우측: 메인 계산 패널
        right_frame = ttk.Frame(self.root, padding=10)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 입력부 프레임
        input_frame = ttk.Frame(right_frame)
        input_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.create_input_group(input_frame, "콜리메이터부 (Collimator)", [
            ("콜리메이터 EFL (mm)", 'collimatorEfl'),
            ("카메라 픽셀 크기 (㎛)", 'pixelSizeUm', "자주 사용하는 픽셀 크기\n - XCL-C30: 7.4\n - usb type: 6.9"),
            ("ROI 가로 (px)", 'roiWidth'),
            ("ROI 세로 (px)", 'roiHeight')
        ], 0, 0)
        
        self.create_input_group(input_frame, "레티클부 (Reticle)", [
            ("이미지 서클 (mm)", 'imageCircle')
        ], 0, 1)

        field_frame = ttk.LabelFrame(input_frame, text="Zoom (Test Lens)", padding=10)
        field_frame.grid(row=0, column=2, padx=5, sticky="nw")
        
        # TELE 입력
        ttk.Checkbutton(field_frame, text="TELE 활성화", variable=self.vars['enableTele']).grid(row=0, column=0, columnspan=4, sticky="w")
        self.create_lens_inputs(field_frame, 'Tele', 1)
        
        # MID 입력
        ttk.Checkbutton(field_frame, text="MID 활성화", variable=self.vars['enableMid']).grid(row=2, column=0, columnspan=4, sticky="w", pady=(5,0))
        self.create_lens_inputs(field_frame, 'Mid', 3)
        
        # WIDE 입력
        ttk.Checkbutton(field_frame, text="WIDE 활성화", variable=self.vars['enableWide']).grid(row=4, column=0, columnspan=4, sticky="w", pady=(5,0))
        self.create_lens_inputs(field_frame, 'Wide', 5)

        # 계산 버튼
        btn_calc = ttk.Button(right_frame, text="계산 실행", command=self.calculate, style="Center.TButton")
        btn_calc.pack(fill=tk.X, pady=(0, 15), ipady=8)

        # 테이블부
        table_frame = ttk.LabelFrame(right_frame, text="필드별 상세 설계 데이터 (0.10F ~ 0.90F)", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("field", "tele_a", "tele_d", "mid_a", "mid_d", "wide_a", "wide_d")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        self.tree.heading("field", text="필드 (F)")
        self.tree.heading("tele_a", text="TELE 각도(°)")
        self.tree.heading("tele_d", text="TELE 레티클 직경(mm)")
        self.tree.heading("mid_a", text="MID 각도(°)")
        self.tree.heading("mid_d", text="MID 레티클 직경(mm)")
        self.tree.heading("wide_a", text="WIDE 각도(°)")
        self.tree.heading("wide_d", text="WIDE 레티클 직경(mm)")
        
        for col in columns:
            self.tree.column(col, width=95, anchor="center")
        
        self.tree.pack(fill=tk.BOTH, expand=True)

        # 태그 색상 지정 및 마우스 이벤트 연결
        self.tree.tag_configure('tagged', background='#C8E6C9') # 태그 배경색 (초록색)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Motion>", self.on_tree_hover)
        self.tree.bind("<Leave>", self.hide_tree_tooltip)

        # 요약부
        self.summary_label = ttk.Label(right_frame, text="", font=("Consolas", 10), justify=tk.LEFT)
        self.summary_label.pack(fill=tk.X, pady=10)

    def create_input_group(self, parent, title, items, row, col):
        frame = ttk.LabelFrame(parent, text=title, padding=10)
        frame.grid(row=row, column=col, padx=5, sticky="nw")
        for i, item in enumerate(items):
            label_text = item[0]
            var_name = item[1]
            hint = item[2] if len(item) > 2 else ""
            
            ttk.Label(frame, text=label_text).grid(row=i, column=0, sticky="w", pady=2)
            
            # 입력창 생성
            entry = ttk.Entry(frame, textvariable=self.vars[var_name], width=10)
            entry.grid(row=i, column=1, padx=5, pady=2)
            
            # 힌트가 있으면 툴팁 연결
            if hint:
                ToolTip(entry, hint)

    def create_lens_inputs(self, parent, mode, start_row):
        ttk.Label(parent, text="EFL(mm):").grid(row=start_row, column=0, sticky="w")
        entry_efl = ttk.Entry(parent, textvariable=self.vars[f'efl{mode}'], width=8)
        entry_efl.grid(row=start_row, column=1, padx=2)
        
        ttk.Label(parent, text="FOV(°):").grid(row=start_row, column=2, sticky="w", padx=(5,0))
        entry_fov = ttk.Entry(parent, textvariable=self.vars[f'fov{mode}'], width=8)
        entry_fov.grid(row=start_row, column=3, padx=2)
        
        if mode in self.lens_entries:
            self.lens_entries[mode] = [entry_efl, entry_fov]

    def toggle_inputs(self):
        tele_state = 'normal' if self.vars['enableTele'].get() else 'disabled'
        mid_state = 'normal' if self.vars['enableMid'].get() else 'disabled'
        wide_state = 'normal' if self.vars['enableWide'].get() else 'disabled'

        for entry in self.lens_entries['Tele']:
            entry.config(state=tele_state)
        for entry in self.lens_entries['Mid']:
            entry.config(state=mid_state)
        for entry in self.lens_entries['Wide']:
            entry.config(state=wide_state)
        
        if self.vars['enableTele'].get() or self.vars['enableMid'].get() or self.vars['enableWide'].get():
            self.btn_export.config(state='normal')
        else:
            self.btn_export.config(state='disabled')

    def calculate(self):
        try:
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.summary_label.config(text="")

            e_tele = self.vars['enableTele'].get()
            e_mid = self.vars['enableMid'].get()
            e_wide = self.vars['enableWide'].get()
            
            p_mm = float(self.vars['pixelSizeUm'].get()) / 1000.0
            ic = float(self.vars['imageCircle'].get())
            c_efl = float(self.vars['collimatorEfl'].get())
            roi_w = float(self.vars['roiWidth'].get())
            roi_h = float(self.vars['roiHeight'].get())

            m_tele, fov_tele = 1, 0
            if e_tele:
                fov_tele = float(self.vars['fovTele'].get())
                m_tele = c_efl / float(self.vars['eflTele'].get())

            m_mid, fov_mid = 1, 0
            if e_mid:
                fov_mid = float(self.vars['fovMid'].get())
                m_mid = c_efl / float(self.vars['eflMid'].get())

            m_wide, fov_wide = 1, 0
            if e_wide:
                fov_wide = float(self.vars['fovWide'].get())
                m_wide = c_efl / float(self.vars['eflWide'].get())

            for i in range(2, 19):
                f = i * 0.05
                row = [f"{f:.2f}"]

                if e_tele:
                    r_tele_a = (fov_tele / 2) * f
                    r_tele_d = (ic * f) / m_tele
                    row.extend([f"{r_tele_a:.3f}", f"{r_tele_d:.3f}"])
                else:
                    row.extend(["-", "-"])
                
                if e_mid:
                    row.extend([f"{(fov_mid / 2) * f:.3f}", f"{(ic * f) / m_mid:.3f}"])
                else:
                    row.extend(["-", "-"])
                    
                if e_wide:
                    row.extend([f"{(fov_wide / 2) * f:.3f}", f"{(ic * f) / m_wide:.3f}"])
                else:
                    row.extend(["-", "-"])
                    
                item = self.tree.insert("", tk.END, values=row)
                f_str = f"{f:.2f}"
                if f_str in self.field_tags:
                    self.tree.item(item, tags=('tagged',))

            # 요약 데이터
            summary = "[가공 및 세팅 참고 데이터]\n"
            def get_sum(mode, m):
                return f"{mode:5s}: H패턴 가공크기 = {((roi_w/3)*p_mm)/m:.3f} mm  |  {int(roi_w)}x{int(roi_h)} ROI 영역 = {(roi_w*p_mm)/m:.3f} x {(roi_h*p_mm)/m:.3f} mm\n"
            
            if e_tele: summary += get_sum("TELE", m_tele)
            if e_mid: summary += get_sum("MIDDLE", m_mid)
            if e_wide: summary += get_sum("WIDE", m_wide)
            self.summary_label.config(text=summary)
            
        except ValueError:
            messagebox.showwarning("입력 오류", "계산에 필요한 숫자가 모두 입력되지 않았거나 문자가 포함되어 있습니다.\n\n빈칸을 모두 채운 후 다시 '계산 실행'을 눌러주세요.")
        except Exception as e:
            messagebox.showerror("계산 오류", f"계산중 오류가 발생했습니다:\n{e}")
    
    # 우클릭 메뉴 및 표 툴팁 기능
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item: return

        self.tree.selection_set(item) # 클릭한 줄 선택
        f_val = self.tree.item(item, "values")[0] # 예: "0.10" (필드 값)

        menu = tk.Menu(self.root, tearoff=0)
        if f_val in self.field_tags:
            menu.add_command(label="태그 수정", command=lambda: self.add_tag(item, f_val))
            menu.add_command(label="태그 삭제", command=lambda: self.remove_tag(item, f_val))
        else:
            menu.add_command(label="태그 추가", command=lambda: self.add_tag(item, f_val))
        
        menu.post(event.x_root, event.y_root)

    def add_tag(self, item, f_val):
        current_text = self.field_tags.get(f_val, "")
        new_text = simpledialog.askstring("태그 입력", f"[{f_val}F] 필드에 추가할 태그를 입력하세요:", initialvalue=current_text)
        
        if new_text is not None: 
            if new_text.strip() == "": # 빈칸으로 확인을 누르면 삭제 처리
                self.remove_tag(item, f_val)
            else:
                self.field_tags[f_val] = new_text
                self.tree.item(item, tags=('tagged',)) # 형광펜 칠하기

    def remove_tag(self, item, f_val):
        if f_val in self.field_tags:
            del self.field_tags[f_val]
            self.tree.item(item, tags=()) # 형광펜 지우기
            self.hide_tree_tooltip()

    def on_tree_hover(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            self.hide_tree_tooltip()
            return

        if item != self.current_hover_item:
            self.hide_tree_tooltip()
            self.current_hover_item = item
            f_val = self.tree.item(item, "values")[0]
            
            if f_val in self.field_tags:
                x, y = event.x_root + 15, event.y_root + 15
                self.tree_tooltip = tw = tk.Toplevel(self.root)
                tw.wm_overrideredirect(True)
                tw.wm_geometry(f"+{x}+{y}")
                tw.attributes("-topmost", True)
                tk.Label(tw, text=self.field_tags[f_val], justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("Arial", 9)).pack(ipadx=4, ipady=4)

    def hide_tree_tooltip(self, event=None):
        if self.tree_tooltip:
            self.tree_tooltip.destroy()
            self.tree_tooltip = None
        self.current_hover_item = None
    
    # 솔리드웍스 연동
    def export_to_solidworks(self):
        # 1. 활성화된 모드 수집
        active_modes = []
        if self.vars['enableTele'].get(): active_modes.append("Tele")
        if self.vars['enableMid'].get(): active_modes.append("Mid")
        if self.vars['enableWide'].get(): active_modes.append("Wide")

        if not active_modes:
            return

        # 2. 다이얼로그 생성 및 창 크기 고정
        dialog = tk.Toplevel(self.root)
        dialog.title("SolidWorks 수식 내보내기")

        try:
            icon_path = resource_path("icon2.ico")
            dialog.iconbitmap(icon_path)
        except Exception:
            pass

        dialog.geometry("340x250") # 레이아웃 추가로 인해 세로 길이를 250으로 확장
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # 3. UI 디자인 - 상단 헤더
        ttk.Label(dialog, text="내보낼 데이터를 선택하세요.", font=("Arial", 10, "bold")).pack(pady=(15, 5))

        # 4. UI 디자인 - 옵션 그룹 프레임
        radio_frame = ttk.LabelFrame(dialog, text="활성화된 모드", padding=(15, 10))
        radio_frame.pack(fill=tk.X, padx=20, pady=5)

        selected_mode = tk.StringVar(value=active_modes[0])

        # 모드별 라디오 버튼 생성 (직관적인 텍스트 추가)
        mode_display = {"Tele": "TELE", "Mid": "MIDDLE", "Wide": "WIDE"}
        for mode in ["Tele", "Mid", "Wide"]:
            if mode in active_modes:
                state = tk.NORMAL
                text_suffix = ""
            else:
                state = tk.DISABLED
                text_suffix = " (비활성화됨)"
                
            ttk.Radiobutton(
                radio_frame, 
                text=f"{mode_display[mode]} 렌즈 데이터{text_suffix}", 
                variable=selected_mode, 
                value=mode, 
                state=state
            ).pack(anchor=tk.W, pady=4)

        # 5. UI 디자인 - 하단 버튼 그룹
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(0, 15))

        def proceed_export():
            mode = selected_mode.get()
            dialog.destroy()
            self._execute_export(mode)

        # 취소 버튼과 확인 버튼을 나란히 배치
        ttk.Button(btn_frame, text="취소", command=dialog.destroy, width=10).pack(side=tk.RIGHT, padx=(5, 20))
        ttk.Button(btn_frame, text="파일 경로 지정", command=proceed_export, width=16).pack(side=tk.RIGHT, padx=(0, 5))

    def _execute_export(self, mode):
        # 실제 파일 저장 로직 (선택된 모드 기반)
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")],
            title=f"솔리드웍스 수식 파일 내보내기 ({mode.upper()})"
        )
        if not file_path:
            return

        try:
            # [수정된 부분] StringVar 빈칸 에러를 막기 위해 float()로 강제 변환
            fov = float(self.vars[f'fov{mode}'].get())
            ic = float(self.vars['imageCircle'].get())
            mag = float(self.vars['collimatorEfl'].get()) / float(self.vars[f'efl{mode}'].get())
            
            lines = []
            
            for i in range(18, 1, -1):
                f = i * 0.05
                angle = (fov / 2) * f
                
                f_str = f"{f:g}"
                
                lines.append(f'"{f_str}F" = {angle:.4f}')

            with open(file_path, 'w', encoding='utf-8') as f_out:
                f_out.write("\n".join(lines))
                
            messagebox.showinfo("내보내기 완료", f"[{mode.upper()}] 모드의 데이터가 솔리드웍스 양식으로 저장되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"파일 저장 중 오류가 발생했습니다:\n{e}")

    # --- 파일 관리 기능 ---
    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        
        # 검색어 및 정렬 옵션 가져오기 (프로그램 초기 로딩 시 변수가 없을 때를 대비한 예외처리 포함)
        search_query = self.search_var.get().lower() if hasattr(self, 'search_var') else ""
        sort_mode = self.sort_var.get() if hasattr(self, 'sort_var') else "이름 오름차순 (A-Z)"

        files_info = []
        for f in os.listdir(self.save_dir):
            if f.endswith(".json"):
                name = f.replace(".json", "")
                # 검색어가 포함된 모델만 걸러냄 (실시간 필터링)
                if search_query in name.lower():
                    path = os.path.join(self.save_dir, f)
                    mtime = os.path.getmtime(path) # 수정된 날짜 및 시간 가져오기
                    files_info.append((name, mtime))

        # 선택된 옵션에 따라 리스트 정렬
        if sort_mode == "이름 오름차순 (A-Z)":
            files_info.sort(key=lambda x: x[0].lower())
        elif sort_mode == "이름 내림차순 (Z-A)":
            files_info.sort(key=lambda x: x[0].lower(), reverse=True)
        elif sort_mode == "최신 수정순":
            files_info.sort(key=lambda x: x[1], reverse=True)
        elif sort_mode == "오래된 순":
            files_info.sort(key=lambda x: x[1])

        # 정렬된 결과를 리스트박스에 삽입
        for name, _ in files_info:
            self.listbox.insert(tk.END, name)

    def get_current_data(self):
        data = {k: v.get() for k, v in self.vars.items()}
        data['field_tags'] = self.field_tags # --- [추가 5-A]
        return data

    def on_list_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            name = self.listbox.get(selection[0])
            self.current_file = name
            path = os.path.join(self.save_dir, f"{name}.json")
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.field_tags = data.get('field_tags', {})
                for k, v in data.items():
                    if k in self.vars:
                        self.vars[k].set(v)
            self.root.title(f"R-Guide 계산기 - [{name}]")
            self.calculate()

    def new_file(self):
        self.current_file = None
        self.root.title("R-Guide 및 레티클 설계 계산기 (새 파일)")
        self.listbox.selection_clear(0, tk.END)
        self.field_tags.clear()

        for k, v in self.vars.items():
            if isinstance(v, tk.StringVar):
                if k in ['roiWidth', 'roiHeight']:
                    continue  # ROI는 초기값 유지
                v.set("")

        self.vars['roiWidth'].set("640.0")
        self.vars['roiHeight'].set("480.0")
        
        self.vars['enableTele'].set(True)
        self.vars['enableMid'].set(False)
        self.vars['enableWide'].set(False)

        for item in self.tree.get_children():
            self.tree.delete(item)
        self.summary_label.config(text="")

    def save_file(self):
        if not self.current_file:
            self.save_as_file()
            return
        path = os.path.join(self.save_dir, f"{self.current_file}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.get_current_data(), f, indent=4)
        messagebox.showinfo("저장 완료", f"'{self.current_file}' 모델을 덮어썼습니다.")

    def save_as_file(self):
        name = simpledialog.askstring("다른 이름으로 저장", "모델 이름(또는 고객사 명)을 입력하세요:")
        if name:
            self.current_file = name
            path = os.path.join(self.save_dir, f"{name}.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.get_current_data(), f, indent=4)
            self.refresh_list()
            self.root.title(f"R-Guide 계산기 - [{name}]")

    def delete_file(self):
        if self.current_file:
            if messagebox.askyesno("삭제 확인", f"'{self.current_file}' 모델을 삭제하시겠습니까?"):
                os.remove(os.path.join(self.save_dir, f"{self.current_file}.json"))
                self.current_file = None
                self.refresh_list()
                self.root.title("R-Guide 계산기")

if __name__ == "__main__":
    root = tk.Tk()
    app = OpticalCalculatorApp(root)
    root.mainloop()