import os
import subprocess
import sys
import webbrowser
import time


def main():
    while True:
        print("\n" + "=" * 54)
        print("   MTS & DATA ENGINEERING MASTER COMMAND CENTER")
        print("=" * 54)
        print("1. Generate Hospital Equipment Quote (hospital_quote.py)")
        print("2. 3-Day Doctor Follow-Ups & CRM (leads_manager.py)")
        print("3. Scan PPRA Medical Tenders (tender_finder.py)")
        print("4. Gym PT Fee Reminders (gym_reminders.py)")
        print("5. Run Data Warehouse CI/CD ETL (run_pipeline_ci.py)")
        print("6. Launch 24/7 AI Receptionist Server (ai_receptionist.py)")
        print("0. Exit")
        print("=" * 54)

        choice = input("Select an option (0-6): ").strip()
        if choice == "1":
            subprocess.run([sys.executable, "hospital_quote.py"])
        elif choice == "2":
            subprocess.run([sys.executable, "leads_manager.py"])
        elif choice == "3":
            subprocess.run([sys.executable, "tender_finder.py"])
        elif choice == "4":
            subprocess.run([sys.executable, "gym_reminders.py"])
        elif choice == "5":
            subprocess.run([sys.executable, "run_pipeline_ci.py"])
        elif choice == "6":
            print("\nStarting 24/7 AI Receptionist at http://127.0.0.1:8000 (Press Ctrl+C to stop)...")
            webbrowser.open("http://127.0.0.1:8000")
            subprocess.run([sys.executable, "-m", "uvicorn", "ai_receptionist:app", "--reload"])
        elif choice == "0":
            print("Exiting Master Command Center.")
            break
        else:
            print("Invalid option. Please enter 0-6.")


if __name__ == "__main__":
    main()
