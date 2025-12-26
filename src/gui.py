import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
from src.parser import parse_noah_xml
from src.automation import HearingAutomation

class HearingAssessmentApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Hearing Assessment Automation")
        self.geometry("600x500")

        # Data store
        self.xml_data = {}
        self.xml_filepath = None
        self.vars_otoscopy = {}
        self.current_step = 0
        self.steps = []

        # Main Layout
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.nav_frame = ctk.CTkFrame(self, height=50)
        self.nav_frame.pack(fill="x", padx=20, pady=10)

        # Navigation Buttons
        self.btn_prev = ctk.CTkButton(self.nav_frame, text="Previous", command=self.prev_step, state="disabled")
        self.btn_prev.pack(side="left")

        self.btn_next = ctk.CTkButton(self.nav_frame, text="Next", command=self.next_step)
        self.btn_next.pack(side="right")

        # Initialize Steps
        self.create_steps()
        self.show_step(0)

    def create_steps(self):
        # Step 1: Target URL & Login (Optional)
        frame1 = ctk.CTkFrame(self.content_frame)
        ctk.CTkLabel(frame1, text="Step 1: Target URL & Login", font=("Arial", 20, "bold")).pack(pady=20)

        ctk.CTkLabel(frame1, text="Target Report URL *", font=("Arial", 12)).pack(anchor="w", padx=20)
        self.url_entry = ctk.CTkEntry(frame1, placeholder_text="https://crm.greattree.com.tw/...")
        self.url_entry.pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(frame1, text="Login Credentials (Optional - Auto Login if needed)", font=("Arial", 12)).pack(anchor="w", padx=20, pady=(20, 0))
        self.username_entry = ctk.CTkEntry(frame1, placeholder_text="Username (Acct)")
        self.username_entry.pack(pady=5, padx=20, fill="x")
        self.password_entry = ctk.CTkEntry(frame1, placeholder_text="Password (Pwd)", show="*")
        self.password_entry.pack(pady=5, padx=20, fill="x")

        self.steps.append(frame1)

        # Step 2: XML
        frame2 = ctk.CTkFrame(self.content_frame)
        ctk.CTkLabel(frame2, text="Step 2: Upload XML", font=("Arial", 20, "bold")).pack(pady=20)
        ctk.CTkButton(frame2, text="Select XML File", command=self.select_xml_file).pack(pady=10)
        self.lbl_filepath = ctk.CTkLabel(frame2, text="No file selected")
        self.lbl_filepath.pack(pady=5)

        ctk.CTkLabel(frame2, text="Select Report Date:", font=("Arial", 12)).pack(pady=(10, 5))
        self.session_var = ctk.StringVar(value="Select XML first")
        self.session_menu = ctk.CTkOptionMenu(frame2, variable=self.session_var, values=[], command=self.on_session_select)
        self.session_menu.pack(pady=5)

        self.lbl_test_date = ctk.CTkLabel(frame2, text="Selected Data: -")
        self.lbl_test_date.pack(pady=5)

        self.parsed_sessions = [] # Store list of sessions
        self.steps.append(frame2)

        # Step 3: Inspector
        frame3 = ctk.CTkFrame(self.content_frame)
        ctk.CTkLabel(frame3, text="Step 3: Inspector Name", font=("Arial", 20, "bold")).pack(pady=20)
        self.inspector_entry = ctk.CTkEntry(frame3, placeholder_text="Inspector Name")
        self.inspector_entry.pack(pady=10, fill="x")
        self.steps.append(frame3)

        # Step 4: Otoscopy
        frame4 = ctk.CTkScrollableFrame(self.content_frame)
        ctk.CTkLabel(frame4, text="Step 4: Otoscopy", font=("Arial", 20, "bold")).pack(pady=10)
        self.create_otoscopy_fields(frame4, "Left")
        ctk.CTkFrame(frame4, height=2, fg_color="gray").pack(fill="x", pady=10)
        self.create_otoscopy_fields(frame4, "Right")
        self.steps.append(frame4)

        # Step 5: Speech Type
        frame5 = ctk.CTkFrame(self.content_frame)
        ctk.CTkLabel(frame5, text="Step 5: Speech Audiometry", font=("Arial", 20, "bold")).pack(pady=20)

        ctk.CTkLabel(frame5, text="Left Ear Type:").pack(pady=5)
        self.speech_left_type = ctk.CTkOptionMenu(frame5, values=["SRT", "SDT"])
        self.speech_left_type.set("SRT")
        self.speech_left_type.pack(pady=5)

        ctk.CTkLabel(frame5, text="Right Ear Type:").pack(pady=5)
        self.speech_right_type = ctk.CTkOptionMenu(frame5, values=["SRT", "SDT"])
        self.speech_right_type.set("SRT")
        self.speech_right_type.pack(pady=5)
        self.steps.append(frame5)

    def create_otoscopy_fields(self, parent, side):
        frame = ctk.CTkFrame(parent)
        frame.pack(pady=5, fill="x")
        ctk.CTkLabel(frame, text=f"{side} Ear Otoscopy", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)

        # Clean Canal
        ctk.CTkLabel(frame, text="Clean Canal?").pack(anchor="w", padx=5)
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

    def show_step(self, step):
        # Hide all
        for frame in self.steps:
            frame.pack_forget()

        # Show current
        self.steps[step].pack(fill="both", expand=True)
        self.current_step = step

        # Update Buttons
        if step == 0:
            self.btn_prev.configure(state="disabled")
        else:
            self.btn_prev.configure(state="normal")

        if step == len(self.steps) - 1:
            self.btn_next.configure(text="Submit", command=self.start_automation)
        else:
            self.btn_next.configure(text="Next", command=self.next_step)

    def next_step(self):
        if self.current_step < len(self.steps) - 1:
            # Validation logic could go here
            self.show_step(self.current_step + 1)

    def prev_step(self):
        if self.current_step > 0:
            self.show_step(self.current_step - 1)

    def select_xml_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("XML Files", "*.xml")])
        if filepath:
            self.xml_filepath = filepath
            self.lbl_filepath.configure(text=filepath)
            try:
                # Returns list of dicts now
                self.parsed_sessions = parse_noah_xml(filepath)

                if not self.parsed_sessions:
                    messagebox.showwarning("Warning", "No hearing sessions found in XML.")
                    self.session_menu.configure(values=[])
                    self.session_var.set("No Data")
                    return

                # Populate OptionMenu
                # Format: "YYYY-MM-DD (Index)"
                options = []
                for idx, session in enumerate(self.parsed_sessions):
                    date_str = session.get("FullTestDate", "Unknown")
                    options.append(f"{date_str} [{idx}]")

                self.session_menu.configure(values=options)
                self.session_var.set(options[0])
                self.on_session_select(options[0]) # Select first by default

            except Exception as e:
                messagebox.showerror("Error", f"Failed to parse XML: {e}")
                self.lbl_test_date.configure(text="Test Date: Error")
                self.parsed_sessions = []

    def on_session_select(self, choice):
        if not self.parsed_sessions:
            return

        # Extract index from "YYYY-MM-DD [0]"
        try:
            idx = int(choice.split("[")[-1].replace("]", ""))
            self.xml_data = self.parsed_sessions[idx]

            # Update display label
            tymp_left = self.xml_data.get("Tymp_Left_Type", "-")
            speech_left = self.xml_data.get("Speech_Left_SRT", "-")
            self.lbl_test_date.configure(text=f"Data Preview: Tymp(L)={tymp_left}, SRT(L)={speech_left}")

        except Exception as e:
            print(f"Selection error: {e}")

    def select_image(self, side):
        filepath = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png")])
        if filepath:
            self.vars_otoscopy[f"{side}_Image_Path"] = filepath
            self.vars_otoscopy[f"{side}_Image_Label"].configure(text=filepath)

    def start_automation(self):
        url = self.url_entry.get()
        user = self.username_entry.get()
        password = self.password_entry.get()
        inspector = self.inspector_entry.get()

        if not all([url, inspector]):
            messagebox.showwarning("Missing Data", "Please fill in URL and Inspector Name.")
            return

        if not self.xml_data:
             # If parsed_sessions exists but xml_data is empty, user might not have selected?
             # But on_session_select sets it.
             # If no file selected at all:
             if not messagebox.askyesno("No XML", "No XML file selected. Proceed with manual data only?"):
                return

        self.btn_next.configure(state="disabled", text="Running...")

        # Collect Data
        manual_data = {
            "InspectorName": inspector,
            "Speech_Left_Type": self.speech_left_type.get(),
            "Speech_Right_Type": self.speech_right_type.get()
        }

        for side in ["Left", "Right"]:
            manual_data[f"Otoscopy_{side}_Clean"] = self.vars_otoscopy[f"{side}_Clean"].get()
            manual_data[f"Otoscopy_{side}_Intact"] = self.vars_otoscopy[f"{side}_Intact"].get()
            manual_data[f"Otoscopy_{side}_Desc"] = self.vars_otoscopy[f"{side}_Desc"].get("1.0", "end-1c")
            if self.vars_otoscopy[f"{side}_Image_Path"]:
                manual_data[f"Otoscopy_{side}_Image"] = self.vars_otoscopy[f"{side}_Image_Path"]

        full_data = {**self.xml_data, **manual_data}

        threading.Thread(target=self.run_automation_thread, args=(url, user, password, full_data)).start()

    def run_automation_thread(self, url, user, password, data):
        try:
            auto = HearingAutomation()
            # Navigate and wait for user to login if necessary, auto-login if creds provided
            if auto.navigate_and_wait(url, username=user, password=password):
                auto.fill_form(data)
                self.after(0, lambda: messagebox.showinfo("Success", "Automation Completed Successfully!"))
            else:
                self.after(0, lambda: messagebox.showerror("Error", "Target page not reached (Timeout or Login Failed)."))
                auto.close()
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Automation Error: {e}"))
        finally:
            self.after(0, lambda: self.btn_next.configure(state="normal", text="Submit"))

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    app = HearingAssessmentApp()
    app.mainloop()
