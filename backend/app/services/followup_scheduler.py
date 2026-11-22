import os
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import SessionLocal
from app.core.logging import logger

scheduler = BackgroundScheduler()


def _run_followup_tick():
    from app.services.outreach_service import outreach_service

    db = SessionLocal()
    try:
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            created = loop.run_until_complete(outreach_service.process_due_followups(db, force=False))
            replies = loop.run_until_complete(outreach_service.poll_replies(db))
            if created.get("created") or replies.get("detected"):
                logger.info(f"Scheduler tick: follow-ups={created} replies={replies}")
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Follow-up scheduler tick failed: {e}")
    finally:
        db.close()


def start_scheduler():
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("DISABLE_SCHEDULER") == "1":
        logger.info("Outreach scheduler disabled in test/CI mode.")
        return
    if scheduler.running:
        return
    scheduler.add_job(_run_followup_tick, "interval", minutes=2, id="outreach_followups", replace_existing=True)
    scheduler.start()
    logger.info("Outreach follow-up scheduler started (every 2 minutes).")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Outreach follow-up scheduler stopped.")
