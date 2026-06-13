"""APScheduler cron for daily question updates."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from config import get_settings

if TYPE_CHECKING:
    from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_daily_scheduler() -> None:
    global _scheduler
    settings = get_settings()
    if not settings.daily_questions_enabled:
        logger.info("Daily question scheduler disabled")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("APScheduler not installed — daily cron disabled")
        return

    if _scheduler is not None:
        return

    from services.daily_question_pipeline import run_daily_question_pipeline

    _scheduler = BackgroundScheduler(timezone="UTC")
    trigger = CronTrigger.from_crontab(settings.daily_questions_cron)

    _scheduler.add_job(
        run_daily_question_pipeline,
        trigger=trigger,
        id="daily_question_pipeline",
        replace_existing=True,
        kwargs={"force": False},
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info(
        "Daily question scheduler started (cron=%s UTC)",
        settings.daily_questions_cron,
    )


def stop_daily_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Daily question scheduler stopped")
