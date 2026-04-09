import os
import asyncio
from typing import List, Dict, Any, Callable, Optional
from playwright.async_api import async_playwright
import tkinter.simpledialog as simpledialog
import tkinter as tk

MAX_RETRIES = 3
RETRY_DELAY = 1.5


class BrowserController:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    async def _ensure_browser(self):
        if not self.browser or not self.browser.is_connected():
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception:
                    pass

            self.playwright = await async_playwright().start()

            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ]
            chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)
            chrome_user_data = os.path.expandvars(r"%LOCALAPPDATA%\VoiceAgentChrome")

            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=chrome_user_data,
                executable_path=chrome_exe if chrome_exe else None,
                headless=False,
                args=["--start-maximized", "--profile-directory=Default"],
                viewport={"width": 1280, "height": 800},
                locale="tr-TR",
                timezone_id="Europe/Istanbul",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            self.page = await self.browser.new_page()
            await self._inject_scripts()
            self.browser.on("disconnected", self._on_browser_closed)

        elif self.page is None or self.page.is_closed():
            self.page = await self.browser.new_page()
            await self._inject_scripts()

    async def _inject_scripts(self):
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
            window.chrome = { runtime: {} };
        """)

    def _on_browser_closed(self, *args):
        self.browser = None
        self.page = None
        self.playwright = None

    async def get_page_snapshot(self) -> str:
        try:
            html = await self.page.evaluate("""() => {
                const clone = document.documentElement.cloneNode(true);
                clone.querySelectorAll('script, style, svg, img, video, noscript, iframe').forEach(el => el.remove());

                const interactive = [];
                clone.querySelectorAll('input, button, a, form, select, textarea, [role="button"], [role="searchbox"], [onclick]').forEach(el => {
                    interactive.push(el.outerHTML.substring(0, 300));
                });

                return interactive.join('\\n');
            }""")
            return html[:8000]
        except Exception:
            return ""

    async def _do_click(self, selector: str, log: Callable):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                await self.page.wait_for_selector(selector, timeout=6000, state="visible")
                await self.page.click(selector)
                return
            except Exception:
                log(f"  Tiklanamadi ({attempt}/{MAX_RETRIES}): {selector}", "system")
                if attempt < MAX_RETRIES:
                    await self.page.wait_for_load_state("networkidle", timeout=5000)
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    raise Exception(f"Tiklanamadi ({MAX_RETRIES} denemeden sonra): {selector}")

    async def _do_type(self, selector: str, text: str, log: Callable):
        fallback_selectors = [
            selector,
            "input[type='search']",
            "input[type='text']",
            "input[name='q']",
            "input[name='search']",
            "input[id*='search']",
            "input[id*='Search']",
            "input[class*='search']",
            "input[class*='Search']",
            "textarea[name='q']",
        ]
        seen = set()
        unique_selectors = []
        for s in fallback_selectors:
            if s not in seen:
                seen.add(s)
                unique_selectors.append(s)

        for attempt in range(1, MAX_RETRIES + 1):
            for sel in unique_selectors:
                try:
                    await self.page.wait_for_selector(sel, timeout=3000, state="visible")
                    await self.page.fill(sel, text)
                    log(f"  Yazildi ({sel})", "system")
                    return
                except Exception:
                    continue

            log(f"  Hic bir selector calismadi ({attempt}/{MAX_RETRIES}), bekleniyor...", "system")
            await self.page.wait_for_load_state("networkidle", timeout=5000)
            await asyncio.sleep(RETRY_DELAY)

        raise Exception(f"Yazma basarisiz, hic bir selector eslesmedi.")

    async def execute_steps(self, steps: List[Dict[str, Any]], agent, log: Callable) -> str:
        await self._ensure_browser()
        result_message = "Gorev tamamlandi."

        i = 0
        while i < len(steps):
            step = steps[i]
            action = step.get("action")
            log(f"  Adim: {action} — {step.get('description', '')}", "system")

            try:
                if action == "navigate":
                    await self.page.goto(step["url"], wait_until="domcontentloaded", timeout=20000)
                    await self.page.wait_for_load_state("networkidle", timeout=8000)
                    await asyncio.sleep(0.8)

                elif action == "click":
                    await self._do_click(step["selector"], log)
                    await asyncio.sleep(0.5)

                elif action == "type":
                    await self._do_type(step["selector"], step["text"], log)
                    await asyncio.sleep(0.3)

                elif action == "press_key":
                    await self.page.keyboard.press(step.get("key", "Enter"))
                    await asyncio.sleep(0.8)
                    await self.page.wait_for_load_state("networkidle", timeout=8000)
                    snapshot = await self.get_page_snapshot()
                    if snapshot:
                        new_steps = await agent.replan_with_snapshot(steps[i+1:], snapshot, self.page.url)
                        steps = steps[:i+1] + new_steps

                elif action == "wait":
                    await asyncio.sleep(step.get("ms", 1000) / 1000)

                elif action == "scroll":
                    await self.page.evaluate(f"window.scrollBy(0, {step.get('amount', 400)})")

                elif action == "ask_user":
                    question = step.get("question", "Bilgi gerekiyor:")
                    log(f"Soru: {question}", "agent")
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, self._ask_dialog, question
                    )
                    if user_input:
                        context = f"Sayfa: {self.page.url}, Soru: {question}"
                        new_steps = await agent.continue_with_info(user_input, context)
                        steps = steps[:i+1] + new_steps + steps[i+1:]
                    else:
                        log("Kullanici iptal etti.", "system")
                        return "Kullanici iptal etti."

                elif action == "done":
                    result_message = step.get("message", "Gorev tamamlandi.")
                    break

            except Exception as e:
                log(f"  Hata ({action}): {e}", "error")
                raise

            i += 1

        return result_message

    def _ask_dialog(self, question: str) -> Optional[str]:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        answer = simpledialog.askstring("Bilgi Gerekiyor", question, parent=root)
        root.destroy()
        return answer

    def close(self):
        self.browser = None
        self.page = None
        self.playwright = None