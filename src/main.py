from src.gui import HearingAssessmentApp
import customtkinter as ctk

def main():
    ctk.set_appearance_mode("System")
    app = HearingAssessmentApp()
    app.mainloop()

if __name__ == "__main__":
    main()
