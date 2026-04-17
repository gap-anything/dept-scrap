"""
collector_main.py
3개 백화점 수집 메인 진입점
"""

import argparse
import concurrent.futures
from collectors import ALL_COLLECTORS


def run_one(CollectorClass, headless: bool) -> dict:
    c = CollectorClass()
    result = c.collect(headless=headless)
    c.save(result)
    return result


def main():
    ap = argparse.ArgumentParser(description="3개 백화점 통합 수집기")
    ap.add_argument("--store",    choices=["shinsegae","hyundai","lotte","all"], default="all")
    ap.add_argument("--parallel", action="store_true", help="3개 동시 수집 (GitHub Actions 권장)")
    ap.add_argument("--show",     action="store_true", help="브라우저 창 표시 (로컬 디버그용)")
    args = ap.parse_args()

    headless = not args.show

    # 수집 대상 필터링
    targets = [C for C in ALL_COLLECTORS
               if args.store == "all" or C.store_id == args.store]

    if not targets:
        print("[오류] 지정한 store가 없습니다")
        return

    print(f"=== 수집 시작 — 대상: {[C.store_name for C in targets]} ===\n")

    if args.parallel and len(targets) > 1:
        # 병렬 수집 (GitHub Actions에서 시간 절약)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            futures = {ex.submit(run_one, C, headless): C.store_name for C in targets}
            for fut in concurrent.futures.as_completed(futures):
                name = futures[fut]
                try:
                    r = fut.result()
                    status = "성공" if not r.get("error") else f"실패: {r['error']}"
                    print(f"[{name}] → {status}")
                except Exception as e:
                    print(f"[{name}] → 예외: {e}")
    else:
        # 순차 수집 (안정적, 로컬 디버그 기본)
        for C in targets:
            run_one(C, headless)

    print("\n=== 수집 완료 ===")


if __name__ == "__main__":
    main()
