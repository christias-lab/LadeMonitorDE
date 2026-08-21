from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

import psycopg
import structlog
from ladepulse_core.config import get_settings

logger = structlog.get_logger()


def run() -> None:
    settings = get_settings()
    logger.info("ingestion_worker_started", mode="synthetic_demo")
    while True:
        try:
            with psycopg.connect(settings.psycopg_dsn) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_try_advisory_xact_lock(128041)")
                    if cursor.fetchone()[0]:
                        cursor.execute(
                            """
                            SELECT id FROM source_publications
                            WHERE external_id = 'ladepulse-demo-dynamic-v1'
                            """
                        )
                        row = cursor.fetchone()
                        if row:
                            now = datetime.now(UTC)
                            cursor.execute(
                                """
                                INSERT INTO feed_health_observations (
                                  id, publication_id, observed_at, status,
                                  latency_seconds, message
                                ) VALUES (%s, %s, %s, %s, NULL, %s)
                                """,
                                (
                                    uuid.uuid4(),
                                    row[0],
                                    now,
                                    "demo_idle",
                                    "Synthetic demo worker heartbeat; no external feed polled.",
                                ),
                            )
                connection.commit()
        except Exception:
            logger.exception("ingestion_worker_heartbeat_failed")
        time.sleep(30)


if __name__ == "__main__":
    run()
