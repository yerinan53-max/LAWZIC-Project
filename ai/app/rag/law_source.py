from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


API_BASE = "https://www.law.go.kr/DRF"


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _normalize_law_name(value: str) -> str:
    return re.sub(r"[\sㆍ·]", "", value)


def _date(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}" if len(digits) >= 8 else digits


@dataclass(frozen=True)
class LawSummary:
    law_id: str
    master_id: str
    name: str
    effective_date: str
    ministry: str
    law_type: str


class LawOpenApiClient:
    def __init__(self, oc: str, timeout: float = 30):
        if not oc.strip():
            raise ValueError("LAW_OPEN_API_OC 또는 --oc 인증값이 필요합니다.")
        self.oc = oc.strip()
        self.timeout = timeout

    def _get(self, endpoint: str, **params) -> dict:
        query = urllib.parse.urlencode({"OC": self.oc, "type": "JSON", **params})
        request = urllib.request.Request(
            f"{API_BASE}/{endpoint}?{query}",
            headers={"User-Agent": "LAWZIC/1.0 (+official-law-sync)"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = response.read().decode("utf-8-sig")
        data = json.loads(payload)
        if isinstance(data, dict) and ("error" in data or "Error" in data):
            raise RuntimeError(f"국가법령정보센터 API 오류: {data}")
        return data

    def find_current_law(self, name: str) -> LawSummary:
        data = self._get(
            "lawSearch.do", target="eflaw", query=name, search=1, nw=3,
            display=100, page=1,
        )
        candidates = _as_list(data.get("LawSearch", {}).get("law"))
        expected = _normalize_law_name(name)
        exact = [
            item for item in candidates
            if _normalize_law_name(_clean(item.get("법령명한글"))) == expected
            and _clean(item.get("현행연혁코드")) == "현행"
        ]
        if not exact:
            raise LookupError(f"현행 법령을 찾지 못했습니다: {name}")
        item = sorted(exact, key=lambda value: _clean(value.get("시행일자")), reverse=True)[0]
        return LawSummary(
            law_id=_clean(item.get("법령ID")),
            master_id=_clean(item.get("법령일련번호")),
            name=_clean(item.get("법령명한글")),
            effective_date=_date(item.get("시행일자")),
            ministry=_clean(item.get("소관부처명")),
            law_type=_clean(item.get("법령구분명")),
        )

    def fetch_current_law(self, summary: LawSummary) -> dict:
        data = self._get("lawService.do", target="eflaw", ID=summary.law_id)
        if "법령" not in data:
            raise RuntimeError(f"본문 응답 형식이 올바르지 않습니다: {summary.name}")
        return data["법령"]


def _leaf_records(article: dict) -> list[tuple[str, str, str, str]]:
    article_text = _clean(article.get("조문내용"))
    paragraphs = _as_list(article.get("항"))
    if not paragraphs:
        return [("", "", "", article_text)] if article_text else []
    records: list[tuple[str, str, str, str]] = []
    for paragraph in paragraphs:
        paragraph_number = _clean(paragraph.get("항번호"))
        paragraph_text = _clean(paragraph.get("항내용"))
        items = _as_list(paragraph.get("호"))
        if not items:
            records.append((paragraph_number, "", "", paragraph_text))
            continue
        for item in items:
            item_number = _clean(item.get("호번호"))
            item_text = _clean(item.get("호내용"))
            subitems = _as_list(item.get("목"))
            if not subitems:
                records.append((paragraph_number, item_number, "", item_text))
                continue
            for subitem in subitems:
                records.append((
                    paragraph_number,
                    item_number,
                    _clean(subitem.get("목번호")),
                    _clean(subitem.get("목내용")),
                ))
    return records


def split_law(summary: LawSummary, payload: dict) -> list[dict]:
    basic = payload.get("기본정보", {})
    effective_date = _date(basic.get("시행일자")) or summary.effective_date
    source_url = f"https://www.law.go.kr/법령/{urllib.parse.quote(summary.name)}/"
    records = []
    for article in _as_list(payload.get("조문", {}).get("조문단위")):
        if _clean(article.get("조문여부")) != "조문":
            continue
        article_number = _clean(article.get("조문번호"))
        branch_number = _clean(article.get("조문가지번호"))
        display_article_number = (
            f"제{article_number}조의{branch_number}"
            if branch_number and branch_number != "0"
            else f"제{article_number}조"
        )
        path_article = (
            display_article_number
            if branch_number and branch_number != "0"
            else f"조{article_number}"
        )
        title = _clean(article.get("조문제목"))
        article_heading = _clean(article.get("조문내용"))
        for sequence, (paragraph, item, subitem, leaf_text) in enumerate(_leaf_records(article), 1):
            text_parts = [part for part in (article_heading, leaf_text) if part]
            text = "\n".join(dict.fromkeys(text_parts))
            if not text:
                continue
            path = ".".join(filter(None, (
                path_article, f"항{paragraph}", f"호{item}", f"목{subitem}",
            )))
            record_id = f"{summary.law_id}:{article.get('조문키', article_number)}:{sequence}"
            records.append({
                "id": record_id,
                "law_id": summary.law_id,
                "master_id": summary.master_id,
                "law_name": summary.name,
                "law_type": summary.law_type,
                "ministry": summary.ministry,
                "article_number": display_article_number,
                "paragraph_number": paragraph,
                "item_number": item,
                "subitem_number": subitem,
                "provision_path": path,
                "title": title,
                "effective_date": effective_date,
                "promulgation_date": _date(basic.get("공포일자")),
                "revision_type": _clean(basic.get("제개정구분")),
                "source_url": source_url,
                "text": text,
            })
    return records


def corpus_hash(records: list[dict]) -> str:
    canonical = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_manifest(laws: list[LawSummary], records: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "source": "국가법령정보센터 국가법령정보 공동활용 Open API",
        "source_url": "https://open.law.go.kr/",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "corpus_sha256": corpus_hash(records),
        "law_count": len(laws),
        "record_count": len(records),
        "laws": [
            {
                "law_id": law.law_id,
                "master_id": law.master_id,
                "law_name": law.name,
                "effective_date": law.effective_date,
                "ministry": law.ministry,
                "law_type": law.law_type,
            }
            for law in laws
        ],
    }


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
