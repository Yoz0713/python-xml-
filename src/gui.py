import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
from src.parser import parse_noah_xml
from src.automation import HearingAutomation

class HearingAssessmentApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Hearing Assessment Automation")
        self.geometry("800x800")

        # Data store
        self.xml_data = {}
        self.xml_filepath = None

        # --- UI Layout ---
        self.create_connection_section()
        self.create_data_source_section()
        self.create_manual_entry_section()
        self.create_action_section()

    def create_connection_section(self):
        self.frame_conn = ctk.CTkFrame(self)
        self.frame_conn.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(self.frame_conn, text="Connection Settings", font=("Arial", 16, "bold")).pack(pady=5)

        self.url_entry = ctk.CTkEntry(self.frame_conn, placeholder_text="Target System URL")
        self.url_entry.pack(pady=5, padx=10, fill="x")

        self.username_entry = ctk.CTkEntry(self.frame_conn, placeholder_text="Username")
        self.username_entry.pack(pady=5, padx=10, fill="x")

        self.password_entry = ctk.CTkEntry(self.frame_conn, placeholder_text="Password", show="*")
        self.password_entry.pack(pady=5, padx=10, fill="x")

        self.patient_id_entry = ctk.CTkEntry(self.frame_conn, placeholder_text="Patient ID (Optional)")
        self.patient_id_entry.pack(pady=5, padx=10, fill="x")

    def create_data_source_section(self):
        self.frame_data = ctk.CTkFrame(self)
        self.frame_data.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(self.frame_data, text="Data Source", font=("Arial", 16, "bold")).pack(pady=5)

        self.btn_select_file = ctk.CTkButton(self.frame_data, text="Select XML File", command=self.select_xml_file)
        self.btn_select_file.pack(pady=5)

        self.lbl_filepath = ctk.CTkLabel(self.frame_data, text="No file selected")
        self.lbl_filepath.pack(pady=2)

        self.lbl_test_date = ctk.CTkLabel(self.frame_data, text="Test Date: -")
        self.lbl_test_date.pack(pady=2)

    def create_manual_entry_section(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Manual Entry", height=300)
        self.scroll_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # Inspector
        ctk.CTkLabel(self.scroll_frame, text="Inspector Name *").pack(anchor="w")
        self.inspector_entry = ctk.CTkEntry(self.scroll_frame)
        self.inspector_entry.pack(fill="x", pady=(0, 10))

        # Otoscopy Left
        self.create_otoscopy_fields(self.scroll_frame, "Left")

        # Otoscopy Right
        self.create_otoscopy_fields(self.scroll_frame, "Right")

        # Speech Audiometry Type
        ctk.CTkLabel(self.scroll_frame, text="Speech Audiometry Type", font=("Arial", 14, "bold")).pack(pady=5, anchor="w")

        grid_frame = ctk.CTkFrame(self.scroll_frame)
        grid_frame.pack(fill="x")

        ctk.CTkLabel(grid_frame, text="Left Ear Type:").grid(row=0, column=0, padx=5, pady=5)
        self.speech_left_type = ctk.CTkOptionMenu(grid_frame, values=["SRT", "SDT"])
        self.speech_left_type.set("SRT")
        self.speech_left_type.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(grid_frame, text="Right Ear Type:").grid(row=0, column=2, padx=5, pady=5)
        self.speech_right_type = ctk.CTkOptionMenu(grid_frame, values=["SRT", "SDT"])
        self.speech_right_type.set("SRT")
        self.speech_right_type.grid(row=0, column=3, padx=5, pady=5)

    def create_otoscopy_fields(self, parent, side):
        frame = ctk.CTkFrame(parent)
        frame.pack(pady=5, fill="x")

        ctk.CTkLabel(frame, text=f"{side} Ear Otoscopy", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)

        # Clean Canal
        ctk.CTkLabel(frame, text="Clean Canal?").pack(anchor="w", padx=5)
        self.vars_otoscopy = getattr(self, "vars_otoscopy", {})

        var_clean = ctk.StringVar(value="Y")
        self.vars_otoscopy[f"{side}_Clean"] = var_clean

        row1 = ctk.CTkFrame(frame, fg_color="transparent")
        row1.pack(fill="x", padx=5)
        ctk.CTkRadioButton(row1, text="Yes", variable=var_clean, value="Y").pack(side="left", padx=10)
        ctk.CTkRadioButton(row1, text="No", variable=var_clean, value="N").pack(side="left", padx=10)

        # Intact Eardrum
        ctk.CTkLabel(frame, text="Intact Eardrum?").pack(anchor="w", padx=5)
        var_intact = ctk.StringVar(value="Y")
        self.vars_otoscopy[f"{side}_Intact"] = var_intact

        row2 = ctk.CTkFrame(frame, fg_color="transparent")
        row2.pack(fill="x", padx=5)
        ctk.CTkRadioButton(row2, text="Yes", variable=var_intact, value="Y").pack(side="left", padx=10)
        ctk.CTkRadioButton(row2, text="No", variable=var_intact, value="N").pack(side="left", padx=10)

        # Description
        ctk.CTkLabel(frame, text="Description").pack(anchor="w", padx=5)
        txt_desc = ctk.CTkTextbox(frame, height=60)
        txt_desc.pack(fill="x", padx=5, pady=5)
        self.vars_otoscopy[f"{side}_Desc"] = txt_desc

        # Image Upload
        row3 = ctk.CTkFrame(frame, fg_color="transparent")
        row3.pack(fill="x", padx=5, pady=5)
        ctk.CTkButton(row3, text="Select Image", width=100,
                      command=lambda s=side: self.select_image(s)).pack(side="left")
        lbl_img = ctk.CTkLabel(row3, text="No image selected")
        lbl_img.pack(side="left", padx=10)
        self.vars_otoscopy[f"{side}_Image_Label"] = lbl_img
        self.vars_otoscopy[f"{side}_Image_Path"] = None

    def create_action_section(self):
        self.btn_start = ctk.CTkButton(self, text="Start Automation", command=self.start_automation, height=40, font=("Arial", 16, "bold"))
        self.btn_start.pack(pady=10, padx=10, fill="x")

    # --- Logic ---

    def select_xml_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("XML Files", "*.xml")])
        if filepath:
            self.xml_filepath = filepath
            self.lbl_filepath.configure(text=filepath)
            try:
                self.xml_data = parse_noah_xml(filepath)
                date_str = self.xml_data.get("FullTestDate", "Unknown")
                self.lbl_test_date.configure(text=f"Test Date: {date_str}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to parse XML: {e}")
                self.lbl_test_date.configure(text="Test Date: Error")

    def select_image(self, side):
        filepath = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png")])
        if filepath:
            self.vars_otoscopy[f"{side}_Image_Path"] = filepath
            self.vars_otoscopy[f"{side}_Image_Label"].configure(text=filepath)

    def start_automation(self):
        # Validation
        url = self.url_entry.get()
        user = self.username_entry.get()
        password = self.password_entry.get()
        inspector = self.inspector_entry.get()

        if not all([url, user, password, inspector]):
            messagebox.showwarning("Missing Data", "Please fill in URL, Username, Password, and Inspector Name.")
            return

        if not self.xml_data:
            if not messagebox.askyesno("No XML", "No XML file selected. Proceed with manual data only?"):
                return

        # Disable button
        self.btn_start.configure(state="disabled", text="Running...")

        # Collect Data
        manual_data = {
            "InspectorName": inspector,
            "Speech_Left_Type": self.speech_left_type.get(),
            "Speech_Right_Type": self.speech_right_type.get()
        }

        # Otoscopy Data
        for side in ["Left", "Right"]:
            manual_data[f"Otoscopy_{side}_Clean"] = self.vars_otoscopy[f"{side}_Clean"].get()
            manual_data[f"Otoscopy_{side}_Intact"] = self.vars_otoscopy[f"{side}_Intact"].get()
            manual_data[f"Otoscopy_{side}_Desc"] = self.vars_otoscopy[f"{side}_Desc"].get("1.0", "end-1c")
            if self.vars_otoscopy[f"{side}_Image_Path"]:
                manual_data[f"Otoscopy_{side}_Image"] = self.vars_otoscopy[f"{side}_Image_Path"]

        full_data = {**self.xml_data, **manual_data}

        # Run in thread to keep UI responsive
        threading.Thread(target=self.run_automation_thread, args=(url, user, password, full_data)).start()

    def run_automation_thread(self, url, user, password, data):
        try:
            auto = HearingAutomation() # Defaults to not headless
            if auto.login(url, user, password):
                auto.fill_form(data)
                messagebox.showinfo("Success", "Automation Completed Successfully!")
                # Keep browser open or close? Prompt doesn't specify.
                # Usually better to keep open for verification, or close.
                # I'll wait a bit then close or just leave it.
                # Let's leave it open for user to review, but the script object might go out of scope.
                # Ideally, we should ask the user or just detach.
                # But for this simple app, we can just say complete.
            else:
                messagebox.showerror("Error", "Login failed.")
                auto.close()
        except Exception as e:
            messagebox.showerror("Error", f"Automation Error: {e}")
        finally:
            self.btn_start.configure(state="normal", text="Start Automation")

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    app = HearingAssessmentApp()
    app.mainloop()
