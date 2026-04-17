"""
collectors/base.py
공통 베이스 수집기 — 모든 백화점 수집기가 이 클래스를 상속합니다.
"""

from __future__ import annotations
import json, csv
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, BrowserContext


# 사람처럼 보이는 공통 User-Agent
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class BaseCollector(ABC):
    """
    서브클래스에서 반드시 정의해야 할 것:
        store_id   : str  — 'shinsegae' | 'hyundai' | 'lotte'
        store_name : str  — '신세계V' | '현대백화점' | '롯데온'
        base_url   : str  — 수집 대상 URL
    
    오버라이드 가능:
        extra_setup(page)      — 팝업 닫기, 쿠키 동의 등 사이트별 전처리
        product_selectors()    — 상품 카드 CSS 셀렉터 목록
        promotion_selectors()  — 프로모션/배너 CSS 셀렉터 목록
        parse_product(el)      — 셀렉터로 못 잡는 경우 커스텀 파싱
        parse_promotion(el)    — 셀렉터로 못 잡는 경우 커스텀 파싱
    """

    store_id:   str = ""
    store_name: str = ""
    base_url:   str = ""

    # 스크롤 설정
    scroll_step_px:  int = 600
    scroll_delay_ms: int = 250
    after_load_ms:   int = 2500

    DATA_ROOT  = Path("data")
    STATS_ROOT = Path("stats")

    # ── 공통 셀렉터 (사이트별로 오버라이드) ──────────────────────
    def product_selectors(self) -> list[str]:
        return [
            ".product-item", ".goods-item", ".item-wrap", ".prd-item",
            "[class*='product-card']", "[class*='goods-card']",
            "[class*='item-card']", "[class*='ProductCard']",
        ]

    def promotion_selectors(self) -> list[str]:
        return [
            "[class*='banner']", "[class*='Banner']",
            "[class*='promo']",  "[class*='Promo']",
            "[class*='event']",  "[class*='Event']",
            "[class*='slide']",  ".swiper-slide",
            "[class*='hero']",   "[class*='Hero']",
            "[class*='visual']", "[class*='Visual']",
        ]

    # ── 사이트별 전처리 훅 ───────────────────────────────────────
    def extra_setup(self, page: Page) -> None:
        """팝업 닫기, 쿠키 동의 등 — 필요 시 서브클래스에서 오버라이드"""
        pass

    # ── 메인 수집 ────────────────────────────────────────────────
    def collect(self, headless: bool = True) -> dict:
        now = datetime.now(timezone.utc).astimezone()
        result = {
            "store_id":     self.store_id,
            "store_name":   self.store_name,
            "collected_at": now.isoformat(),
            "url":          self.base_url,
            "promotions":   [],
            "products":     [],
            "error":        None,
        }

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless)
                ctx = self._make_context(browser)
                page = ctx.new_page()

                print(f"[{self.store_name}] 접속 중... {self.base_url}")
                page.goto(self.base_url, wait_until="networkidle", timeout=35_000)
                page.wait_for_timeout(self.after_load_ms)

                self.extra_setup(page)
                self._scroll(page)

                result["promotions"] = self._collect_promotions(page)
                result["products"]   = self._collect_products(page)

                # 스크린샷
                shot_path = self._shot_path(now)
                shot_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(shot_path), full_page=True)
                result["screenshot"] = str(shot_path)

                browser.close()

        except Exception as e:
            result["error"] = str(e)
            print(f"[{self.store_name}] 수집 실패: {e}")

        promo_cnt = len(result["promotions"])
        prod_cnt  = len(result["products"])
        print(f"[{self.store_name}] 완료 — 프로모션 {promo_cnt}건 / 상품 {prod_cnt}건")
        return result

    # ── 저장 ─────────────────────────────────────────────────────
    def save(self, result: dict) -> Path:
        now     = datetime.fromisoformat(result["collected_at"])
        day_dir = self.DATA_ROOT / self.store_id / now.strftime("%Y/%m/%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        ts = now.strftime("%H%M")

        json_path = day_dir / f"data_{ts}.json"
        json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")

        if result["products"]:
            with open(day_dir / f"products_{ts}.csv", "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=["name","price","original_price","badge","link","image"], extrasaction="ignore")
                w.writeheader(); w.writerows(result["products"])

        if result["promotions"]:
            with open(day_dir / f"promotions_{ts}.csv", "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=["title","full_text","link","image"], extrasaction="ignore")
                w.writeheader(); w.writerows(result["promotions"])

        print(f"[{self.store_name}] 저장 → {json_path}")
        return json_path

    # ── 내부 헬퍼 ────────────────────────────────────────────────
    def _make_context(self, browser) -> BrowserContext:
        return browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=USER_AGENT,
            locale="ko-KR",
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9",
                "Referer": self.base_url,
            },
        )

    def _scroll(self, page: Page) -> None:
        h = page.evaluate("document.body.scrollHeight")
        for pos in range(0, h + self.scroll_step_px, self.scroll_step_px):
            page.evaluate(f"window.scrollTo(0, {pos})")
            page.wait_for_timeout(self.scroll_delay_ms)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

    def _shot_path(self, now: datetime) -> Path:
        return (
            self.DATA_ROOT / self.store_id
            / now.strftime("%Y/%m/%d")
            / f"screenshot_{now.strftime('%H%M')}.png"
        )

    def _collect_promotions(self, page: Page) -> list[dict]:
        items, seen = [], set()
        for sel in self.promotion_selectors():
            for el in page.query_selector_all(sel):
                try:
                    text  = (el.inner_text() or "").strip()[:200]
                    href  = el.get_attribute("href") or ""
                    title = _find_text(el, ["h1","h2","h3","h4","strong",
                                            ".title",".name","[class*='title']"])
                    img   = _first_img(el)
                    if not (text or title):
                        continue
                    key = (title or text)[:60]
                    if key in seen:
                        continue
                    seen.add(key)
                    items.append({
                        "title":     title or text[:60],
                        "full_text": text,
                        "link":      self._abs(href),
                        "image":     img,
                        "selector":  sel,
                    })
                except Exception:
                    pass
        return items

    def _collect_products(self, page: Page) -> list[dict]:
        items, seen = [], set()
        for sel in self.product_selectors():
            for el in page.query_selector_all(sel):
                try:
                    name  = _find_text(el, [
                        ".prd-name",".goods-name",".product-name",
                        ".name","[class*='name']","strong","h3","h4",
                    ])
                    price = _find_text(el, [
                        ".price",".prd-price","[class*='price']",
                        "[class*='Price']",
                    ])
                    badge = _find_text(el, [
                        ".badge",".label","[class*='badge']","[class*='tag']",
                    ])
                    orig  = _find_text(el, [
                        ".original-price","del","s","[class*='origin']",
                    ])
                    link_a = el.query_selector("a")
                    href   = link_a.get_attribute("href") if link_a else ""
                    img    = _first_img(el)

                    if not name:
                        continue
                    key = name[:40]
                    if key in seen:
                        continue
                    seen.add(key)
                    items.append({
                        "name": name, "price": price,
                        "original_price": orig, "badge": badge,
                        "link": self._abs(href), "image": img,
                    })
                except Exception:
                    pass
        return items

    def _abs(self, href: str) -> str:
        if not href: return ""
        if href.startswith("http"): return href
        if href.startswith("//"): return "https:" + href
        base = self.base_url.rstrip("/")
        return base + href if href.startswith("/") else href


# ── 유틸 함수 ────────────────────────────────────────────────────

def _find_text(el, selectors: list[str]) -> str:
    for s in selectors:
        try:
            found = el.query_selector(s)
            if found:
                t = found.inner_text().strip()
                if t:
                    return t
        except Exception:
            pass
    return ""

def _first_img(el) -> str:
    try:
        img = el.query_selector("img")
        if img:
            src = (img.get_attribute("src")
                   or img.get_attribute("data-src")
                   or img.get_attribute("data-lazy")
                   or "")
            return src if src.startswith("http") else ("https:" + src if src.startswith("//") else src)
    except Exception:
        pass
    return ""
