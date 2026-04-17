"""collectors/shinsegae.py — 신세계V"""
from collectors.base import BaseCollector
from playwright.sync_api import Page


class ShinsegaeCollector(BaseCollector):
    store_id   = "shinsegae"
    store_name = "신세계V"
    base_url   = "https://www.shinsegaev.com"

    def promotion_selectors(self):
        return [
            "[class*='BannerSlide']", "[class*='MainBanner']",
            "[class*='EventBanner']", "[class*='banner']",
            "[class*='promotion']",   "[class*='visual']",
            ".swiper-slide",
        ]

    def product_selectors(self):
        return [
            "[class*='ProductCard']", "[class*='GoodsCard']",
            "[class*='ItemCard']",    "[class*='product-item']",
            "[class*='goods-item']",  ".prd-item",
        ]

    def extra_setup(self, page: Page):
        # 팝업/레이어 닫기 시도
        for sel in ["[class*='popup'] button[class*='close']",
                    "[class*='modal'] button[class*='close']",
                    "[class*='layer'] .btn-close"]:
            try:
                btn = page.query_selector(sel)
                if btn:
                    btn.click()
                    page.wait_for_timeout(500)
            except Exception:
                pass
