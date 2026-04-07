import threading
import time
import datetime
from .services import sync_softone_products, sync_softone_stock

def run_sync_task():
    """
    Διενεργεί πλήρη συγχρονισμό προϊόντων και αποθέματος.
    """
    print(f"[{datetime.datetime.now()}] 🕒 Ξεκινάει ο προγραμματισμένος συγχρονισμός (8:00 AM)...")
    try:
        new_count = sync_softone_products()
        print(f"[{datetime.datetime.now()}] ✅ Συγχρονισμός προϊόντων: {new_count} νέα προιόντα.")
        
        updated_stock = sync_softone_stock()
        print(f"[{datetime.datetime.now()}] ✅ Συγχρονισμός αποθέματος: {updated_stock} ενημερώσεις.")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] ❌ Σφάλμα στον προγραμματισμένο συγχρονισμό: {e}")

def scheduler_loop():
    """
    Κύριος βρόχος που ελέγχει την ώρα και εκτελεί το task στις 8:00 πμ.
    """
    print("🚀 Background Scheduler started.")
    last_run_date = None
    
    while True:
        now = datetime.datetime.now()
        
        # Έλεγχος αν είναι 8:00 πμ και αν δεν έχει τρέξει ήδη σήμερα
        if now.hour == 8 and now.minute == 0 and last_run_date != now.date():
            run_sync_task()
            last_run_date = now.date()
            
        # Περιμένουμε 30 δευτερόλεπτα πριν τον επόμενο έλεγχο
        time.sleep(30)

def start_scheduler():
    """
    Ξεκινάει τον scheduler σε ξεχωριστό thread.
    """
    # Αποφυγή διπλής εκτέλεσης αν το Flask τρέχει σε debug mode (reloader)
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not os.environ.get('FLASK_DEBUG'):
        thread = threading.Thread(target=scheduler_loop, daemon=True)
        thread.start()
    elif os.environ.get('WERKZEUG_RUN_MAIN') is None:
        # Σε περίπτωση που δεν τρέχει μέσω werkzeug but directly (π.χ. production)
        thread = threading.Thread(target=scheduler_loop, daemon=True)
        thread.start()
