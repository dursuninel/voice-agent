# Sesli Ajan

Sesli komutlarla tarayıcıyı kontrol eden Windows masaüstü uygulaması. Konuşarak web sitelerinde gezin, arama yapın, form doldurun.

## Kurulum

1. `setup.bat` çalıştır — bağımlılıkları kurar, API anahtarlarını ister
2. `run.bat` ile başlat

## Gereksinimler

- Python 3.10+
- Mikrofon
- [Gemini API anahtarı](https://aistudio.google.com) — tarayıcı otomasyon planlaması
- [Groq API anahtarı](https://console.groq.com) — ses tanıma (ücretsiz)

## Örnek Komutlar

- "YouTube'u aç ve Neffex şarkısı arat, ilk videoyu aç"
- "LinkedIn hesabıma giriş yap"
- "Cimri'den en ucuz RAM fiyatlarını göster"
- "Gmail'i aç ve gelen kutusunu göster"

## Mimari

```
main.py                → Tkinter UI + koordinasyon
agent/gemini_agent.py  → Gemini 2.5 Flash ile adım planlama
browser/controller.py  → Playwright + Chrome ile tarayıcı kontrolü
voice/listener.py      → Groq Whisper Large v3 ile ses tanıma
voice/speaker.py       → pyttsx3 ile sesli geri bildirim
```

## Notlar

- Groq Whisper Large v3 kullanılır — bulut tabanlı, Türkçe için optimize
- Hassas bilgiler (şifre vb.) dialog kutusuyla istenir, loglara yazılmaz
- Mevcut Chrome kurulumunu kullanır, açık pencerelerinize dokunmaz
