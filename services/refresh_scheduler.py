"""Background scheduler for automatic database refresh"""
import schedule
import time
import threading
from datetime import datetime
import pytz
from services.sp500_importer import fetch_and_import_sp500
from services.macro_importer import refresh_all_macro_data

# US Eastern timezone
ET = pytz.timezone('US/Eastern')


def is_market_hours() -> bool:
    """Check if current time is during US market hours (9:30 AM - 4:00 PM ET)"""
    now_et = datetime.now(ET)
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)

    is_weekday = now_et.weekday() < 5
    is_open = market_open <= now_et <= market_close
    return is_weekday and is_open


def refresh_job():
    """Execute database refresh"""
    try:
        print(f"\nStarting scheduled refresh at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
        stock_count = fetch_and_import_sp500()
        macro_counts = refresh_all_macro_data()
        if stock_count > 0:
            print(f"Refresh complete: {stock_count} stocks updated")
        else:
            print("Refresh returned 0 stocks")

        print(f"✅ Indices: {macro_counts.get('indices', 0)} updated")
        print(f"✅ Indicators: {macro_counts.get('indicators', 0)} updated")
        print(f"✅ Alternative assets: {macro_counts.get('assets', 0)} updated")
    except Exception as e:
        print(f"Refresh failed: {e}")


def schedule_refresh():
    """Set up refresh schedule"""
    # During market hours: every 15 minutes
    schedule.every(15).minutes.do(lambda: refresh_job() if is_market_hours() else None)

    # Outside market hours: every hour
    schedule.every().hour.do(lambda: refresh_job() if not is_market_hours() else None)

    print("Refresh scheduler initialized")
    print("   - Market hours (Mon-Fri 9:30 AM - 4:00 PM ET): Every 15 minutes")
    print("   - Outside market hours: Every hour")


def run_scheduler():
    """Run the scheduler in a loop"""
    while True:
        schedule.run_pending()
        time.sleep(30)


def start_scheduler_background():
    """Start scheduler in background thread"""
    schedule_refresh()

    # Run initial refresh immediately
    print("\nRunning initial database refresh...")
    refresh_job()

    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("Background scheduler started\n")

