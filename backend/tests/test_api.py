from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.app.api as api_module
from backend.app.db import Base


class APITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "api_test.db"
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        self.testing_session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.testing_session()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_health(self) -> None:
        self.assertEqual(api_module.health(), {"status": "ok"})

    def test_invalid_ticker_rejected(self) -> None:
        with self.assertRaises(HTTPException) as context:
            api_module.create_analysis(
                ticker="INVALID_TOO_LONG",
                background_tasks=BackgroundTasks(),
                db=self.db,
            )
        self.assertEqual(context.exception.status_code, 400)

    def test_create_and_fetch_analysis(self) -> None:
        created = api_module.create_analysis(
            ticker="AAPL",
            background_tasks=BackgroundTasks(),
            db=self.db,
        )
        self.assertEqual(created.ticker, "AAPL")
        self.assertEqual(created.status, "queued")

        fetched = api_module.get_analysis(run_id=created.run_id, db=self.db)
        self.assertEqual(fetched.run_id, created.run_id)
        self.assertEqual(fetched.ticker, "AAPL")
        self.assertEqual(fetched.status, "queued")
        self.assertIsNone(fetched.result)

    def test_list_analyses_returns_created_run(self) -> None:
        api_module.create_analysis(
            ticker="NVDA",
            background_tasks=BackgroundTasks(),
            db=self.db,
        )
        rows = api_module.list_analyses(limit=10, db=self.db)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].ticker, "NVDA")


if __name__ == "__main__":
    unittest.main()
