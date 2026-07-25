from dataclasses import replace
from unittest.mock import Mock

from backend.config import get_settings
from backend.rag.evaluate import EvaluationCase, evaluate_retrieval, load_cases
from backend.rag.repository import MongoInsuranceConditionsRepository
from backend.rag.retriever import MongoInsuranceConditionsRetriever


class EvaluationSearcher:
    def search(self, query, category=None, policy_name=None, top_k=5):
        if "courtesy" in query:
            return [
                {
                    "policyName": "SafeCar26.1",
                    "pageNumber": 3,
                    "content": "A replacement car is available for up to 10\nconsecutive days.",
                    "source": "SafeCar26.1#page-3-chunk-1",
                }
            ]
        return []


def test_evaluation_dataset_contains_grounded_cases_for_every_coverage_type():
    cases = load_cases()

    assert len(cases) >= 15
    assert {case.coverage_type for case in cases} == {"auto", "home", "life"}
    assert all(case.expected_pages for case in cases)
    assert all(case.required_terms for case in cases)


def test_evaluation_report_measures_page_hits_rank_and_required_terms():
    cases = [
        EvaluationCase(
            id="auto-courtesy-car",
            coverage_type="auto",
            query="Can I get a courtesy car?",
            expected_policy="SafeCar26.1",
            expected_pages=(3,),
            required_terms=("replacement", "10 consecutive days"),
        ),
        EvaluationCase(
            id="missing",
            coverage_type="home",
            query="Something absent",
            expected_policy="HomeSafe26.1",
            expected_pages=(4,),
            required_terms=("excluded",),
        ),
    ]

    report = evaluate_retrieval(EvaluationSearcher(), cases, retrieval_mode="text", top_k=3)

    assert report.hit_rate == 0.5
    assert report.mean_reciprocal_rank == 0.5
    assert report.required_term_recall == 0.6667
    assert report.cases[0].missing_terms == ()
    assert report.cases[1].retrieved_sources == ()


def test_hybrid_search_fuses_text_and_vector_rankings_with_rrf():
    repository = object.__new__(MongoInsuranceConditionsRepository)
    repository.search = Mock(
        return_value=[
            {"id": "text-first", "score": 9.0, "content": "text"},
            {"id": "shared", "score": 4.0, "content": "shared"},
        ]
    )
    repository.vector_search = Mock(
        return_value=[
            {"id": "shared", "score": 0.9, "content": "shared"},
            {"id": "vector-only", "score": 0.8, "content": "vector"},
        ]
    )

    rows = repository.hybrid_search(
        "query",
        [0.1, 0.2],
        vector_index="index",
        category="Car",
        top_k=3,
        rrf_k=60,
    )

    assert [row["id"] for row in rows] == ["shared", "text-first", "vector-only"]


class FailingHybridRepository:
    def hybrid_search(self, *args, **kwargs):
        raise RuntimeError("vector index is unavailable")

    def search(self, query, category=None, policy_name=None, top_k=5):
        return [
            {
                "id": "fallback",
                "content": "Fallback text result",
                "score": 1.0,
                "policy_id": 1,
                "policy_mongo_id": "policy",
                "category": "Car",
                "name_conditions": "SafeCar26.1",
                "storage_url": "https://example.test/policy.pdf",
                "page_number": 2,
                "chunk_index": 0,
                "source": "SafeCar26.1#page-2-chunk-0",
            }
        ]


class FakeQueryEmbedder:
    def embed_query(self, query):
        return [0.1, 0.2]


def test_hybrid_retriever_falls_back_to_text_search():
    settings = replace(get_settings(), rag_retrieval_mode="hybrid")
    retriever = MongoInsuranceConditionsRetriever(
        FailingHybridRepository(),
        settings,
        FakeQueryEmbedder(),
    )

    result = retriever.run("collision excess", category="Car", top_k=3)

    document = result["documents"][0]
    assert document.meta["retrievalMode"] == "text"
    assert document.meta["retrievalFallbackReason"] == "RuntimeError"
