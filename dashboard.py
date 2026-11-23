import os
import subprocess
import sys
from datetime import datetime


def run_script(script_name):
    if os.path.exists(script_name):
        subprocess.run([sys.executable, script_name])
    else:
        print(f"\n[ERROR] '{script_name}' not found in {os.getcwd()}.")


def main():
    while True:
        now_str = datetime.now().strftime("%A, %d %b %Y | %I:%M %p")
        print("\n" + "=" * 64)
        print("   MUHAMMAD MUDASIR MASOOD — DAILY BUSINESS COMMAND CENTER")
        print(f"   {now_str}")
        print("=" * 64)
        print("  1. MTS Express Hospital Quote Generator  (hospital_quote.py)")
        print("  2. MTS Doctor Leads & 3-Day Follow-Ups   (leads_manager.py)")
        print("  3. PPRA & Hospital Tender Scanner        (tender_finder.py)")
        print("  4. Gym Personal Training Fee Reminders   (gym_reminders.py)")
        print("  5. MTS Data Warehouse & SQL Analytics    (de_etl_lab.py)")
        print("  6. Exit")
        print("=" * 64)

        choice = input("Select an operation (1-6): ").strip()

        if choice == "1":
            run_script("hospital_quote.py")
        elif choice == "2":
            run_script("leads_manager.py")
        elif choice == "3":
            run_script("tender_finder.py")
        elif choice == "4":
            run_script("gym_reminders.py")
        elif choice == "5":
            run_script("de_etl_lab.py")
        elif choice == "6":
            print("\nHave a productive day! Closing Command Center.")
            break
        else:
            print("\nInvalid option. Please enter 1, 2, 3, 4, 5, or 6.")


if __name__ == "__main__":
    main()
