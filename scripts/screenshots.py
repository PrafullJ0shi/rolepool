"""Render the site with headless Chrome and save screenshots to docs/."""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:18473/"
OUT = Path(__file__).resolve().parent.parent / "docs"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        shots = [
            ("board-light", "#board", 1440, 1800, "light"), ("board-dark", "#board", 1440, 1800, "dark"),
            ("trends-light", "#trends", 1440, 2600, "light"), ("feeds-light", "#feeds", 1440, 1700, "light"),
            ("method-light", "#method", 1440, 2400, "light"), ("board-mobile", "#board", 390, 1600, "light"),
        ]
        for name, hash_, w, h, scheme in shots:
            ctx = await browser.new_context(viewport={"width": w, "height": h}, color_scheme=scheme, device_scale_factor=1 if w > 800 else 2)
            page = await ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            await page.goto(BASE + "index.html" + hash_)
            await page.wait_for_selector("#jobs tbody tr", state="attached")
            await page.wait_for_timeout(600)
            await page.screenshot(path=str(OUT / f"screenshot-{name}.png"), full_page=False)
            print(name, "errors:", errors)
            await ctx.close()
        await browser.close()


asyncio.run(main())
