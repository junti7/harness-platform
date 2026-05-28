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

# Try to find yt-dlp in the active virtualenv or virtualenv bin directory first, fallback to ~/bin/yt-dlp
possible_paths = [
    Path(__file__).parent.parent / ".venv" / "bin" / "yt-dlp",
    Path(sys.executable).parent / "yt-dlp",
    Path(os.path.expanduser("~/bin/yt-dlp")),
]
YT_DLP = str(next((p for p in possible_paths if p.exists()), Path(os.path.expanduser("~/bin/yt-dlp"))))

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "edu_youtube_transcripts"

# 교육 및 직장인 AI 불안 도메인 검색 쿼리 (글로벌/영어 포함)
DEFAULT_QUERIES = [
    "AI 교육 학부모",
    "자녀 AI 사용 부모 고민",
    "인공지능 시대 자녀 교육",
    "AI 의존 아이 교육법",
    "챗GPT 학교 숙제 부모 대처",
    "AI 시대 직장인 불안",
    "인공지능 직업 대체 직장인 고민",
    "챗GPT 직장인 생존 전략",
    "AI anxiety employees jobs",
    "artificial intelligence replacement anxiety workers",
    "generative AI education anxiety parents",
    "ChatGPT school cheating parents response",
    "AI education revolution kids",
    # Arabic (UAE & Global)
    "الذكاء الاصطناعي في التعليم قلق أولياء الأمور",
    "استبدال الوظائف بالذكاء الاصطناعي قلق الموظفين",
    "تأثير الذكاء الاصطناعي على مستقبل الوظائف دبي",
    # Hebrew (Israel)
    "חרדת הורים חינוך בינה מלאכותית",
    "בינה מלאכותית החלפת משרות חרדה",
    "אוטומציה במקום העבודה עובדים",
]



def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def search_and_collect(query: str, max_results: int = 10) -> list[dict]:
    """YouTube 검색 결과 URL 목록 수집"""
    print(f"🔍 검색: {query} (최대 {max_results}개)")
    base_cmd = [
        YT_DLP,
        f"ytsearch{max_results}:{query}",
        "--extractor-args", "youtube:player-client=ios,android,web",
        "--print", "%(id)s\t%(title)s",
        "--no-playlist",
        "--quiet",
    ]
    
    # 1. impersonate chrome을 탑재하여 최초 시도
    cmd = base_cmd.copy()
    cmd.extend(["--impersonate", "chrome"])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0 and "Impersonate target" in (result.stderr or ""):
            # impersonate 타겟 오류 발생 시, impersonate 옵션을 제외하고 재시도
            print("  ⚠️ Impersonate chrome 사용 불가. 일반 모드로 검색을 재시도합니다...")
            result = subprocess.run(base_cmd, capture_output=True, text=True, timeout=60)
            
        if result.returncode != 0:
            err_msg = (result.stderr or "").strip()
            print(f"  ⚠️ 검색 명령어 오류 (리턴코드 {result.returncode}): {err_msg[:200]}")
            return []
            
        lines = result.stdout.strip().split("\n")
        items = []
        for line in lines:
            line = line.strip()
            if "\t" not in line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                vid_id = parts[0].strip()
                title = parts[1].strip()
                if vid_id and not vid_id.startswith("WARNING"):
                    items.append({"id": vid_id, "title": title, "url": f"https://www.youtube.com/watch?v={vid_id}"})
        return items
    except subprocess.TimeoutExpired:
        print("  ⚠️ 검색 타임아웃")
        return []
    except Exception as e:
        print(f"  ⚠️ 검색 오류: {e}")
        return []

def fetch_transcript(url: str) -> dict | None:
    """비디오 자막 추출 (실패 시 info.json 설명문으로 폴백)"""
    base_cmd = [
        YT_DLP,
        url,
        "--extractor-args", "youtube:player-client=ios,android,web",
        "--write-auto-sub",
        "--sub-lang", "ko,en",
        "--sub-format", "json3",
        "--write-info-json",  # 비디오 정보 JSON 보장
        "--skip-download",
        "--sleep-requests", "2.0",
        "--sleep-interval", "5.0",
        "--max-sleep-interval", "10.0",
        "--quiet",
        "-o", str(OUTPUT_DIR / "%(id)s"),
    ]
    
    max_attempts = 3
    use_impersonate = True
    vid_id = None
    
    # URL에서 비디오 ID 사전 추출 시도
    import re
    id_match = re.search(r'(?:v=|\/v\/|embed\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', url)
    if id_match:
        vid_id = id_match.group(1)
        
    for attempt in range(1, max_attempts + 1):
        try:
            cmd = base_cmd.copy()
            if use_impersonate:
                cmd.extend(["--impersonate", "chrome"])
            if attempt == 1:
                cmd.extend(["--cookies-from-browser", "chrome"])
                
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
            if result.returncode != 0:
                err_msg = result.stderr or ""
                if use_impersonate and "Impersonate target" in err_msg:
                    print("  ⚠️ Impersonate chrome 사용 불가. 해당 옵션을 끄고 즉시 재시도합니다...")
                    use_impersonate = False
                    continue
                if attempt == 1 and ("Cookie" in err_msg or "locked" in err_msg or "Keyring" in err_msg or "Profile" in err_msg):
                    print("  ⚠️ 크롬 쿠키 로드 실패. 쿠키 없이 재시도합니다...")
                    continue
                
                if "429" in err_msg or "Too Many Requests" in err_msg:
                    backoff = 30 * attempt
                    print(f"  ⚠️ [Attempt {attempt}/{max_attempts}] YouTube HTTP 429 감지. {backoff}초 대기 후 재시도...")
                    import time
                    time.sleep(backoff)
                    continue
            break
        except subprocess.TimeoutExpired:
            print(f"  ⚠️ 타임아웃: {url}")
            return None
        except Exception as e:
            print(f"  ⚠️ 오류 ({url}): {e}")
            return None
            
    # 비디오 ID 스캔 및 info.json 탐색
    if not vid_id:
        info_files = list(OUTPUT_DIR.glob("*.info.json"))
        if info_files:
            info_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            vid_id = info_files[0].stem
        
    if not vid_id:
        print("  ⚠️ 비디오 ID 추출 실패 및 수집 데이터 없음")
        return None
        
    info_path = OUTPUT_DIR / f"{vid_id}.info.json"
    if not info_path.exists():
        matched_infos = list(OUTPUT_DIR.glob(f"*{vid_id}*.info.json"))
        if matched_infos:
            info_path = matched_infos[0]
            
    if not info_path.exists():
        print(f"  ⚠️ 메타데이터 파일 없음: {info_path.name}")
        return None
        
    # 1. info.json 파싱
    try:
        with open(info_path, encoding="utf-8") as f:
            info_data = json.load(f)
    except Exception as e:
        print(f"  ⚠️ info.json 로드 실패: {e}")
        return None
        
    title = info_data.get("title", "")
    channel = info_data.get("channel", "")
    duration = info_data.get("duration", 0)
    upload_date = info_data.get("upload_date", "")
    description = info_data.get("description", "")
    
    # 임시 info.json 제거
    try:
        info_path.unlink()
    except Exception:
        pass
        
    # 2. 자막 파싱 시도
    sub_files = list(OUTPUT_DIR.glob(f"{vid_id}.*.json3"))
    transcript_text = ""
    is_fallback = False
    
    if sub_files:
        sub_file = sub_files[0]
        try:
            with open(sub_file, encoding="utf-8") as f:
                sub_data = json.load(f)
            texts = []
            for event in sub_data.get("events", []):
                for seg in event.get("segs", []):
                    t = seg.get("utf8", "").strip()
                    if t and t != "\n":
                        texts.append(t)
            transcript_text = " ".join(texts)
        except Exception as e:
            print(f"  ⚠️ 자막 파싱 중 에러 발생: {e}")
        finally:
            try:
                sub_file.unlink()
            except Exception:
                pass
                
    # 3. 자막 부재 시 설명문(description)으로 폴백
    if len(transcript_text.strip()) < 100:
        if description and len(description.strip()) > 50:
            transcript_text = f"[자막 수집 제한에 따른 요약 설명문 대체]\n\n{description}"
            is_fallback = True
            print("    ↳ ⚠️ 자막 다운로드 차단(429 등) 감지: 영상 설명글(description) 데이터로 보완 수집합니다.")
        else:
            print("    ↳ ❌ 자막 및 설명문 모두 부재하여 스킵합니다.")
            return None
            
    return {
        "video_id": vid_id,
        "title": title,
        "channel": channel,
        "duration_sec": int(duration) if duration else 0,
        "upload_date": upload_date,
        "url": url,
        "transcript": transcript_text,
        "transcript_length": len(transcript_text),
        "collected_at": datetime.now().isoformat(),
        "domain": "edu_consulting",
        "signal_type": "youtube_transcript",
        "is_fallback": is_fallback
    }

    if not parts:
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
