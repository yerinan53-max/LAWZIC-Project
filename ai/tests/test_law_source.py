import json
from pathlib import Path

from app.rag.law_source import LawSummary, corpus_hash, split_law


def test_official_law_payload_is_split_by_article_paragraph_item_and_subitem():
    summary = LawSummary(
        law_id="001872",
        master_id="265959",
        name="근로기준법",
        effective_date="2025-10-23",
        ministry="고용노동부",
        law_type="법률",
    )
    payload = {
        "기본정보": {
            "시행일자": "20251023",
            "공포일자": "20241022",
            "제개정구분": "일부개정",
        },
        "조문": {
            "조문단위": [{
                "조문번호": "2",
                "조문가지번호": "0",
                "조문키": "0002001",
                "조문여부": "조문",
                "조문제목": "정의",
                "조문내용": "제2조(정의)",
                "항": [{
                    "항번호": "①",
                    "항내용": "① 이 법에서 사용하는 용어의 뜻은 다음과 같다.",
                    "호": [{
                        "호번호": "1.",
                        "호내용": "1. 근로자란 임금을 목적으로 근로를 제공하는 사람이다.",
                        "목": [
                            {"목번호": "가.", "목내용": "가. 예시 세부 기준"},
                            {"목번호": "나.", "목내용": "나. 다른 세부 기준"},
                        ],
                    }],
                }],
            }],
        },
    }

    records = split_law(summary, payload)

    assert len(records) == 2
    assert records[0]["law_name"] == "근로기준법"
    assert records[0]["article_number"] == "제2조"
    assert records[0]["paragraph_number"] == "①"
    assert records[0]["item_number"] == "1."
    assert records[0]["subitem_number"] == "가."
    assert records[0]["provision_path"] == "조2.항①.호1..목가."
    assert records[0]["effective_date"] == "2025-10-23"
    assert records[0]["source_url"].startswith("https://www.law.go.kr/")


def test_corpus_hash_is_stable_for_same_records():
    records = [{"id": "1", "law_name": "근로기준법", "text": "본문"}]
    assert corpus_hash(records) == corpus_hash(list(records))


def test_checked_in_official_corpus_matches_manifest():
    law_dir = Path(__file__).parents[1] / "data" / "laws"
    records = json.loads((law_dir / "labor_law_corpus.json").read_text(encoding="utf-8"))
    manifest = json.loads((law_dir / "labor_law_manifest.json").read_text(encoding="utf-8"))

    assert manifest["source"].startswith("국가법령정보센터")
    assert manifest["law_count"] == 45
    assert manifest["record_count"] == len(records)
    assert len(records) >= 10_000
    assert len({record["id"] for record in records}) == len(records)
    assert corpus_hash(records) == manifest["corpus_sha256"]
    assert all(record["effective_date"] for record in records)
    assert all(record["source_url"].startswith("https://www.law.go.kr/") for record in records)
