"""
analyzer.py
3개 백화점 통합 통계 분석기
stats/{store_id}/summary.json 개별 저장
stats/combined.json 통합 저장
"""

import json, re
from pathlib import Path
from datetime import datetime, timezone
from collectors import ALL_COLLECTORS

DATA_ROOT  = Path("data")
STATS_ROOT = Path("stats")
STATS_ROOT.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────
def load_runs(store_id: str) -> list[dict]:
    runs = []
    store_dir = DATA_ROOT / store_id
    if not store_dir.exists():
        return runs
    for f in sorted(store_dir.rglob("data_*.json")):
        try:
            d = json.loads(f.read_text("utf-8"))
            d["_file"] = str(f)
            runs.append(d)
        except Exception:
            pass
    return runs


def clean_price(raw: str):
    digits = re.sub(r"[^\d]", "", raw or "")
    return int(digits) if digits else None


def analyze_store(store_id: str, store_name: str) -> dict:
    runs = load_runs(store_id)
    if not runs:
        return {"store_id": store_id, "store_name": store_name, "total_runs": 0}

    all_products   = {}
    all_promotions = {}
    prod_counts, promo_counts = [], []

    for run in runs:
        ts = run.get("collected_at", "")
        prods  = run.get("products", [])
        promos = run.get("promotions", [])
        prod_counts.append(len(prods))
        promo_counts.append(len(promos))

        for p in prods:
            name = (p.get("name") or "").strip()
            if not name: continue
            price = clean_price(p.get("price",""))
            if name not in all_products:
                all_products[name] = {
                    "name": name, "price_history": [],
                    "badge": p.get("badge",""), "link": p.get("link",""),
                    "image": p.get("image",""),
                    "first_seen": ts, "last_seen": ts, "appear_count": 0,
                }
            e = all_products[name]
            e["last_seen"] = ts
            e["appear_count"] += 1
            if price: e["price_history"].append({"ts": ts, "price": price})

        for pr in promos:
            title = (pr.get("title") or "").strip()[:80]
            if not title: continue
            if title not in all_promotions:
                all_promotions[title] = {
                    "title": title, "link": pr.get("link",""),
                    "image": pr.get("image",""),
                    "first_seen": ts, "last_seen": ts, "appear_count": 0,
                }
            all_promotions[title]["last_seen"] = ts
            all_promotions[title]["appear_count"] += 1

    # 가격 변동
    price_changes = []
    for name, e in all_products.items():
        h = e["price_history"]
        if len(h) < 2: continue
        fp, lp = h[0]["price"], h[-1]["price"]
        if fp != lp:
            diff = lp - fp
            price_changes.append({
                "name": name, "first_price": fp, "last_price": lp,
                "diff": diff,
                "diff_pct": round(diff / fp * 100, 1) if fp else 0,
            })

    # 최근 3회 기준 신규
    recent_ts = sorted({r["collected_at"] for r in runs})[-3:]
    new_products   = [p for p in all_products.values()
                      if p["first_seen"] in recent_ts and p["appear_count"] <= 3]
    new_promotions = [p for p in all_promotions.values()
                      if p["first_seen"] in recent_ts and p["appear_count"] <= 3]

    top_products = sorted(all_products.values(),
                          key=lambda x: x["appear_count"], reverse=True)[:20]
    top_promos   = sorted(all_promotions.values(),
                          key=lambda x: x["appear_count"], reverse=True)

    summary = {
        "store_id":       store_id,
        "store_name":     store_name,
        "generated_at":   datetime.now(timezone.utc).astimezone().isoformat(),
        "total_runs":     len(runs),
        "first_collected": runs[0]["collected_at"],
        "last_collected":  runs[-1]["collected_at"],
        "products": {
            "unique_total":  len(all_products),
            "avg_per_run":   round(sum(prod_counts)/len(prod_counts), 1),
            "top_trending":  top_products,
            "price_changes": sorted(price_changes, key=lambda x: abs(x["diff"]), reverse=True)[:10],
            "new_products":  new_products,
        },
        "promotions": {
            "unique_total":   len(all_promotions),
            "avg_per_run":    round(sum(promo_counts)/len(promo_counts), 1),
            "all":            top_promos,
            "new_promotions": new_promotions,
        },
        "run_history": [
            {"collected_at": r["collected_at"],
             "products": len(r.get("products",[])),
             "promotions": len(r.get("promotions",[]))}
            for r in runs
        ],
    }
    return summary


# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    all_summaries = {}

    for C in ALL_COLLECTORS:
        print(f"[분석] {C.store_name}...")
        summary = analyze_store(C.store_id, C.store_name)
        all_summaries[C.store_id] = summary

        store_dir = STATS_ROOT / C.store_id
        store_dir.mkdir(exist_ok=True)
        (store_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), "utf-8"
        )
        print(f"  → 상품 {summary.get('products',{}).get('unique_total',0)}개 "
              f"/ 프로모션 {summary.get('promotions',{}).get('unique_total',0)}개")

    # 통합 저장
    combined = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "stores": all_summaries,
    }
    (STATS_ROOT / "combined.json").write_text(
        json.dumps(combined, ensure_ascii=False, indent=2), "utf-8"
    )
    print(f"\n[완료] stats/combined.json 저장")
