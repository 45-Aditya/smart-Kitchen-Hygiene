import os
import subprocess
import sys
import time

# ==================== MENU-BASED MAIN CONTROLLER ====================

def clear_screen():
    """Clear console for better readability."""
    os.system('cls' if os.name == 'nt' else 'clear')
    

def show_banner():
    print("=" * 60)
    print(" 🧠 SMART KITCHEN HYGIENE MONITORING SYSTEM ")
    print("=" * 60)
    print("""
    1️⃣  Person Hygiene Detection (via Webcam)
    2️⃣  Kitchen Platform Cleanliness Detection (via Image)
    3️⃣  Vegetable Freshness Detection (via Webcam)
    4️⃣  Exit
    """)
    print("=" * 60)

def run_script(script_name):
    """Execute selected script using Python subprocess."""
    try:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
        if not os.path.exists(script_path):
            print(f"❌ Script not found: {script_name}")
            return

        print(f"\n🚀 Launching {script_name}...\n")
        time.sleep(1)
        subprocess.run([sys.executable, script_path])
    except Exception as e:
        print(f"⚠️ Error while running {script_name}: {e}")
    finally:
        input("\nPress Enter to return to main menu...")

def main():
    while True:
        clear_screen()
        show_banner()
        choice = input("👉 Select an option (1-4): ").strip()

        if choice == "1":
            run_script("person_detection.py")
        elif choice == "2":
            run_script("platform_detection.py")
        elif choice == "3":
            run_script("vegetable_detection.py")
        elif choice == "4":
            clear_screen()
            print("👋 Exiting Smart Kitchen System. Stay Hygienic!\n")
            break
        else:
            print("❌ Invalid choice! Please select 1-4.")
            time.sleep(1.5)

if __name__ == "__main__":
    main()
