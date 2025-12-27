import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.parser import parse_noah_xml
from src.automation import HearingAutomation
from src.config import FIELD_MAP

class HearingAssessmentApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Hearing Assessment Automation (Dual-Mode)")
        self.geometry("900x700")

        # Global State
        self.monitoring = False
        self.observer = None
        self.detected_file = None
        self.xml_data = {}

        # Layout
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=20, pady=20)

        self.tab_monitor = self.tab_view.add("Real-Time Monitor")
        self.tab_batch = self.tab_view.add("Batch Upload")

        self.setup_monitor_tab()
        self.setup_batch_tab()

    # =========================================================================
    # TAB 1: REAL-TIME MONITOR (WATCHDOG)
    # =========================================================================
    def setup_monitor_tab(self):
        # Top Bar: Controls
        frame_top = ctk.CTkFrame(self.tab_monitor)
        frame_top.pack(fill="x", pady=10)

        self.btn_monitor = ctk.CTkButton(frame_top, text="Start Monitoring", command=self.toggle_monitoring)
        self.btn_monitor.pack(side="left", padx=10)

        self.lbl_status = ctk.CTkLabel(frame_top, text="Status: Stopped", text_color="red")
        self.lbl_status.pack(side="left", padx=10)

        # User Config (Shared)
        frame_config = ctk.CTkFrame(self.tab_monitor)
        frame_config.pack(fill="x", pady=5)
        ctk.CTkLabel(frame_config, text="CRM URL:").pack(side="left", padx=5)
        self.entry_url = ctk.CTkEntry(frame_config, width=300)
        self.entry_url.pack(side="left", padx=5)
        # Placeholder: pre-fill
        self.entry_url.insert(0, "https://crm.greattree.com.tw/...")

        # Dashboard Area (Hidden initially)
        self.frame_dashboard = ctk.CTkFrame(self.tab_monitor)
        self.frame_dashboard.pack(fill="both", expand=True, pady=10)

        self.lbl_new_file = ctk.CTkLabel(self.frame_dashboard, text="Waiting for new files...", font=("Arial", 16))
        self.lbl_new_file.pack(pady=20)

        # Dynamic Form Area
        self.frame_form = ctk.CTkScrollableFrame(self.frame_dashboard, height=300)
        # We will populate this when a file is detected

        # Action Buttons
        self.btn_process = ctk.CTkButton(self.frame_dashboard, text="Upload & Process", state="disabled", command=self.process_single_file)
        self.btn_process.pack(pady=10)

    def toggle_monitoring(self):
        if not self.monitoring:
            # Start
            path = filedialog.askdirectory(title="Select Folder to Monitor")
            if not path: return

            self.monitoring = True
            self.btn_monitor.configure(text="Stop Monitoring", fg_color="red")
            self.lbl_status.configure(text=f"Monitoring: {path}", text_color="green")

            # Start Watchdog
            event_handler = NewFileHandler(self)
            self.observer = Observer()
            self.observer.schedule(event_handler, path, recursive=False)
            self.observer.start()
        else:
            # Stop
            self.monitoring = False
            self.btn_monitor.configure(text="Start Monitoring", fg_color="#1f6aa5")
            self.lbl_status.configure(text="Status: Stopped", text_color="red")
            if self.observer:
                self.observer.stop()
                self.observer.join()

    def on_new_file_detected(self, filepath):
        """Called by Watchdog Thread. Use after() to update GUI."""
        if filepath.endswith(".xml"):
            self.after(0, lambda: self.load_file_to_dashboard(filepath))

    def load_file_to_dashboard(self, filepath):
        self.detected_file = filepath
        self.lbl_new_file.configure(text=f"New File Detected: {os.path.basename(filepath)}")

        # Parse
        try:
            sessions = parse_noah_xml(filepath)
            if sessions:
                self.xml_data = sessions[0] # Default to most recent
                # TODO: Allow selecting session if multiple

                # Show Form
                self.frame_form.pack(fill="both", expand=True, pady=10)
                self.populate_manual_form()
                self.btn_process.configure(state="normal")
            else:
                 self.lbl_new_file.configure(text=f"Error: No sessions in {os.path.basename(filepath)}")
        except Exception as e:
            self.lbl_new_file.configure(text=f"Error Parsing: {e}")

    def populate_manual_form(self):
        # Clear existing
        for widget in self.frame_form.winfo_children():
            widget.destroy()

        # Add Manual Fields (Case History, Sales, Price) as requested
        # Plus Otoscopy fields

        fields = [
            ("Case History", "Text"),
            ("Sales Model", "Text"),
            ("Price", "Text"),
            ("Inspector Name", "Text")
        ]

        self.manual_inputs = {}

        for name, ftype in fields:
            row = ctk.CTkFrame(self.frame_form)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=name, width=150, anchor="w").pack(side="left", padx=5)
            entry = ctk.CTkEntry(row)
            entry.pack(side="left", fill="x", expand=True, padx=5)
            self.manual_inputs[name] = entry

        # Add Image Selectors
        img_row = ctk.CTkFrame(self.frame_form)
        img_row.pack(fill="x", pady=10)
        self.btn_img_l = ctk.CTkButton(img_row, text="Select Left Image", command=lambda: self.select_img("Left"))
        self.btn_img_l.pack(side="left", padx=5)
        self.btn_img_r = ctk.CTkButton(img_row, text="Select Right Image", command=lambda: self.select_img("Right"))
        self.btn_img_r.pack(side="left", padx=5)

    def select_img(self, side):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png")])
        if path:
            print(f"Selected {side}: {path}")
            # TODO: Store path in self.xml_data or separate dict

    def process_single_file(self):
        # Gather data from manual inputs
        manual_data = {
            "InspectorName": self.manual_inputs["Inspector Name"].get(),
            # ... others
        }

        # Merge
        full_payload = {**self.xml_data, **manual_data}

        # Run Automation
        self.run_automation_task(full_payload, self.detected_file)

    def run_automation_task(self, payload, filepath):
        # Threaded execution
        def task():
            config = {
                "url": self.entry_url.get(),
                "username": "admin", # TODO: Add inputs for these
                "password": "password"
            }
            try:
                # Per requirements: "Workflow: Setup: Headless Chrome".
                # For Monitor mode, user already did manual entry, so automation can be headless.
                auto = HearingAutomation(headless=True)
                auto.run_automation(payload, filepath, config)
                self.after(0, lambda: messagebox.showinfo("Success", "Processing Complete"))
                self.after(0, self.reset_dashboard)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=task).start()

    def reset_dashboard(self):
        self.detected_file = None
        self.lbl_new_file.configure(text="Waiting for new files...")
        self.frame_form.pack_forget()
        self.btn_process.configure(state="disabled")

    # =========================================================================
    # TAB 2: BATCH UPLOAD (THE CLEANER)
    # =========================================================================
    def setup_batch_tab(self):
        # Folder Selection
        frame_folder = ctk.CTkFrame(self.tab_batch)
        frame_folder.pack(fill="x", pady=10)
        self.entry_batch_path = ctk.CTkEntry(frame_folder, placeholder_text="Folder Path")
        self.entry_batch_path.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(frame_folder, text="Browse", command=self.browse_batch_folder).pack(side="left", padx=5)

        # Default Values
        frame_defaults = ctk.CTkFrame(self.tab_batch)
        frame_defaults.pack(fill="x", pady=10)
        ctk.CTkLabel(frame_defaults, text="Batch Defaults", font=("Arial", 14, "bold")).pack(anchor="w", padx=5)

        self.batch_defaults = {}
        defaults_to_set = ["Default Case History", "Default Sales Model", "Default Price", "Inspector Name"]

        for name in defaults_to_set:
            row = ctk.CTkFrame(frame_defaults)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=name, width=150, anchor="w").pack(side="left", padx=5)
            entry = ctk.CTkEntry(row)
            entry.pack(side="left", fill="x", expand=True, padx=5)
            self.batch_defaults[name] = entry

        # Progress
        self.progress_bar = ctk.CTkProgressBar(self.tab_batch)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=20, padx=20)

        # Start Button
        self.btn_start_batch = ctk.CTkButton(self.tab_batch, text="Start Batch Processing", command=self.start_batch)
        self.btn_start_batch.pack(pady=10)

    def browse_batch_folder(self):
        p = filedialog.askdirectory()
        if p:
            self.entry_batch_path.delete(0, "end")
            self.entry_batch_path.insert(0, p)

    def start_batch(self):
        path = self.entry_batch_path.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Invalid Folder Path")
            return

        # Disable UI
        self.btn_start_batch.configure(state="disabled")

        # Get defaults
        defaults = {k: v.get() for k, v in self.batch_defaults.items()}

        threading.Thread(target=self.run_batch_logic, args=(path, defaults)).start()

    def run_batch_logic(self, folder_path, defaults):
        files = [f for f in os.listdir(folder_path) if f.endswith(".xml")]
        total = len(files)

        if total == 0:
            self.after(0, lambda: messagebox.showinfo("Info", "No XML files found."))
            self.after(0, lambda: self.btn_start_batch.configure(state="normal"))
            return

        config = {
            "url": "https://crm.greattree.com.tw/...", # TODO: Get from shared config
            "username": "admin",
            "password": "password"
        }

        # Shared automation instance? Or new one per file?
        # New one per file is safer if they crash, but slower.
        # Single instance is faster. Let's try single instance.

        try:
            # auto = HearingAutomation(headless=True) # Silent mode
            # CHANGE: Instantiate inside loop because run_automation closes the driver.

            for i, filename in enumerate(files):
                filepath = os.path.join(folder_path, filename)

                try:
                    # 1. Parse
                    sessions = parse_noah_xml(filepath)
                    if not sessions:
                        print(f"Skipping {filename}: No sessions.")
                        continue # Or move to Failed

                    data = sessions[0]

                    # 2. Auto-match Images
                    # Look for [Mobile]_L.jpg in same folder
                    base_name = os.path.splitext(filename)[0]
                    # Logic: if filename is "PatientA.xml", look for "PatientA_L.jpg"?
                    # Prompt says: Look for `[Mobile]_L.jpg`
                    # Assuming Mobile is part of filename? Or specific pattern?
                    # "Look for [Mobile]_L.jpg / [Mobile]_R.jpg"
                    # I'll implement a simple check for matching prefix

                    l_img = os.path.join(folder_path, f"{base_name}_L.jpg")
                    if os.path.exists(l_img):
                        data["Otoscopy_Left_Image"] = l_img

                    r_img = os.path.join(folder_path, f"{base_name}_R.jpg")
                    if os.path.exists(r_img):
                        data["Otoscopy_Right_Image"] = r_img

                    # 3. Apply Defaults
                    # Merge defaults into data
                    # Map "Default Case History" -> "CaseHistory" key
                    # ...
                    data["InspectorName"] = defaults.get("Inspector Name")

                    # 4. Run Automation
                    # Create new instance for each file to ensure fresh driver
                    auto = HearingAutomation(headless=True)
                    auto.run_automation(data, filepath, config)

                except Exception as e:
                    print(f"Error processing {filename}: {e}")
                    # Move to Failed is handled inside run_automation if filepath is passed

                # Update Progress
                prog = (i + 1) / total
                self.after(0, lambda p=prog: self.progress_bar.set(p))

            self.after(0, lambda: messagebox.showinfo("Batch Complete", f"Processed {total} files."))

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Batch Error", str(e)))
        finally:
            self.after(0, lambda: self.btn_start_batch.configure(state="normal"))


class NewFileHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_created(self, event):
        if not event.is_directory:
             self.app.on_new_file_detected(event.src_path)

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    app = HearingAssessmentApp()
    app.mainloop()
