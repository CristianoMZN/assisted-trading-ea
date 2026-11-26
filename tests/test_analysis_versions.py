import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.prompts import version_records
from backend.repository import AnalysisRepository


class AnalysisVersionPersistenceTests(unittest.TestCase):
    def test_analysis_versions_are_recovered_with_result(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        repository = AnalysisRepository(sessionmaker(engine, expire_on_commit=False), retention_days=30)
        request = {
            "request_id": "123e4567-e89b-42d3-a456-426614174099",
            "instrument": {"logical_symbol": "WDO", "broker_symbol": "WDOZ26"},
            "preferences": {"risk_reward": "1:2"},
        }
        response = {
            "schema_version": "1.1",
            "message_type": "error",
            "request_id": request["request_id"],
            "error": {"code": "analysis_unavailable", "message": "Analysis unavailable."},
        }
        repository.save(request, response, versions=version_records())
        recovered = repository.get(request["request_id"])
        self.assertEqual(recovered["state"], "failed")
        self.assertEqual(
            {item["component"]: item["version"] for item in recovered["versions"]},
            {item["component"]: item["version"] for item in version_records()},
        )
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
