import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from typing import List, Dict, Any

load_dotenv()

SYSTEM_PROMPT = """Sen bir tarayıcı otomasyon ajanısın. Kullanıcının sesli komutunu alıp tarayıcıda gerçekleştirilecek adımlara çevirirsin.

Her yanıtını JSON formatında ver. Format:
{
  "steps": [
    {"action": "navigate", "url": "https://...", "description": "..."},
    {"action": "click", "selector": "CSS_SELECTOR", "description": "ne tıklandığı"},
    {"action": "type", "selector": "...", "text": "yazılacak metin", "description": "..."},
    {"action": "wait", "ms": 1000, "description": "bekleniyor"},
    {"action": "press_key", "key": "Enter", "description": "..."},
    {"action": "ask_user", "question": "kullanıcıya sorulacak soru"},
    {"action": "done", "message": "tamamlama mesajı"}
  ]
}

Kullanılabilir action'lar:
- navigate: URL'e git
- click: elemana tıkla (selector gerekli)
- type: metin yaz (selector + text gerekli)
- wait: bekle (ms cinsinden)
- scroll: sayfayı kaydır (amount px)
- ask_user: kullanıcıdan bilgi iste (sifre, email vb.)
- press_key: klavye tusuna bas (Enter, Tab vb.)
- done: gorevi tamamla (message ile)

ONEMLI KURALLAR:
1. Sifre veya hassas bilgi gerektiginde MUTLAKA ask_user kullan
2. Her adim icin description ekle
3. Adimlar arasi wait ekle (500-1500ms)
4. Kullanici komutu Turkce sesli tanima ile alindi. Yanlis algilanan kelimeleri duzelt (ornek: 'youtuba' -> 'YouTube', 'linkedlin' -> 'LinkedIn')
5. Sadece JSON dondur, markdown veya aciklama ekleme
6. Bir selector calismazsa alternatif selector dene (id, name, aria-label, placeholder sirasinda)
7. Sayfa yuklenmesini beklemeden eleman aramaya calisma, her navigate sonrasi wait ekle
8. Arama islemi icin genellikle: navigate -> type -> press_key(Enter) -> wait -> click sirasi izle
9. Giris gerektiren sitelerde once sayfanin tam yuklenmesini bekle, sonra alanlari doldur
10. Kullanicinin komutu belirsizse en makul yorumu yap, sormadan devam et
11. Arama yapmak icin Google kullanma. Hedef siteye direkt navigate et (ornek: cimri.com, akakce.com). Google bot korumasi engel cikarabilir."""


class GeminiAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY bulunamadi.\n"
                ".env dosyasinda GEMINI_API_KEY=... satirinin oldugu emin ol.\n"
                "Dosya konumu: voice-agent klasoru icinde .env"
            )
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def _parse(self, raw: str) -> dict:
        raw = raw.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())

    async def plan(self, command: str) -> List[Dict[str, Any]]:
        prompt = f"{SYSTEM_PROMPT}\n\nKullanici komutu: {command}"
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        data = self._parse(response.text)
        return data.get("steps", [])

    async def continue_with_info(self, user_answer: str, context: str) -> List[Dict[str, Any]]:
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Kullanici su bilgiyi verdi: \"{user_answer}\"\n"
            f"Baglamı: {context}\n"
            f"Bu bilgiyle devam etmek icin gereken adimlari ver."
        )
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        data = self._parse(response.text)
        return data.get("steps", [])

    async def replan_with_snapshot(self, remaining_steps: list, snapshot: str, url: str) -> list:
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Simdi su sayfadasin: {url}\n\n"
            f"Sayfadaki gercek HTML elementleri:\n{snapshot}\n\n"
            f"Asagidaki adimlari bu sayfanin gercek elementlerini kullanarak yeniden planla.\n"
            f"Selector olarak sadece bu HTML'de gercekten var olan id, name, class veya attribute degerlerini kullan.\n\n"
            f"Mevcut kalan adimlar:\n{remaining_steps}"
        )
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        data = self._parse(response.text)
        return data.get("steps", remaining_steps)