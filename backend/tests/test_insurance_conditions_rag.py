from dataclasses import replace

from backend.config import get_settings
from backend.rag.pdf_ingestion import PolicyPdfIngestor
from backend.rag.repository import MongoInsuranceConditionsRepository
from backend.rag.service import InsuranceConditionsRag


class FakeConditionsRepository:
    def __init__(self, rows: list[dict] | None = None, policies: list[dict] | None = None):
        self.rows = rows or []
        self.policies = policies or []
        self.search_arguments = None
        self.replacements = []

    def list_policies(self):
        return self.policies

    def replace_policy_chunks(self, policy, pdf_hash, chunks):
        self.replacements.append((policy, pdf_hash, chunks))
        return len(chunks)

    def search(self, query, category=None, policy_name=None, top_k=5):
        self.search_arguments = (query, category, policy_name, top_k)
        return self.rows[:top_k]


class FakeDownloader:
    def download(self, url):
        return {"https://storage.test/car.pdf": b"%PDF-car-v1"}[url]


class FakeChunker:
    def extract(self, pdf_bytes, policy):
        return [
            {
                "chunk_index": 0,
                "page_number": 7,
                "content": "Theft is covered when the vehicle is locked.",
                "content_hash": "content-hash",
                "source": f"{policy['name_conditions']}#page-7-chunk-0",
            }
        ]


def test_mongodb_query_contains_text_search_and_policy_filters():
    query = MongoInsuranceConditionsRepository.build_filter("theft locked vehicle", "Car", "SafeCar26.1")

    assert query == {
        "$text": {"$search": "theft locked vehicle"},
        "category": {"$regex": "^Car$", "$options": "i"},
        "name_conditions": {"$regex": "^SafeCar26\\.1$", "$options": "i"},
    }


def test_ingestion_downloads_pdf_and_writes_page_aware_chunks():
    policy = {
        "policy_mongo_id": "6963abbfaec737a82f1efd0d",
        "policy_id": 1,
        "category": "Car",
        "name_conditions": "SafeCar26.1",
        "storage_url": "https://storage.test/car.pdf",
        "indexed_pdf_hash": None,
    }
    repository = FakeConditionsRepository(policies=[policy])

    summary = PolicyPdfIngestor(repository, FakeDownloader(), FakeChunker()).run()

    assert summary.indexed == 1
    assert summary.failed == 0
    assert summary.chunks == 1
    assert repository.replacements[0][2][0]["page_number"] == 7
    assert repository.replacements[0][2][0]["source"] == "SafeCar26.1#page-7-chunk-0"


def test_ingestion_skips_unchanged_pdf():
    import hashlib

    pdf = b"%PDF-car-v1"
    policy = {
        "policy_mongo_id": "6963abbfaec737a82f1efd0d",
        "policy_id": 1,
        "category": "Car",
        "name_conditions": "SafeCar26.1",
        "storage_url": "https://storage.test/car.pdf",
        "indexed_pdf_hash": hashlib.sha256(pdf).hexdigest(),
    }
    repository = FakeConditionsRepository(policies=[policy])

    summary = PolicyPdfIngestor(repository, FakeDownloader(), FakeChunker()).run()

    assert summary.skipped == 1
    assert repository.replacements == []


def test_haystack_pipeline_returns_chunks_with_policy_and_page_citation():
    repository = FakeConditionsRepository(
        rows=[
            {
                "id": "mongo-chunk-1",
                "content": "Theft is covered when the vehicle is locked.",
                "score": 4.5,
                "policy_id": 1,
                "policy_mongo_id": "6963abbfaec737a82f1efd0d",
                "category": "Car",
                "name_conditions": "SafeCar26.1",
                "storage_url": "https://storage.test/car.pdf",
                "page_number": 7,
                "chunk_index": 0,
                "source": "SafeCar26.1#page-7-chunk-0",
            }
        ]
    )
    settings = replace(get_settings(), conditions_auto_ingest=False)
    rag = InsuranceConditionsRag(settings, repository=repository)

    matches = rag.search("is theft covered?", category="Car", policy_name="SafeCar26.1", top_k=3)

    assert repository.search_arguments == ("is theft covered?", "Car", "SafeCar26.1", 3)
    assert matches[0]["policyName"] == "SafeCar26.1"
    assert matches[0]["pageNumber"] == 7
    assert matches[0]["source"] == "SafeCar26.1#page-7-chunk-0"
