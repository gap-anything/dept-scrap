"""collectors/hyundai.py — 현대백화점 Hi!"""
from collectors.base import BaseCollector, USER_AGENT
from playwright.sync_api import Page, BrowserContext


class HyundaiCollector(BaseCollector):
    store_id   = "hyundai"
    store_name = "현대백화점"
    base_url   = "https://hi.thehyundai.com"

    # 현대 Hi는 robots.txt 차단 → 브라우저 지문 강화
    after_load_ms = 3000

    def _make_context(self, browser) -> BrowserContext:
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=USER_AGENT,
            locale="ko-KR",
            # 자바스크립트 navigator 속성 위장
            java_script_enabled=True,
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-Mode": "navigate",
            },
        )
        # webdriver 탐지 우회
        ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['ko-KR','ko'] });
        """)
        return ctx

    def promotion_selectors(self):
        return [
            "[class*='MainBanner']", "[class*='VisualBanner']",
            "[class*='EventBanner']", "[class*='HeroBanner']",
            "[class*='Promotion']",   "[class*='promotion']",
            "[class*='banner']",      ".swiper-slide",
            "[class*='MainSlide']",   "[class*='FeatureArea']",
        ]

    def product_selectors(self):
        return [
            "[class*='ProductItem']", "[class*='GoodsItem']",
            "[class*='ProductCard']", "[class*='product-item']",
            "[class*='goods-card']",  "[class*='ItemList'] li",
            "[class*='RecommendItem']",
        ]

    def extra_setup(self, page: Page):
        # 쿠키 동의 버튼 클릭 시도
        for sel in [
            "button[class*='agree']", "button[class*='Accept']",
            ".cookie-agree", "#cookieAgreeBtn",
        ]:
            try:
                btn = page.query_selector(sel)
                if btn:
                    btn.click()
                    page.wait_for_timeout(600)
                    break
            except Exception:
                pass

        # 팝업 닫기
        for sel in [
            "[class*='Popup'] button[class*='close']",
            "[class*='Modal'] button[class*='close']",
            "[class*='popup-close']", ".btn-close",
        ]:
            try:
                btn = page.query_selector(sel)
                if btn:
                    btn.click()
                    page.wait_for_timeout(400)
            except Exception:
                pass
