import asyncio
import threading
import tkinter as tk
from tkinter import scrolledtext
import queue

from voice.listener import VoiceListener
from agent.gemini_agent import GeminiAgent
from browser.controller import BrowserController
from voice.speaker import Speaker

MSG_QUEUE = queue.Queue()

class VoiceAgentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sesli Ajan")
        self.root.geometry("600x500")
        self.root.configure(bg="#1a1a2e")

        self.agent = GeminiAgent()
        self.speaker = Speaker()
        self.browser = BrowserController()
        self.listener = VoiceListener(on_text=self.on_voice_input)

        self.listening = False
        self._build_ui()
        self._poll_queue()

    def _build_ui(self):
        title = tk.Label(self.root, text="Sesli Ajan", font=("Segoe UI", 18, "bold"),
                         bg="#1a1a2e", fg="#e0e0e0")
        title.pack(pady=(20, 5))

        self.status_label = tk.Label(self.root, text="Hazır", font=("Segoe UI", 11),
                                     bg="#1a1a2e", fg="#7f77dd")
        self.status_label.pack(pady=(0, 10))

        self.log_box = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, width=70, height=18,
            bg="#0f0f1a", fg="#c0c0d0", font=("Consolas", 10),
            insertbackground="white", relief="flat", bd=0
        )
        self.log_box.pack(padx=20, pady=5, fill=tk.BOTH, expand=True)
        self.log_box.tag_config("user", foreground="#9fe1cb")
        self.log_box.tag_config("agent", foreground="#afa9ec")
        self.log_box.tag_config("system", foreground="#f5c4b3")
        self.log_box.tag_config("error", foreground="#f09595")

        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=15)

        self.mic_btn = tk.Button(
            btn_frame, text="  Dinle  ", font=("Segoe UI", 12),
            bg="#534ab7", fg="white", activebackground="#7f77dd",
            relief="flat", padx=20, pady=8, cursor="hand2",
            command=self.toggle_listen
        )
        self.mic_btn.pack(side=tk.LEFT, padx=8)

        stop_btn = tk.Button(
            btn_frame, text="  Durdur  ", font=("Segoe UI", 12),
            bg="#3d3d3a", fg="#c0c0d0", activebackground="#5f5e5a",
            relief="flat", padx=20, pady=8, cursor="hand2",
            command=self.stop_all
        )
        stop_btn.pack(side=tk.LEFT, padx=8)

    def log(self, text, tag="system"):
        MSG_QUEUE.put((text, tag))

    def _poll_queue(self):
        while not MSG_QUEUE.empty():
            text, tag = MSG_QUEUE.get_nowait()
            self.log_box.insert(tk.END, text + "\n", tag)
            self.log_box.see(tk.END)
        self.root.after(100, self._poll_queue)

    def toggle_listen(self):
        if not self.listening:
            self.listening = True
            self.mic_btn.config(text="  Dinleniyor...  ", bg="#993c1d")
            self.status_label.config(text="Sizi dinliyorum...", fg="#f0997b")
            threading.Thread(target=self.listener.listen_once, daemon=True).start()
        else:
            self.listening = False
            self.mic_btn.config(text="  Dinle  ", bg="#534ab7")
            self.status_label.config(text="Hazır", fg="#7f77dd")

    def on_voice_input(self, text: str):
        self.listening = False
        self.root.after(0, lambda: self.mic_btn.config(text="  Dinle  ", bg="#534ab7"))
        self.root.after(0, lambda: self.status_label.config(text="İşleniyor...", fg="#fac775"))
        self.log(f"Sen: {text}", "user")
        threading.Thread(target=self._run_agent, args=(text,), daemon=True).start()

    def _run_agent(self, command: str):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._execute(command))
        loop.close()

    async def _execute(self, command: str):
        try:
            steps = await self.agent.plan(command)
            self.log(f"Ajan: {len(steps)} adım planlandı", "agent")

            result = await self.browser.execute_steps(steps, self.agent, self.log)

            self.speaker.say(result)
            self.log(f"Tamamlandı: {result}", "agent")
        except Exception as e:
            msg = f"Hata: {str(e)}"
            self.log(msg, "error")
            self.speaker.say("Bir hata oluştu. " + str(e))
        finally:
            self.root.after(0, lambda: self.status_label.config(text="Hazır", fg="#7f77dd"))

    def stop_all(self):
        self.listener.stop()
        self.listening = False
        self.mic_btn.config(text="  Dinle  ", bg="#534ab7")
        self.status_label.config(text="Hazir", fg="#7f77dd")
        self.log("Dinleme durduruldu.", "system")



def main():
    root = tk.Tk()
    app = VoiceAgentApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
