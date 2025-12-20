"""Example: Basic worker queue usage."""

from nethical_recon.core.models import ScanJob, Target, TargetScope, TargetType
from nethical_recon.core.storage import init_database
from nethical_recon.core.storage.repository import ScanJobRepository, TargetRepository
from nethical_recon.worker.tasks import run_scan_job


def main():
    """Submit a job to the worker queue."""
    # Initialize database
    db = init_database()

    with db.session() as session:
        target_repo = TargetRepository(session)
        job_repo = ScanJobRepository(session)

        # Create target
        target = Target(
            value="example.com",
            type=TargetType.DOMAIN,
            scope=TargetScope.IN_SCOPE,
            tags=["example", "test"],
        )
        target = target_repo.create(target)

        # Create scan job
        job = ScanJob(
            target_id=target.id,
            name="Example scan",
            description="Basic example of worker queue usage",
            tools=["nmap", "nikto"],
        )
        job = job_repo.create(job)
        session.commit()

        print(f"Created job: {job.id}")

        # Submit to worker queue (requires Redis and Celery worker running)
        # task = run_scan_job.delay(str(job.id))
        # print(f"Submitted task: {task.id}")

        print("\nTo execute this job:")
        print("1. Start Redis: redis-server")
        print("2. Start Celery worker: celery -A nethical_recon.worker.celery_app worker --loglevel=info")
        print("3. Uncomment the task submission lines above and run again")


if __name__ == "__main__":
    main()
