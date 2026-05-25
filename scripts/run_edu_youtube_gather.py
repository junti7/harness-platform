#!/usr/bin/env python3
"""
run_edu_youtube_gather.py — AR-034
교육 컨설팅 도메인 YouTube 자막 수집 파이프라인 (Mac Mini용)

사용법:
  python3 scripts/run_edu_youtube_gather.py --query "AI 교육 학부모" --max 10
  python3 scripts/run_edu_youtube_gather.py --url "https://youtube.com/watch?v=XXX"
  python3 scripts/run_edu_youtube_gather.py --playlist "https://youtube.com/playlist?list=XXX"

출력: data/edu_youtube_transcripts/YYYYMMDD_<video_id>.json
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

YT_DLP = os.path.expanduser("~/bin/yt-dlp")
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "edu_youtube_transcripts"

# 교육 컨설팅 기본 검색 쿼리 (학부모 AI 불안 도메인)
DEFAULT_QUERIES = [
    "AI 교육 학부모",
    "자녀 AI 사용 부모 고민",
    "인공지능 시대 자녀 교육",
    "AI 의존 아이 교육법",
    "챗GPT 학교 숙제 부모 대처",
]

def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def search_and_collect(query: str, max_results: int = 10) -> list[dict]:
    """YouTube 검색 결과 URL 목록 수집"""
    print(f"🔍 검색: {query} (최대 {max_results}개)")
    cmd = [
        YT_DLP,
        f"ytsearch{max_results}:{query}",
        "--get-id",
        "--get-title",
        "--no-playlist",
        "--quiet",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        lines = result.stdout.strip().split("\n")
        # yt-dlp --get-id --get-title: id와 title이 번갈아 출력
        items = []
        for i in range(0, len(lines) - 1, 2):
            vid_id = lines[i].strip()
            title = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if vid_id:
                items.append({"id": vid_id, "title": title, "url": f"https://www.youtube.com/watch?v={vid_id}"})
        return items
    except subprocess.TimeoutExpired:
        print("  ⚠️ 검색 타임아웃")
        return []
    except Exception as e:
        print(f"  ⚠️ 검색 오류: {e}")
        return []

def fetch_transcript(url: str) -> dict | None:
    """자막(한국어 우선, 없으면 영어) 추출"""
    cmd = [
        YT_DLP,
        url,
        "--write-auto-sub",
        "--sub-lang", "ko,en",
        "--sub-format", "json3",
        "--skip-download",
        "--print", "%(id)s\t%(title)s\t%(duration)s\t%(upload_date)s\t%(channel)s",
        "--quiet",
        "-o", str(OUTPUT_DIR / "%(id)s"),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return None

        meta_line = result.stdout.strip().split("\n")[-1]
        parts = meta_line.split("\t")
        if len(parts) < 5:
            return None

        vid_id, title, duration, upload_date, channel = parts[:5]

        # 자막 파일 찾기
        sub_files = list(OUTPUT_DIR.glob(f"{vid_id}.*.json3"))
        transcript_text = ""
        if sub_files:
            sub_file = sub_files[0]
            with open(sub_file) as f:
                sub_data = json.load(f)
            # json3 포맷: events[].segs[].utf8
            texts = []
            for event in sub_data.get("events", []):
                for seg in event.get("segs", []):
                    t = seg.get("utf8", "").strip()
                    if t and t != "\n":
                        texts.append(t)
            transcript_text = " ".join(texts)
            sub_file.unlink()  # 원본 json3 삭제 (통합 JSON에 저장)

        return {
            "video_id": vid_id,
            "title": title,
            "channel": channel,
            "duration_sec": int(duration) if duration.isdigit() else 0,
            "upload_date": upload_date,
            "url": url,
            "transcript": transcript_text,
            "transcript_length": len(transcript_text),
            "collected_at": datetime.now().isoformat(),
            "domain": "edu_consulting",
            "signal_type": "youtube_transcript",
        }
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ 타임아웃: {url}")
        return None
    except Exception as e:
        print(f"  ⚠️ 오류 ({url}): {e}")
        return None

def save_result(data: dict):
    date_str = datetime.now().strftime("%Y%m%d")
    out_path = OUTPUT_DIR / f"{date_str}_{data['video_id']}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 저장: {out_path.name} ({data['transcript_length']}자)")

def run_query_mode(query: str, max_results: int):
    ensure_dirs()
    items = search_and_collect(query, max_results)
    print(f"  → {len(items)}개 영상 발견")
    saved = 0
    for item in items:
        print(f"  📹 {item['title'][:50]}")
        data = fetch_transcript(item["url"])
        if data and data["transcript_length"] > 100:
            save_result(data)
            saved += 1
        else:
            print("    ↳ 자막 없음 또는 너무 짧음 — 스킵")
    print(f"\n완료: {saved}/{len(items)}개 저장 → {OUTPUT_DIR}")

def run_url_mode(url: str):
    ensure_dirs()
    print(f"📹 단일 영상: {url}")
    data = fetch_transcript(url)
    if data:
        save_result(data)
    else:
        print("  ❌ 자막 추출 실패")

def run_batch_mode(max_per_query: int):
    """기본 쿼리 목록 전체 실행"""
    ensure_dirs()
    total = 0
    for query in DEFAULT_QUERIES:
        items = search_and_collect(query, max_per_query)
        for item in items:
            data = fetch_transcript(item["url"])
            if data and data["transcript_length"] > 100:
                save_result(data)
                total += 1
    print(f"\n배치 완료: 총 {total}개 수집 → {OUTPUT_DIR}")

def main():
    parser = argparse.ArgumentParser(description="YouTube 교육 자막 수집 (AR-034)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--query", help="검색 쿼리")
    group.add_argument("--url", help="단일 YouTube URL")
    group.add_argument("--batch", action="store_true", help="기본 쿼리 목록 전체 실행")
    parser.add_argument("--max", type=int, default=10, help="쿼리당 최대 수집 수 (기본: 10)")
    args = parser.parse_args()

    if not Path(YT_DLP).exists():
        print(f"❌ yt-dlp를 찾을 수 없습니다: {YT_DLP}")
        print("   설치: pip3 install yt-dlp --user")
        sys.exit(1)

    if args.url:
        run_url_mode(args.url)
    elif args.batch:
        run_batch_mode(args.max)
    elif args.query:
        run_query_mode(args.query, args.max)
    else:
        parser.print_help()
        print("\n기본 쿼리로 배치 실행하려면: --batch")

if __name__ == "__main__":
    main()
