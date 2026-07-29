from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app import config as _config
from app.rag import LawRagService
from app.rag.law_source import (
    LawOpenApiClient,
    build_manifest,
    split_law,
    write_json_atomic,
)


PROJECT_DIR = Path(__file__).resolve().parents[1]
LAW_DIR = PROJECT_DIR / "data" / "laws"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="국가법령정보센터에서 현행 노동관계 법령을 동기화합니다.",
    )
    parser.add_argument("--oc", default=os.getenv("LAW_OPEN_API_OC", ""))
    parser.add_argument("--catalog", type=Path, default=LAW_DIR / "labor_law_catalog.json")
    parser.add_argument("--corpus", type=Path, default=LAW_DIR / "labor_law_corpus.json")
    parser.add_argument("--manifest", type=Path, default=LAW_DIR / "labor_law_manifest.json")
    parser.add_argument("--ingest", action="store_true", help="동기화 후 ChromaDB를 재구축합니다.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    names = json.loads(args.catalog.read_text(encoding="utf-8"))
    client = LawOpenApiClient(args.oc)
    laws = []
    records = []
    for index, name in enumerate(names, start=1):
        summary = client.find_current_law(name)
        payload = client.fetch_current_law(summary)
        chunks = split_law(summary, payload)
        if not chunks:
            raise RuntimeError(f"조문을 추출하지 못했습니다: {name}")
        laws.append(summary)
        records.extend(chunks)
        print(f"[{index}/{len(names)}] {summary.name}: {len(chunks)}개 조·항·호")

    records.sort(key=lambda item: (
        item["law_name"], item["law_id"], item["article_number"],
        item["paragraph_number"], item["item_number"], item["subitem_number"],
    ))
    manifest = build_manifest(laws, records)
    old_hash = None
    if args.manifest.exists():
        old_hash = json.loads(args.manifest.read_text(encoding="utf-8")).get("corpus_sha256")
    write_json_atomic(args.corpus, records)
    write_json_atomic(args.manifest, manifest)
    print(
        f"공식 법령 동기화 완료: {manifest['law_count']}개 법령, "
        f"{manifest['record_count']}개 조·항·호, 변경={old_hash != manifest['corpus_sha256']}"
    )
    if args.ingest:
        count = LawRagService().ingest(force=False)
        print(f"ChromaDB 재적재 완료: {count}개 레코드")


if __name__ == "__main__":
    main()
