import schedule
import time
import threading
from send_expiry import main as send_expiry_notifications


def run_scheduler():
    """Run the scheduler in a separate thread"""
    # Schedule to run daily at 9 AM
    schedule.every().day.at("09:00").do(send_expiry_notifications)
    
    print("Scheduler started. Will check for expiring products daily at 9 AM.")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def start_scheduler():
    """Start scheduler in background thread"""
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    return scheduler_thread

if __name__ == "__main__":
    # For testing - run immediately
    print("Running expiry check...")
    send_expiry_notifications()
    
    # Then start scheduler
    run_scheduler()