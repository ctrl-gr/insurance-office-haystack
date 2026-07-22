from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from io import BytesIO

import httpx
from haystack import Document
from haystack.components.preprocessors import DocumentSplitter
from pypdf import PdfReader

from backend.config import Settings, get_settings
from .repository import MongoInsuranceConditionsRepository


class PdfDownloader:
    def __init__(self, timeout_seconds: float, max_bytes: int, bearer_token: str | None = None):
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.headers = {"Authorization": f"Bearer {bearer_token}"} if bearer_token else {}

    def download(self, url: str) -> bytes:
        with httpx.Client(follow_redirects=True, timeout=self.timeout_seconds, headers=self.headers) as client:
            response = client.get(url)
            response.raise_for_status()
        content = response.content
        if len(content) > self.max_bytes:
            raise ValueError(f"PDF exceeds maximum size of {self.max_bytes} bytes")
        if not content.startswith(b"%PDF"):
            raise ValueError("storage_url did not return a PDF document")
        return content


class PdfChunker:
    def __init__(self, chunk_size_words: int, chunk_overlap_words: int):
        if chunk_overlap_words >= chunk_size_words:
            raise ValueError("RAG chunk overlap must be smaller than chunk size")
        self.splitter = DocumentSplitter(
            split_by="word",
            split_length=chunk_size_words,
            split_overlap=chunk_overlap_words,
        )
        self.splitter.warm_up()

    def extract(self, pdf_bytes: bytes, policy: dict) -> list[dict]:
        reader = PdfReader(BytesIO(pdf_bytes))
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(Document(content=text, meta={"page_number": page_number}))
        if not pages:
            raise ValueError("PDF contains no extractable text; OCR is required")

        split_result = self.splitter.run(documents=pages)
        chunks = []
        for chunk_index, document in enumerate(split_result["documents"]):
            content = (document.content or "").strip()
            if not content:
                continue
            page_number = int(document.meta["page_number"])
            source = f"{policy['name_conditions']}#page-{page_number}-chunk-{chunk_index}"
            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "page_number": page_number,
                    "content": content,
                    "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    "source": source,
                }
            )
        return chunks


@dataclass(frozen=True)
class IngestionSummary:
    indexed: int
    skipped: int
    failed: int
    chunks: int
    results: list[dict]


class PolicyPdfIngestor:
    def __init__(
        self,
        repository: MongoInsuranceConditionsRepository,
        downloader: PdfDownloader,
        chunker: PdfChunker,
    ):
        self.repository = repository
        self.downloader = downloader
        self.chunker = chunker

    def run(self) -> IngestionSummary:
        indexed = skipped = failed = total_chunks = 0
        results = []
        for policy in self.repository.list_policies():
            try:
                pdf_bytes = self.downloader.download(policy["storage_url"])
                pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
                if policy.get("indexed_pdf_hash") == pdf_hash:
                    skipped += 1
                    results.append({"policy": policy["name_conditions"], "status": "skipped"})
                    continue
                chunks = self.chunker.extract(pdf_bytes, policy)
                count = self.repository.replace_policy_chunks(policy, pdf_hash, chunks)
                indexed += 1
                total_chunks += count
                results.append({"policy": policy["name_conditions"], "status": "indexed", "chunks": count})
            except Exception as error:
                failed += 1
                results.append(
                    {
                        "policy": policy.get("name_conditions", "unknown"),
                        "status": "failed",
                        "error": str(error),
                    }
                )
        return IngestionSummary(indexed, skipped, failed, total_chunks, results)


def build_ingestor(settings: Settings, repository: MongoInsuranceConditionsRepository | None = None) -> PolicyPdfIngestor:
    repository = repository or MongoInsuranceConditionsRepository(
        settings.mongodb_uri,
        settings.mongodb_database,
        settings.mongodb_policies_collection,
        settings.mongodb_chunks_collection,
        settings.mongodb_server_selection_timeout_ms,
    )
    return PolicyPdfIngestor(
        repository,
        PdfDownloader(
            settings.pdf_download_timeout_seconds,
            settings.pdf_max_bytes,
            settings.pdf_storage_bearer_token,
        ),
        PdfChunker(settings.rag_chunk_size_words, settings.rag_chunk_overlap_words),
    )


def main() -> None:
    summary = build_ingestor(get_settings()).run()
    print(json.dumps(summary.__dict__, indent=2))
    if summary.failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
