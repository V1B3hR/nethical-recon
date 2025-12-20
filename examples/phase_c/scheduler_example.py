"""Example: Scheduler usage for periodic scans."""

import time

from nethical_recon.scheduler import ScanScheduler


def main():
    """Schedule periodic scans."""
    scheduler = ScanScheduler()

    # Start the scheduler
    scheduler.start()
    print("Scheduler started")

    # Schedule a periodic scan every 6 hours
    job_id = scheduler.schedule_periodic_scan(
        target="example.com",
        tools=["nmap", "nikto"],
        interval_hours=6,
        name="Example periodic scan",
    )
    print(f"Scheduled periodic scan: {job_id}")

    # Schedule a cron scan (daily at 2 AM)
    cron_job_id = scheduler.schedule_cron_scan(
        target="test.com",
        tools=["nmap"],
        cron_expression="0 2 * * *",  # minute hour day month day_of_week
        name="Daily security scan",
    )
    print(f"Scheduled cron scan: {cron_job_id}")

    # Schedule baseline updates (daily)
    baseline_job_id = scheduler.schedule_baseline_update(interval_hours=24)
    print(f"Scheduled baseline updates: {baseline_job_id}")

    # List all scheduled jobs
    print("\nScheduled jobs:")
    for job in scheduler.list_jobs():
        print(f"  - {job['name']} (ID: {job['id']})")
        print(f"    Next run: {job['next_run']}")
        print(f"    Trigger: {job['trigger']}")

    # Keep scheduler running
    print("\nScheduler is running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.shutdown()
        print("Scheduler stopped")


if __name__ == "__main__":
    main()
