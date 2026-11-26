import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from backend.database import Base, make_engine
from backend.macro_repository import MacroRepository


NOW = datetime(2026, 11, 26, 15, 0, tzinfo=timezone.utc)


def result(status="available"):
    return {
        "status": status, "summary": "Pesquisa concluída.",
        "items": [{"title": "Fato", "url": "https://www.bcb.gov.br/fato", "published_at": None,
                   "confirmation": "official_confirmation", "relevance": "high",
                   "instrument_effect": "unclear", "fact_summary": "Fato confirmado.",
                   "transmission_channel": "Expectativas de juros."}] if status == "available" else [],
        "model_id": "test/model",
    }


class MacroRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.engine = make_engine(f"sqlite:///{self.tempdir.name}/macro.db")
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine, expire_on_commit=False)
        self.repo = MacroRepository(self.factory)

    def tearDown(self):
        self.engine.dispose()
        self.tempdir.cleanup()

    def save(self, instrument="WDO", status="available", completed=NOW):
        return self.repo.save_success(
            instrument, result(status), rss_evidence=[{"status": "empty", "source": "example.org"}],
            as_of=completed - timedelta(seconds=3), completed_at=completed,
            prompt_version="macro-v1",
        )

    def test_success_no_news_failure_expiry_and_instrument_isolation(self):
        first = self.save()
        self.assertEqual(self.repo.latest_usable("WDO", now=NOW)["id"], first)
        self.assertIsNone(self.repo.latest_usable("WIN", now=NOW))
        self.repo.save_failure("WDO", as_of=NOW, completed_at=NOW + timedelta(minutes=1), error_code="provider_timeout")
        self.assertEqual(self.repo.latest_usable("WDO", now=NOW + timedelta(minutes=2))["id"], first)
        second = self.save(status="no_relevant_news", completed=NOW + timedelta(minutes=3))
        self.assertEqual(self.repo.latest_usable("WDO", now=NOW + timedelta(minutes=4))["id"], second)
        self.assertEqual(self.repo.latest_usable("WDO", now=NOW + timedelta(minutes=4))["items"], [])
        self.assertIsNone(self.repo.latest_usable("WDO", now=NOW + timedelta(minutes=18)))

    def test_invalid_result_does_not_write_partial_context(self):
        with self.assertRaises(ValueError):
            self.repo.save_success("WIN", {**result(), "items": []}, rss_evidence=[], as_of=NOW, completed_at=NOW, prompt_version="macro-v1")
        self.assertIsNone(self.repo.latest_usable("WIN", now=NOW))

    def test_context_exceeding_page_fetch_budget_is_not_usable(self):
        record_id = self.save()
        with self.factory() as session:
            from backend.models import MacroExecution
            record = session.get(MacroExecution, record_id)
            record.items = record.items * 5
            session.commit()
        self.assertIsNone(self.repo.latest_usable("WDO", now=NOW))

    def test_concurrent_writers_keep_independent_immutable_records(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            ids = list(executor.map(lambda instrument: self.save(instrument), ("WIN", "WDO")))
        self.assertNotEqual(ids[0], ids[1])
        self.assertEqual(self.repo.latest_usable("WIN", now=NOW)["id"], ids[0])
        self.assertEqual(self.repo.latest_usable("WDO", now=NOW)["id"], ids[1])


class MacroMigrationTests(unittest.TestCase):
    def test_upgrade_preserves_previous_analysis_and_exposes_macro_fields(self):
        with tempfile.TemporaryDirectory() as tempdir:
            database = Path(tempdir) / "migration.db"
            config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
            with patch.dict("os.environ", {"DATABASE_URL": f"sqlite:///{database}"}):
                command.upgrade(config, "0003_analysis_snapshot")
                engine = create_engine(f"sqlite:///{database}")
                with engine.begin() as connection:
                    connection.execute(text("INSERT INTO analyses (request_id, logical_symbol, broker_symbol, state, created_at) VALUES ('old-request', 'WDO', 'WDOX26', 'no_signal', '2026-11-26 15:00:00')"))
                engine.dispose()
                command.upgrade(config, "head")
                engine = create_engine(f"sqlite:///{database}")
                with engine.connect() as connection:
                    self.assertEqual(connection.scalar(text("SELECT request_id FROM analyses")), "old-request")
                    columns = {item["name"] for item in inspect(connection).get_columns("macro_executions")}
                    self.assertTrue({"logical_symbol", "state", "items", "rss_evidence", "as_of", "completed_at", "valid_until", "model_id", "prompt_version", "error_code"} <= columns)
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
