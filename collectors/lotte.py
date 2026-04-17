"""collectors/lotte.py — 롯데온 백화점관"""
from collectors.base import BaseCollector
from playwright.sync_api import Page


class LotteCollector(BaseCollector):
    store_id   = "lotte"
    store_name = "롯데온"
    base_url   = "https://www.lotteon.com/p/display/shop/seltDpShop/13331?callType=menu"

    after_load_ms = 3000   # 롯데온은 렌더링이 느린 편

    def promotion_selectors(self):
        return [
            # 롯데온 실제 클래스 패턴
            "[class*='bn_']",         # 배너류
            "[class*='bnr']",
            "[class*='visual']",
            "[class*='event']",
            "[class*='EventBanner']",
            "[class*='MainBanner']",
            ".swiper-slide",
            "[class*='shopBanner']",
            "[class*='brandBanner']",
            "[class*='promotion']",
        ]

    def product_selectors(self):
        return [
            # 롯데온 상품 카드
            ".prod_item",        ".prod-item",
            "[class*='prod_']",  "[class*='item_unit']",
            "[class*='goodsItem']", "[class*='goods_item']",
            "[class*='ProductCard']",
            "li[class*='item']",
        ]

    def extra_setup(self, page: Page):
        # 롯데온 레이어 팝업 닫기
        for sel in [
            ".layer_popup .btn_close",
            "[class*='popup'] .close",
            "#popupWrap .btnClose",
            "button[class*='layerClose']",
        ]:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(500)
            except Exception:
                pass
