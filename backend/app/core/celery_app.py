from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "wa_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.whatsapp_tasks", "app.tasks.ai_tasks", "app.tasks.followup_tasks"]
)
celery_app.set_default()

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'check-stale-leads-every-hour': {
        'task': 'followup.check_stale_leads',
        'schedule': crontab(minute=0, hour='*'),
    },
    'send-group-promos-every-30-minutes': {
        'task': 'followup.send_group_promos',
        'schedule': crontab(minute='*/30'),
    },
}
