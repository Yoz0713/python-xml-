import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.parser import parse_noah_xml, get_available_sessions
from src.automation import HearingAutomation
from src.config import FIELD_MAP

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SessionWizardDialog(ctk.CTkToplevel):
    """
    Multi-page wizard for selecting sessions and filling otoscopy data.
    Page 1: Inspector name + Select PTA date + Select Tympanometry date
    Page 2: Otoscopy settings (left/right ear clean/intact, images)
    Page 3: Confirm and submit
    """
    
    def __init__(self, parent, session_info, filepath, config):
        super().__init__(parent)
        
        self.parent = parent
        self.session_info = session_info
        self.filepath = filepath
        self.config = config
        self.result = None
        
        self.title("📋 聽力報告設定精靈")
        self.geometry("550x600")
        self.resizable(False, False)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Data storage
        self.selected_images = {"Left": None, "Right": None}
        self.current_page = 0
        
        # Setup pages
        self.pages = []
        self.setup_page1()
        self.setup_page2()
        self.setup_page3()
        
        # Show first page
        self.show_page(0)
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (550 // 2)
        y = (self.winfo_screenheight() // 2) - (600 // 2)
        self.geometry(f"+{x}+{y}")
    
    def setup_page1(self):
        """Page 1: Inspector + Session Selection"""
        page = ctk.CTkFrame(self, fg_color="transparent")
        
        # Title
        ctk.CTkLabel(page, text="步驟 1/3：基本設定", 
                    font=ctk.CTkFont(size=20, weight="bold"),
                    text_color="#4fc3f7").pack(pady=(20, 10))
        
        # Patient Info Display
        patient_name = self.session_info["patient_info"].get("Target_Patient_Name", "未知")
        birth_date = self.session_info["patient_info"].get("Patient_BirthDate", "")
        
        info_frame = ctk.CTkFrame(page, fg_color="#1e3a5f", corner_radius=10)
        info_frame.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(info_frame, text=f"👤 病患: {patient_name}", 
                    font=ctk.CTkFont(size=14)).pack(anchor="w", padx=15, pady=(10, 2))
        ctk.CTkLabel(info_frame, text=f"🎂 生日: {birth_date}", 
                    font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w", padx=15, pady=(0, 10))
        
        # Inspector Name
        inspector_frame = ctk.CTkFrame(page, fg_color="transparent")
        inspector_frame.pack(fill="x", padx=30, pady=15)
        ctk.CTkLabel(inspector_frame, text="檢查人員姓名 *", 
                    font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        self.entry_inspector = ctk.CTkEntry(inspector_frame, placeholder_text="請輸入檢查人員姓名", height=38)
        self.entry_inspector.pack(fill="x", pady=(5, 0))
        
        # PTA Session Selection
        pta_frame = ctk.CTkFrame(page, fg_color="transparent")
        pta_frame.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(pta_frame, text="選擇純音聽力報告", 
                    font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        
        pta_options = [s["display"] for s in self.session_info["pta_sessions"]]
        if not pta_options:
            pta_options = ["無可用的純音聽力報告"]
        self.pta_var = ctk.StringVar(value=pta_options[0] if pta_options else "")
        self.pta_dropdown = ctk.CTkOptionMenu(pta_frame, values=pta_options, variable=self.pta_var, width=400)
        self.pta_dropdown.pack(fill="x", pady=(5, 0))
        
        # Tympanometry Session Selection
        tymp_frame = ctk.CTkFrame(page, fg_color="transparent")
        tymp_frame.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(tymp_frame, text="選擇中耳鼓室圖報告", 
                    font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        
        tymp_options = [s["display"] for s in self.session_info["tymp_sessions"]]
        if not tymp_options:
            tymp_options = ["無可用的中耳鼓室圖報告"]
        self.tymp_var = ctk.StringVar(value=tymp_options[0] if tymp_options else "")
        self.tymp_dropdown = ctk.CTkOptionMenu(tymp_frame, values=tymp_options, variable=self.tymp_var, width=400)
        self.tymp_dropdown.pack(fill="x", pady=(5, 0))
        
        # Navigation
        nav_frame = ctk.CTkFrame(page, fg_color="transparent")
        nav_frame.pack(side="bottom", fill="x", padx=30, pady=20)
        
        ctk.CTkButton(nav_frame, text="下一步 →", width=120, height=40,
                     fg_color="#2196f3", hover_color="#1976d2",
                     command=lambda: self.next_page()).pack(side="right")
        
        self.pages.append(page)
    
    def setup_page2(self):
        """Page 2: Otoscopy Settings"""
        page = ctk.CTkFrame(self, fg_color="transparent")
        
        # Title
        ctk.CTkLabel(page, text="步驟 2/3：耳鏡檢查設定", 
                    font=ctk.CTkFont(size=20, weight="bold"),
                    text_color="#4fc3f7").pack(pady=(20, 15))
        
        # Initialize StringVars
        self.left_ear_clean = ctk.StringVar(value="True")
        self.left_ear_intact = ctk.StringVar(value="True")
        self.right_ear_clean = ctk.StringVar(value="True")
        self.right_ear_intact = ctk.StringVar(value="True")
        
        # Scrollable content
        content = ctk.CTkScrollableFrame(page, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20)
        
        # --- Left Ear ---
        left_frame = ctk.CTkFrame(content, fg_color="#e8f5e9", corner_radius=10, border_width=2, border_color="#4caf50")
        left_frame.pack(fill="x", pady=(0, 10))
        
        left_header = ctk.CTkFrame(left_frame, fg_color="#4caf50", corner_radius=0)
        left_header.pack(fill="x")
        ctk.CTkLabel(left_header, text="👂 左耳 Left", font=ctk.CTkFont(size=13, weight="bold"), text_color="white").pack(pady=8)
        
        left_content = ctk.CTkFrame(left_frame, fg_color="#e8f5e9")
        left_content.pack(fill="x", padx=15, pady=15)
        
        # Left Clean
        left_clean_row = ctk.CTkFrame(left_content, fg_color="#e8f5e9")
        left_clean_row.pack(fill="x", pady=5)
        ctk.CTkLabel(left_clean_row, text="耳道乾淨：", width=100, anchor="w", text_color="#1b5e20", font=ctk.CTkFont(size=12)).pack(side="left")
        ctk.CTkRadioButton(left_clean_row, text="是", variable=self.left_ear_clean, value="True", text_color="#1b5e20", fg_color="#4caf50").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(left_clean_row, text="否", variable=self.left_ear_clean, value="False", text_color="#1b5e20", fg_color="#4caf50").pack(side="left")
        
        # Left Intact
        left_intact_row = ctk.CTkFrame(left_content, fg_color="#e8f5e9")
        left_intact_row.pack(fill="x", pady=5)
        ctk.CTkLabel(left_intact_row, text="鼓膜完整：", width=100, anchor="w", text_color="#1b5e20", font=ctk.CTkFont(size=12)).pack(side="left")
        ctk.CTkRadioButton(left_intact_row, text="是", variable=self.left_ear_intact, value="True", text_color="#1b5e20", fg_color="#4caf50").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(left_intact_row, text="否", variable=self.left_ear_intact, value="False", text_color="#1b5e20", fg_color="#4caf50").pack(side="left")
        
        # Left Image
        self.btn_img_l = ctk.CTkButton(left_content, text="📷 選擇左耳圖像", height=35,
                                       fg_color="#2e7d32", hover_color="#1b5e20", text_color="white",
                                       command=lambda: self.select_image("Left"))
        self.btn_img_l.pack(fill="x", pady=(10, 0))
        
        # --- Right Ear ---
        right_frame = ctk.CTkFrame(content, fg_color="#ffebee", corner_radius=10, border_width=2, border_color="#e53935")
        right_frame.pack(fill="x", pady=(0, 10))
        
        right_header = ctk.CTkFrame(right_frame, fg_color="#e53935", corner_radius=0)
        right_header.pack(fill="x")
        ctk.CTkLabel(right_header, text="👂 右耳 Right", font=ctk.CTkFont(size=13, weight="bold"), text_color="white").pack(pady=8)
        
        right_content = ctk.CTkFrame(right_frame, fg_color="#ffebee")
        right_content.pack(fill="x", padx=15, pady=15)
        
        # Right Clean
        right_clean_row = ctk.CTkFrame(right_content, fg_color="#ffebee")
        right_clean_row.pack(fill="x", pady=5)
        ctk.CTkLabel(right_clean_row, text="耳道乾淨：", width=100, anchor="w", text_color="#b71c1c", font=ctk.CTkFont(size=12)).pack(side="left")
        ctk.CTkRadioButton(right_clean_row, text="是", variable=self.right_ear_clean, value="True", text_color="#b71c1c", fg_color="#e53935").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(right_clean_row, text="否", variable=self.right_ear_clean, value="False", text_color="#b71c1c", fg_color="#e53935").pack(side="left")
        
        # Right Intact
        right_intact_row = ctk.CTkFrame(right_content, fg_color="#ffebee")
        right_intact_row.pack(fill="x", pady=5)
        ctk.CTkLabel(right_intact_row, text="鼓膜完整：", width=100, anchor="w", text_color="#b71c1c", font=ctk.CTkFont(size=12)).pack(side="left")
        ctk.CTkRadioButton(right_intact_row, text="是", variable=self.right_ear_intact, value="True", text_color="#b71c1c", fg_color="#e53935").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(right_intact_row, text="否", variable=self.right_ear_intact, value="False", text_color="#b71c1c", fg_color="#e53935").pack(side="left")
        
        # Right Image
        self.btn_img_r = ctk.CTkButton(right_content, text="📷 選擇右耳圖像", height=35,
                                       fg_color="#c62828", hover_color="#b71c1c", text_color="white",
                                       command=lambda: self.select_image("Right"))
        self.btn_img_r.pack(fill="x", pady=(10, 0))
        
        # Navigation
        nav_frame = ctk.CTkFrame(page, fg_color="transparent")
        nav_frame.pack(side="bottom", fill="x", padx=30, pady=20)
        
        ctk.CTkButton(nav_frame, text="← 上一步", width=120, height=40,
                     fg_color="#757575", hover_color="#616161",
                     command=lambda: self.prev_page()).pack(side="left")
        ctk.CTkButton(nav_frame, text="下一步 →", width=120, height=40,
                     fg_color="#2196f3", hover_color="#1976d2",
                     command=lambda: self.next_page()).pack(side="right")
        
        self.pages.append(page)
    
    def setup_page3(self):
        """Page 3: Confirm and Submit"""
        page = ctk.CTkFrame(self, fg_color="transparent")
        
        # Title
        ctk.CTkLabel(page, text="步驟 3/3：確認並送出", 
                    font=ctk.CTkFont(size=20, weight="bold"),
                    text_color="#4fc3f7").pack(pady=(20, 15))
        
        # Summary frame
        summary_frame = ctk.CTkFrame(page, fg_color="#263238", corner_radius=10)
        summary_frame.pack(fill="both", expand=True, padx=30, pady=10)
        
        ctk.CTkLabel(summary_frame, text="📋 即將上傳的資料摘要", 
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="#81d4fa").pack(anchor="w", padx=20, pady=(15, 10))
        
        self.summary_text = ctk.CTkTextbox(summary_frame, height=300, font=ctk.CTkFont(size=12))
        self.summary_text.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        # Navigation
        nav_frame = ctk.CTkFrame(page, fg_color="transparent")
        nav_frame.pack(side="bottom", fill="x", padx=30, pady=20)
        
        ctk.CTkButton(nav_frame, text="← 上一步", width=120, height=40,
                     fg_color="#757575", hover_color="#616161",
                     command=lambda: self.prev_page()).pack(side="left")
        ctk.CTkButton(nav_frame, text="🚀 送出到 CRM", width=150, height=40,
                     fg_color="#4caf50", hover_color="#388e3c",
                     command=self.submit).pack(side="right")
        
        self.pages.append(page)
    
    def select_image(self, side):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg")])
        if path:
            self.selected_images[side] = path
            basename = os.path.basename(path)[:15]
            if side == "Left":
                self.btn_img_l.configure(text=f"✅ {basename}...")
            else:
                self.btn_img_r.configure(text=f"✅ {basename}...")
    
    def show_page(self, index):
        for p in self.pages:
            p.pack_forget()
        
        self.pages[index].pack(fill="both", expand=True)
        self.current_page = index
        
        # Update summary on page 3
        if index == 2:
            self.update_summary()
    
    def update_summary(self):
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        
        patient = self.session_info["patient_info"].get("Target_Patient_Name", "")
        summary = f"病患: {patient}\n"
        summary += f"檢查人員: {self.entry_inspector.get()}\n"
        summary += f"純音聽力: {self.pta_var.get()}\n"
        summary += f"中耳鼓室圖: {self.tymp_var.get()}\n\n"
        summary += f"左耳 - 乾淨: {self.left_ear_clean.get()}, 完整: {self.left_ear_intact.get()}\n"
        summary += f"右耳 - 乾淨: {self.right_ear_clean.get()}, 完整: {self.right_ear_intact.get()}\n"
        
        if self.selected_images["Left"]:
            summary += f"\n左耳圖像: {os.path.basename(self.selected_images['Left'])}"
        if self.selected_images["Right"]:
            summary += f"\n右耳圖像: {os.path.basename(self.selected_images['Right'])}"
        
        self.summary_text.insert("1.0", summary)
        self.summary_text.configure(state="disabled")
    
    def next_page(self):
        if self.current_page == 0:
            # Validate page 1
            if not self.entry_inspector.get().strip():
                messagebox.showwarning("提示", "請輸入檢查人員姓名")
                return
        
        if self.current_page < len(self.pages) - 1:
            self.show_page(self.current_page + 1)
    
    def prev_page(self):
        if self.current_page > 0:
            self.show_page(self.current_page - 1)
    
    def submit(self):
        # Build result data
        self.result = {
            "inspector_name": self.entry_inspector.get(),
            "pta_selection": self.pta_var.get(),
            "tymp_selection": self.tymp_var.get(),
            "otoscopy": {
                "left_clean": self.left_ear_clean.get(),
                "left_intact": self.left_ear_intact.get(),
                "right_clean": self.right_ear_clean.get(),
                "right_intact": self.right_ear_intact.get(),
                "left_image": self.selected_images["Left"],
                "right_image": self.selected_images["Right"],
            }
        }
        self.destroy()
    
    def get_result(self):
        self.wait_window()
        return self.result


class HearingAssessmentApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🌳 大樹聽中行政自動化")
        self.geometry("1000x800")
        self.minsize(900, 700)

        # Global State
        self.monitoring = False
        self.observer = None
        self.detected_file = None
        self.xml_data = {}
        self.selected_images = {"Left": None, "Right": None}

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Header
        self.setup_header()

        # Tab View
        self.tab_view = ctk.CTkTabview(self.main_container, corner_radius=10)
        self.tab_view.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        self.tab_monitor = self.tab_view.add("📡 即時監控")
        self.tab_batch = self.tab_view.add("📦 批次上傳")
        self.tab_settings = self.tab_view.add("⚙️ 設定")

        self.setup_monitor_tab()
        self.setup_batch_tab()
        self.setup_settings_tab()

    def setup_header(self):
        """Setup the header with title and status"""
        header = ctk.CTkFrame(self.main_container, fg_color="transparent", height=50)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(header, text="🎧 聽力評估自動化工具", 
                           font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=0, column=0, sticky="w")

        # Global status indicator
        self.global_status = ctk.CTkLabel(header, text="⏹️ 未啟動", 
                                         font=ctk.CTkFont(size=14),
                                         text_color="gray")
        self.global_status.grid(row=0, column=2, sticky="e", padx=10)

    # =========================================================================
    # SETTINGS TAB (Shared Configuration)
    # =========================================================================
    def setup_settings_tab(self):
        """Settings tab for CRM credentials"""
        settings_frame = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        settings_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # CRM Settings Card
        crm_card = ctk.CTkFrame(settings_frame, corner_radius=10)
        crm_card.pack(fill="x", pady=10)

        ctk.CTkLabel(crm_card, text="🔐 CRM 登入設定", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(15, 10))

        # URL
        url_frame = ctk.CTkFrame(crm_card, fg_color="transparent")
        url_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(url_frame, text="CRM 網址", width=100, anchor="w").pack(side="left")
        self.entry_url = ctk.CTkEntry(url_frame, placeholder_text="https://crm.greattree.com.tw/...")
        self.entry_url.pack(side="left", fill="x", expand=True, padx=(10, 0))
        self.entry_url.insert(0, "https://crm.greattree.com.tw/")

        # Username
        user_frame = ctk.CTkFrame(crm_card, fg_color="transparent")
        user_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(user_frame, text="帳號 (工號)", width=100, anchor="w").pack(side="left")
        self.entry_username = ctk.CTkEntry(user_frame, placeholder_text="請輸入您的工號")
        self.entry_username.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # Password
        pass_frame = ctk.CTkFrame(crm_card, fg_color="transparent")
        pass_frame.pack(fill="x", padx=20, pady=(5, 5))
        ctk.CTkLabel(pass_frame, text="密碼", width=100, anchor="w").pack(side="left")
        self.entry_password = ctk.CTkEntry(pass_frame, placeholder_text="請輸入您的密碼", show="●")
        self.entry_password.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # Store Selection
        store_frame = ctk.CTkFrame(crm_card, fg_color="transparent")
        store_frame.pack(fill="x", padx=20, pady=(5, 15))
        ctk.CTkLabel(store_frame, text="操作店別", width=100, anchor="w").pack(side="left")
        
        # Store options from the CRM
        self.store_options = {
            "不切換 (使用預設)": "",
            "桃園藝文店": "0O146270501766340937",
            "龜山萬壽店": "0O303359038470254289",
            "內壢忠孝二店": "0O309358019937740140",
            "中壢環東店": "0O311663907407279810",
            "彰化員林大同店": "0P345691397366329983",
            "湖口成長店": "0O312542441306802027",
            "北屯崇德店": "0O312543766542134683",
            "西屯福科店": "0P343591528669372377",
            "竹北中興店": "0P343592174119614845",
            "羅東倉前店": "0P345513608514105513",
        }
        
        self.store_var = ctk.StringVar(value="不切換 (使用預設)")
        self.store_dropdown = ctk.CTkOptionMenu(store_frame, values=list(self.store_options.keys()),
                                                 variable=self.store_var, width=200)
        self.store_dropdown.pack(side="left", padx=(10, 0))

        # Save hint
        ctk.CTkLabel(crm_card, text="💡 設定會在啟動自動化時使用", 
                    text_color="gray", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(0, 15))

    # =========================================================================
    # TAB 1: REAL-TIME MONITOR
    # =========================================================================
    def setup_monitor_tab(self):
        self.tab_monitor.grid_columnconfigure(0, weight=1)
        self.tab_monitor.grid_rowconfigure(2, weight=1)

        # Control Bar
        control_bar = ctk.CTkFrame(self.tab_monitor, corner_radius=10)
        control_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        control_bar.grid_columnconfigure(1, weight=1)

        self.btn_monitor = ctk.CTkButton(control_bar, text="▶️ 開始監控", 
                                        width=140, height=40,
                                        font=ctk.CTkFont(size=14, weight="bold"),
                                        command=self.toggle_monitoring)
        self.btn_monitor.grid(row=0, column=0, padx=15, pady=15)

        self.lbl_status = ctk.CTkLabel(control_bar, text="選擇資料夾開始監控", 
                                      font=ctk.CTkFont(size=13))
        self.lbl_status.grid(row=0, column=1, sticky="w", padx=10)

        self.lbl_folder = ctk.CTkLabel(control_bar, text="", text_color="gray",
                                       font=ctk.CTkFont(size=12))
        self.lbl_folder.grid(row=0, column=2, sticky="e", padx=15)

        # Patient Info Card (Shows when file detected)
        self.patient_card = ctk.CTkFrame(self.tab_monitor, corner_radius=10)
        self.patient_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.patient_card.grid_columnconfigure(1, weight=1)

        self.lbl_patient_icon = ctk.CTkLabel(self.patient_card, text="👤", 
                                            font=ctk.CTkFont(size=32))
        self.lbl_patient_icon.grid(row=0, column=0, rowspan=2, padx=15, pady=15)

        self.lbl_patient_name = ctk.CTkLabel(self.patient_card, text="等待偵測 XML 檔案...", 
                                            font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_patient_name.grid(row=0, column=1, sticky="sw", padx=5)

        self.lbl_patient_info = ctk.CTkLabel(self.patient_card, text="", 
                                            text_color="gray", font=ctk.CTkFont(size=13))
        self.lbl_patient_info.grid(row=1, column=1, sticky="nw", padx=5)

        self.btn_process = ctk.CTkButton(self.patient_card, text="⚙️ 設定並上傳", 
                                        width=130, height=36, state="disabled",
                                        fg_color="#28a745", hover_color="#218838",
                                        command=self.process_single_file)
        self.btn_process.grid(row=0, column=2, rowspan=2, padx=15, pady=15)

        # Main Content Area (Two columns)
        content_area = ctk.CTkFrame(self.tab_monitor, fg_color="transparent")
        content_area.grid(row=2, column=0, sticky="nsew")
        content_area.grid_columnconfigure(0, weight=1)
        content_area.grid_columnconfigure(1, weight=1)
        content_area.grid_rowconfigure(0, weight=1)

        # Left Column - Manual Input Form
        form_card = ctk.CTkFrame(content_area, corner_radius=10)
        form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        ctk.CTkLabel(form_card, text="📝 手動輸入欄位", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(15, 10))

        self.frame_form = ctk.CTkScrollableFrame(form_card, fg_color="transparent")
        self.frame_form.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Otoscopy section will be created dynamically in populate_manual_form
        # when XML data is loaded
        self.otoscopy_frame = None  # Placeholder for dynamic creation

        # Right Column - Status Log
        log_card = ctk.CTkFrame(content_area, corner_radius=10)
        log_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        ctk.CTkLabel(log_card, text="📋 執行狀態", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(15, 10))

        self.log_text = ctk.CTkTextbox(log_card, font=ctk.CTkFont(size=12))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Initialize form with empty state
        self.populate_manual_form()

    def toggle_monitoring(self):
        if not self.monitoring:
            path = filedialog.askdirectory(title="選擇要監控的資料夾")
            if not path:
                return

            self.monitoring = True
            self.btn_monitor.configure(text="⏹️ 停止監控", fg_color="#dc3545", hover_color="#c82333")
            self.lbl_status.configure(text="🟢 監控中...")
            self.lbl_folder.configure(text=f"📁 {path}")
            self.global_status.configure(text="🟢 監控中", text_color="#28a745")

            # Start Watchdog
            event_handler = NewFileHandler(self)
            self.observer = Observer()
            self.observer.schedule(event_handler, path, recursive=False)
            self.observer.start()
            self.log_status(f"開始監控: {path}")
        else:
            self.monitoring = False
            self.btn_monitor.configure(text="▶️ 開始監控", fg_color="#1f6aa5", hover_color="#144870")
            self.lbl_status.configure(text="⏹️ 已停止")
            self.lbl_folder.configure(text="")
            self.global_status.configure(text="⏹️ 未啟動", text_color="gray")

            if self.observer:
                self.observer.stop()
                self.observer.join()
            self.log_status("監控已停止")

    def on_new_file_detected(self, filepath):
        if filepath.endswith(".xml"):
            self.after(0, lambda: self.load_file_to_dashboard(filepath))

    def load_file_to_dashboard(self, filepath):
        # Bring window to front
        self.deiconify()
        self.lift()
        self.attributes('-topmost', True)
        self.after(100, lambda: self.attributes('-topmost', False))
        self.focus_force()

        self.detected_file = filepath
        self.log_status(f"偵測到新檔案: {os.path.basename(filepath)}")

        try:
            sessions = parse_noah_xml(filepath)
            if sessions:
                self.xml_data = sessions[0]

                # Update patient card
                patient_name = self.xml_data.get("Target_Patient_Name", "未知病患")
                birth_date = self.xml_data.get("Patient_BirthDate", "")
                test_date = self.xml_data.get("FullTestDate", "")

                self.lbl_patient_name.configure(text=f"👤 {patient_name}")
                self.lbl_patient_info.configure(text=f"生日: {birth_date} | 檔案: {os.path.basename(filepath)}")

                self.populate_manual_form()
                self.btn_process.configure(state="normal")
                self.log_status(f"解析成功: {patient_name} (生日: {birth_date})")
            else:
                self.lbl_patient_name.configure(text="⚠️ 無法解析檔案")
                self.lbl_patient_info.configure(text=os.path.basename(filepath))
        except Exception as e:
            self.lbl_patient_name.configure(text="❌ 解析錯誤")
            self.lbl_patient_info.configure(text=str(e))
            self.log_status(f"錯誤: {e}")

    def populate_manual_form(self):
        """Show parsed XML data preview. Inspector and otoscopy are now in the wizard dialog."""
        # Clear existing
        for widget in self.frame_form.winfo_children():
            widget.destroy()

        self.manual_inputs = {}

        # Only show XML data preview if data is loaded
        if self.xml_data:
            # Info message
            ctk.CTkLabel(self.frame_form, text="💡 點擊「設定並上傳」按鈕來選擇報告日期和填寫耳鏡檢查資料", 
                        font=ctk.CTkFont(size=11),
                        text_color="#ffa726",
                        wraplength=280).pack(anchor="w", pady=(0, 15))
            
            # ==========================================
            # XML Parsed Data Preview
            # ==========================================
            preview_text = ""
            skip_keys = ["Raw_FirstName", "Raw_LastName"]
            
            for key, value in self.xml_data.items():
                if key not in skip_keys and value:
                    preview_text += f"{key}: {value}\n"

            if preview_text.strip():
                ctk.CTkLabel(self.frame_form, text="📊 從 XML 解析的數據", 
                            font=ctk.CTkFont(size=12, weight="bold"),
                            text_color="#17a2b8").pack(anchor="w", pady=(0, 5))

                xml_preview = ctk.CTkTextbox(self.frame_form, height=250, font=ctk.CTkFont(size=11))
                xml_preview.pack(fill="x", pady=5)
                xml_preview.insert("1.0", preview_text)
                xml_preview.configure(state="disabled")

    def process_single_file(self):
        """Open wizard dialog and process the result."""
        if not self.detected_file:
            messagebox.showwarning("提示", "請先載入 XML 檔案")
            return
        
        # Get available sessions from XML
        try:
            session_info = get_available_sessions(self.detected_file)
        except Exception as e:
            messagebox.showerror("錯誤", f"無法解析 XML: {e}")
            return
        
        # Build config
        config = {
            "url": self.entry_url.get(),
            "username": self.entry_username.get(),
            "password": self.entry_password.get(),
            "store_id": self.store_options.get(self.store_var.get(), "")
        }
        
        # Open wizard dialog
        wizard = SessionWizardDialog(self, session_info, self.detected_file, config)
        result = wizard.get_result()
        
        if result is None:
            return  # User closed dialog
        
        # Extract selected dates from display text (format: "YYYY-MM-DD ...")
        pta_date = result["pta_selection"].split()[0] if result["pta_selection"] else None
        tymp_date = result["tymp_selection"].split()[0] if result["tymp_selection"] else None
        
        # Parse XML with the selected dates
        sessions = parse_noah_xml(self.detected_file)
        
        # Find matching sessions
        selected_data = {}
        for session in sessions:
            session_date = session.get("TestDateY", "") + "-" + session.get("TestDateM", "").zfill(2) + "-" + session.get("TestDateD", "").zfill(2)
            full_date = session.get("FullTestDate", "").split("T")[0]
            
            # Check if this session matches selected PTA date
            if pta_date and full_date == pta_date:
                # Copy PTA-related fields
                for key, value in session.items():
                    if key.startswith("PTA_") or key.startswith("Speech_") or key.startswith("Test"):
                        selected_data[key] = value
            
            # Check if this session matches selected Tymp date  
            if tymp_date and full_date == tymp_date:
                # Copy Tymp-related fields
                for key, value in session.items():
                    if key.startswith("Tymp_"):
                        selected_data[key] = value
        
        # Add patient info from first session
        if sessions:
            selected_data["Target_Patient_Name"] = sessions[0].get("Target_Patient_Name", "")
            selected_data["Patient_BirthDate"] = sessions[0].get("Patient_BirthDate", "")
        
        # Add wizard results
        selected_data["InspectorName"] = result["inspector_name"]
        selected_data["Otoscopy_Left_Clean"] = result["otoscopy"]["left_clean"]
        selected_data["Otoscopy_Left_Intact"] = result["otoscopy"]["left_intact"]
        selected_data["Otoscopy_Right_Clean"] = result["otoscopy"]["right_clean"]
        selected_data["Otoscopy_Right_Intact"] = result["otoscopy"]["right_intact"]
        
        if result["otoscopy"]["left_image"]:
            selected_data["Otoscopy_Left_Image"] = result["otoscopy"]["left_image"]
        if result["otoscopy"]["right_image"]:
            selected_data["Otoscopy_Right_Image"] = result["otoscopy"]["right_image"]
        
        # Default Speech Type
        selected_data["Speech_Left_Type"] = "1"
        selected_data["Speech_Right_Type"] = "1"
        
        self.log_status(f"📝 InspectorName: {result['inspector_name']}")
        self.log_status(f"📅 PTA 日期: {pta_date}")
        self.log_status(f"📅 Tymp 日期: {tymp_date}")
        
        self.run_automation_task(selected_data, self.detected_file)

    def log_status(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.update_idletasks()

    def run_automation_task(self, payload, filepath):
        def task():
            self.after(0, lambda: self.log_status("🚀 開始處理..."))
            self.after(0, lambda: self.btn_process.configure(state="disabled"))

            config = {
                "url": self.entry_url.get(),
                "username": self.entry_username.get(),
                "password": self.entry_password.get(),
                "store_id": self.store_options.get(self.store_var.get(), "")
            }

            try:
                self.after(0, lambda: self.log_status("🔐 正在登入 CRM..."))
                auto = HearingAutomation(headless=False)  # DEBUG: 有頭模式，可觀察操作

                self.after(0, lambda: self.log_status("🔍 正在搜尋病患..."))
                auto.run_automation(payload, filepath, config)

                self.after(0, lambda: messagebox.showinfo("成功", "✅ 處理完成！"))
                self.after(0, lambda: self.log_status("✅ 上傳成功！"))
                self.after(0, self.reset_dashboard)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("錯誤", str(e)))
                self.after(0, lambda: self.log_status(f"❌ 錯誤: {e}"))
                self.after(0, lambda: self.btn_process.configure(state="normal"))

        threading.Thread(target=task).start()

    def reset_dashboard(self):
        """Reset dashboard to initial state after successful upload."""
        self.detected_file = None
        self.xml_data = {}
        self.selected_images = {"Left": None, "Right": None}

        self.lbl_patient_name.configure(text="等待偵測 XML 檔案...")
        self.lbl_patient_info.configure(text="")
        self.btn_process.configure(state="disabled")
        
        # Clear the form area
        for widget in self.frame_form.winfo_children():
            widget.destroy()
        
        self.log_status("🔄 已重置，準備處理下一個檔案...")

    # =========================================================================
    # TAB 2: BATCH UPLOAD
    # =========================================================================
    def setup_batch_tab(self):
        self.tab_batch.grid_columnconfigure(0, weight=1)
        self.tab_batch.grid_rowconfigure(1, weight=1)

        # Folder Selection Card
        folder_card = ctk.CTkFrame(self.tab_batch, corner_radius=10)
        folder_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        folder_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(folder_card, text="📁", font=ctk.CTkFont(size=24)).grid(row=0, column=0, padx=15, pady=15)

        self.entry_batch_path = ctk.CTkEntry(folder_card, placeholder_text="選擇包含 XML 檔案的資料夾...")
        self.entry_batch_path.grid(row=0, column=1, sticky="ew", padx=5, pady=15)

        ctk.CTkButton(folder_card, text="瀏覽", width=80, 
                     command=self.browse_batch_folder).grid(row=0, column=2, padx=(5, 15), pady=15)

        # Defaults Card
        defaults_card = ctk.CTkFrame(self.tab_batch, corner_radius=10)
        defaults_card.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        ctk.CTkLabel(defaults_card, text="⚙️ 批次預設值", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(15, 10))

        defaults_frame = ctk.CTkScrollableFrame(defaults_card, fg_color="transparent")
        defaults_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.batch_defaults = {}
        defaults = [
            ("檢查人員姓名", "InspectorName"),
        ]

        for label, key in defaults:
            row = ctk.CTkFrame(defaults_frame, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=label, width=140, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, placeholder_text=f"輸入{label}")
            entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
            self.batch_defaults[key] = entry

        # Progress Area
        progress_card = ctk.CTkFrame(self.tab_batch, corner_radius=10)
        progress_card.grid(row=2, column=0, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(progress_card)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20, pady=15)

        self.lbl_progress = ctk.CTkLabel(progress_card, text="準備就緒", text_color="gray")
        self.lbl_progress.pack(pady=(0, 5))

        self.btn_start_batch = ctk.CTkButton(progress_card, text="🚀 開始批次處理", 
                                            height=40, font=ctk.CTkFont(size=14, weight="bold"),
                                            command=self.start_batch)
        self.btn_start_batch.pack(pady=(0, 15))

    def browse_batch_folder(self):
        p = filedialog.askdirectory()
        if p:
            self.entry_batch_path.delete(0, "end")
            self.entry_batch_path.insert(0, p)

    def start_batch(self):
        path = self.entry_batch_path.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("錯誤", "請選擇有效的資料夾路徑")
            return

        self.btn_start_batch.configure(state="disabled")
        defaults = {k: v.get() for k, v in self.batch_defaults.items()}
        threading.Thread(target=self.run_batch_logic, args=(path, defaults)).start()

    def run_batch_logic(self, folder_path, defaults):
        files = [f for f in os.listdir(folder_path) if f.endswith(".xml")]
        total = len(files)

        if total == 0:
            self.after(0, lambda: messagebox.showinfo("資訊", "找不到 XML 檔案"))
            self.after(0, lambda: self.btn_start_batch.configure(state="normal"))
            return

        config = {
            "url": self.entry_url.get(),
            "username": self.entry_username.get(),
            "password": self.entry_password.get()
        }

        # Statistics tracking
        success_count = 0
        fail_count = 0
        failed_files = []

        # Create log file path in the batch folder
        log_file_path = os.path.join(folder_path, "batch_log.txt")

        try:
            for i, filename in enumerate(files):
                filepath = os.path.join(folder_path, filename)
                self.after(0, lambda f=filename, idx=i+1, t=total: 
                    self.lbl_progress.configure(text=f"處理中 ({idx}/{t}): {f}"))

                try:
                    sessions = parse_noah_xml(filepath)
                    if not sessions:
                        fail_count += 1
                        error_msg = "無法解析 XML 檔案"
                        failed_files.append((filename, error_msg))
                        continue

                    data = sessions[0]
                    data.update(defaults)

                    # Add batch defaults for otoscopy (all True = normal)
                    data["Otoscopy_Left_Clean"] = "True"
                    data["Otoscopy_Left_Intact"] = "True"
                    data["Otoscopy_Right_Clean"] = "True"
                    data["Otoscopy_Right_Intact"] = "True"
                    
                    # Default Speech Type to SRT
                    data["Speech_Left_Type"] = "1"
                    data["Speech_Right_Type"] = "1"

                    # Auto-match images
                    base_name = os.path.splitext(filename)[0]
                    for ext in [".jpg", ".png", ".jpeg"]:
                        l_img = os.path.join(folder_path, f"{base_name}_L{ext}")
                        r_img = os.path.join(folder_path, f"{base_name}_R{ext}")
                        if os.path.exists(l_img):
                            data["Otoscopy_Left_Image"] = l_img
                        if os.path.exists(r_img):
                            data["Otoscopy_Right_Image"] = r_img

                    auto = HearingAutomation(headless=True)
                    auto.run_automation(data, filepath, config)
                    
                    # Success
                    success_count += 1

                except Exception as e:
                    fail_count += 1
                    error_msg = str(e)
                    failed_files.append((filename, error_msg))
                    print(f"Error processing {filename}: {e}")

                prog = (i + 1) / total
                self.after(0, lambda p=prog: self.progress_bar.set(p))

            # Write error log if there are failures
            if failed_files:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                with open(log_file_path, "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"批次處理日誌 - {timestamp}\n")
                    f.write(f"{'='*60}\n")
                    f.write(f"成功: {success_count} | 失敗: {fail_count} | 總計: {total}\n\n")
                    f.write("失敗檔案:\n")
                    for fname, error in failed_files:
                        f.write(f"  ❌ {fname}\n")
                        f.write(f"     原因: {error}\n\n")

            # Show summary dialog
            summary = f"✅ 成功: {success_count}\n❌ 失敗: {fail_count}\n📊 總計: {total}"
            if failed_files:
                summary += f"\n\n錯誤日誌已儲存至:\n{log_file_path}"
            
            self.after(0, lambda: messagebox.showinfo("批次處理完成", summary))
            self.after(0, lambda s=success_count, f=fail_count: 
                self.lbl_progress.configure(text=f"✅ 完成 - 成功: {s}, 失敗: {f}"))

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("錯誤", str(e)))
        finally:
            self.after(0, lambda: self.btn_start_batch.configure(state="normal"))


class NewFileHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_created(self, event):
        if not event.is_directory:
            self.app.on_new_file_detected(event.src_path)


if __name__ == "__main__":
    app = HearingAssessmentApp()
    app.mainloop()
