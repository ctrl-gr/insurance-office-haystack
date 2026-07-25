from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from backend.config import get_settings
from backend.rag.coverage_mapping import CoverageType, category_for_coverage
from backend.rag.service import InsuranceConditionsRag


DEFAULT_DATASET = Path(__file__).with_name("evaluation_cases.json")


class ConditionsSearcher(Protocol):
    def search(
        self,
        query: str,
        category: str | None = None,
        policy_name: str | None = None,
        top_k: int = 5,
    ) -> list[dict]: ...


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    coverage_type: CoverageType
    query: str
    expected_policy: str
    expected_pages: tuple[int, ...]
    required_terms: tuple[str, ...]


@dataclass(frozen=True)
class CaseResult:
    id: str
    query: str
    hit: bool
    reciprocal_rank: float
    required_terms_found: int
    required_terms_total: int
    missing_terms: tuple[str, ...]
    retrieved_sources: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationReport:
    retrieval_mode: str
    top_k: int
    total_cases: int
    hit_rate: float
    mean_reciprocal_rank: float
    required_term_recall: float
    cases: tuple[CaseResult, ...]


def load_cases(path: Path = DEFAULT_DATASET) -> list[EvaluationCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        EvaluationCase(
            id=item["id"],
            coverage_type=item["coverage_type"],
            query=item["query"],
            expected_policy=item["expected_policy"],
            expected_pages=tuple(item["expected_pages"]),
            required_terms=tuple(item.get("required_terms", [])),
        )
        for item in payload["cases"]
    ]


def evaluate_retrieval(
    searcher: ConditionsSearcher,
    cases: list[EvaluationCase],
    *,
    retrieval_mode: str,
    top_k: int = 5,
) -> EvaluationReport:
    def normalize(value: str) -> str:
        return " ".join(value.casefold().split())

    results: list[CaseResult] = []
    hit_count = 0
    reciprocal_rank_total = 0.0
    terms_found = 0
    terms_total = 0

    for case in cases:
        matches = searcher.search(
            case.query,
            category=category_for_coverage(case.coverage_type),
            policy_name=case.expected_policy,
            top_k=top_k,
        )
        expected_pages = set(case.expected_pages)
        expected_rank = next(
            (
                rank
                for rank, match in enumerate(matches, start=1)
                if match.get("policyName") == case.expected_policy
                and match.get("pageNumber") in expected_pages
            ),
            None,
        )
        hit = expected_rank is not None
        reciprocal_rank = 1 / expected_rank if expected_rank else 0.0
        retrieved_text = normalize("\n".join(str(match.get("content", "")) for match in matches))
        missing_terms = tuple(term for term in case.required_terms if normalize(term) not in retrieved_text)
        found_for_case = len(case.required_terms) - len(missing_terms)

        hit_count += int(hit)
        reciprocal_rank_total += reciprocal_rank
        terms_found += found_for_case
        terms_total += len(case.required_terms)
        results.append(
            CaseResult(
                id=case.id,
                query=case.query,
                hit=hit,
                reciprocal_rank=round(reciprocal_rank, 4),
                required_terms_found=found_for_case,
                required_terms_total=len(case.required_terms),
                missing_terms=missing_terms,
                retrieved_sources=tuple(
                    str(match["source"]) for match in matches if isinstance(match.get("source"), str)
                ),
            )
        )

    total = len(cases)
    return EvaluationReport(
        retrieval_mode=retrieval_mode,
        top_k=top_k,
        total_cases=total,
        hit_rate=round(hit_count / total, 4) if total else 0.0,
        mean_reciprocal_rank=round(reciprocal_rank_total / total, 4) if total else 0.0,
        required_term_recall=round(terms_found / terms_total, 4) if terms_total else 1.0,
        cases=tuple(results),
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate insurance-condition retrieval against grounded PDF cases.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-hit-rate", type=float, default=0.0)
    parser.add_argument("--min-term-recall", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if args.top_k < 1:
        raise SystemExit("--top-k must be at least 1")
    if not 0 <= args.min_hit_rate <= 1 or not 0 <= args.min_term_recall <= 1:
        raise SystemExit("evaluation thresholds must be between 0 and 1")

    settings = get_settings()
    report = evaluate_retrieval(
        InsuranceConditionsRag(settings),
        load_cases(args.dataset),
        retrieval_mode=settings.rag_retrieval_mode,
        top_k=args.top_k,
    )
    print(json.dumps(asdict(report), indent=2))
    if report.hit_rate < args.min_hit_rate or report.required_term_recall < args.min_term_recall:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
