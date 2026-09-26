"""SpeakWise: a prompt-driven, personalized English conversation tutor.

Run:
    python app.py

The app uses only Python's standard library. If an API key is provided, it
calls an OpenAI-compatible chat-completions endpoint; without one it runs in
local demo mode.
"""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any


LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
LEVEL_SCORE = {level: index for index, level in enumerate(LEVELS, start=1)}


def build_prompt(name: str, goal: str, interest: str, starting_level: str) -> str:
    return f"""You are SpeakWise, a hyper-personalized English conversation tutor.
Learner profile: name={name}; goal={goal}; interests={interest}; starting estimate={starting_level}.

RULES
1. Conversation is text-based and your learner-facing conversation is in English. Ask one natural follow-up question every turn.
2. Adapt vocabulary, sentence length, grammar and topic difficulty to the learner's demonstrated CEFR level.
3. Reassess after every 3 learner turns (or sooner when strong evidence appears). Choose exactly one CEFR code: A1, A2, B1, B2, C1, or C2.
4. If the new level differs from the previous level, explicitly write: "LEVEL CHANGE: previous X -> new Y" and give one evidence-based reason.
5. Give concise, specific feedback after each learner message: one correction, a more natural alternative, and one useful expression.
6. Keep an evidence log of grammar control, vocabulary range, fluency/coherence, comprehensibility and interaction.
   Do not claim listening or pronunciation evidence from text.
7. On START, introduce the activity and ask an easy question. On END, provide final CEFR, evidence,
   2 strengths, 2 priorities, and a 3-step practice plan.

OUTPUT FORMAT
Reply: <natural English response and one follow-up question>
Feedback: <specific correction / natural alternative / useful expression>
Assessment: <show every 3 turns or when changed: CEFR: X — brief evidence>
Always be encouraging, honest, concise, and personalized."""


EXAMPLES = {
    "A1 Basic User": """Student: My name is Mina. I live in Seoul. I like coffee.
SpeakWise: Nice to meet you, Mina! What coffee do you like?
Feedback: “I like coffee” is correct. Add “I usually drink …” to give more information.
Assessment: CEFR: A1 — short, familiar sentences with basic personal information.""",
    "A2 → B1 Level Change": """Student: I went to Busan last weekend. The beach was beautiful and I eat seafood.
SpeakWise: What did you do after eating seafood?
Feedback: Say “I ate seafood” because the trip was in the past.
Assessment: CEFR: A2 — understandable past events with one tense error.

Student: After lunch, we walked along the beach, although it was raining, because we wanted to see the sunset.
Feedback: Excellent use of “although” and “because.”
LEVEL CHANGE: A2 → B1
Evidence: You connected ideas with linking words and explained a recommendation.""",
    "B2 Independent User": """Student: Remote work can improve productivity, but its impact depends on how organizations structure communication and accountability.
SpeakWise: What policy would preserve flexibility without weakening collaboration?
Feedback: Your contrast and abstract vocabulary are effective.
Assessment: CEFR: B2 — sustained, nuanced argument with clear organization.""",
}


class SpeakWiseApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SpeakWise | 초개인화 영어 회화 챗봇")
        self.geometry("1160x760")
        self.minsize(900, 620)
        self.configure(bg="#f5f7fb")
        self.active = False
        self.turns = 0
        self.current_level = ""
        self.messages: list[dict[str, str]] = []
        self.request_in_progress = False
        self._build_style()
        self._build_ui()

    def _build_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f5f7fb")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("Title.TLabel", background="#f5f7fb", foreground="#172033", font=("Arial", 25, "bold"))
        style.configure("Subtitle.TLabel", background="#f5f7fb", foreground="#697386", font=("Arial", 11))
        style.configure("PanelTitle.TLabel", background="#ffffff", foreground="#172033", font=("Arial", 13, "bold"))
        style.configure("Primary.TButton", background="#365cf5", foreground="#ffffff", padding=8)
        style.map("Primary.TButton", background=[("active", "#2949d4")])
        style.configure("TNotebook", background="#ffffff", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(14, 9))

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x", padx=24, pady=(20, 12))
        ttk.Label(header, text="SpeakWise", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="나에게 맞춰 대화하고, 근거와 함께 성장하는 영어 회화 연습",
                  style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 22))
        self.sidebar = ttk.Frame(body, style="Panel.TFrame", padding=18)
        self.sidebar.pack(side="left", fill="y", padx=(0, 16))
        self.main = ttk.Frame(body, style="Panel.TFrame")
        self.main.pack(side="left", fill="both", expand=True)
        self._build_sidebar()
        self._build_main()

    def _entry(self, parent: ttk.Frame, label: str, value: str = "", secret: bool = False) -> tk.Entry:
        ttk.Label(parent, text=label, background="#ffffff", foreground="#697386").pack(anchor="w", pady=(10, 3))
        entry = tk.Entry(parent, show="*" if secret else "", relief="solid", bd=1)
        entry.insert(0, value)
        entry.pack(fill="x")
        return entry

    def _build_sidebar(self) -> None:
        ttk.Label(self.sidebar, text="학습자 프로필", style="PanelTitle.TLabel").pack(anchor="w")
        self.name = self._entry(self.sidebar, "이름 또는 닉네임", "Learner")
        self.goal = self._entry(self.sidebar, "학습 목표", "여행에서 자연스럽게 대화하기")
        self.interest = self._entry(self.sidebar, "관심 주제", "travel, food, daily life")
        ttk.Label(self.sidebar, text="시작 예상 수준", background="#ffffff", foreground="#697386").pack(anchor="w", pady=(10, 3))
        self.start_level = ttk.Combobox(self.sidebar, values=LEVELS, state="readonly")
        self.start_level.set("B1")
        self.start_level.pack(fill="x")
        self.endpoint = self._entry(self.sidebar, "API endpoint (OpenAI 호환)",
                                    "https://api.openai.com/v1/chat/completions")
        self.model = self._entry(self.sidebar, "Model", "gpt-4o-mini")
        self.api_key = self._entry(self.sidebar, "API key (임시 사용)", secret=True)

        buttons = ttk.Frame(self.sidebar, style="Panel.TFrame")
        buttons.pack(fill="x", pady=(16, 0))
        self.start_button = ttk.Button(buttons, text="연습 시작", style="Primary.TButton", command=self.start_session)
        self.start_button.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.end_button = ttk.Button(buttons, text="연습 종료", command=self.end_session, state="disabled")
        self.end_button.pack(side="left", fill="x", expand=True)
        ttk.Label(self.sidebar, text="API key 없이도 데모 모드로 실행됩니다.",
                  background="#ffffff", foreground="#697386", wraplength=250).pack(anchor="w", pady=(10, 0))

        status = ttk.Frame(self.sidebar, style="Panel.TFrame")
        status.pack(fill="x", pady=(22, 0))
        ttk.Separator(status).pack(fill="x", pady=(0, 12))
        ttk.Label(status, text="현재 평가", background="#ffffff", foreground="#697386").pack(anchor="w")
        self.level_label = ttk.Label(status, text="—", background="#ffffff", foreground="#365cf5",
                                     font=("Arial", 27, "bold"))
        self.level_label.pack(anchor="w")
        self.assessment = ttk.Label(status, text="아직 평가하지 않았습니다.", background="#ffffff",
                                    foreground="#697386", wraplength=260)
        self.assessment.pack(anchor="w")

    def _build_main(self) -> None:
        self.tabs = ttk.Notebook(self.main)
        self.tabs.pack(fill="both", expand=True)
        chat_tab = ttk.Frame(self.tabs, style="Panel.TFrame", padding=14)
        examples_tab = ttk.Frame(self.tabs, style="Panel.TFrame", padding=18)
        prompt_tab = ttk.Frame(self.tabs, style="Panel.TFrame", padding=18)
        self.tabs.add(chat_tab, text="회화 연습")
        self.tabs.add(examples_tab, text="제출용 예시 3개")
        self.tabs.add(prompt_tab, text="개발 프롬프트")

        self.chat = tk.Text(chat_tab, state="disabled", wrap="word", relief="flat",
                            bg="#ffffff", fg="#172033", font=("Arial", 11), padx=8, pady=8)
        self.chat.pack(fill="both", expand=True)
        composer = ttk.Frame(chat_tab, style="Panel.TFrame")
        composer.pack(fill="x", pady=(10, 0))
        self.input = tk.Text(composer, height=3, wrap="word", relief="solid", bd=1)
        self.input.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.send_button = ttk.Button(composer, text="보내기", style="Primary.TButton",
                                      command=self.send_message, state="disabled")
        self.send_button.pack(side="right", anchor="s")
        self.input.bind("<Control-Return>", lambda _event: self.send_message())

        for title, text in EXAMPLES.items():
            ttk.Label(examples_tab, text=f"대화 · {title}", style="PanelTitle.TLabel").pack(anchor="w", pady=(0, 5))
            box = tk.Text(examples_tab, height=7, wrap="word", relief="solid", bd=1, bg="#fafbfe")
            box.insert("1.0", text)
            box.configure(state="disabled")
            box.pack(fill="x", pady=(0, 12))

        ttk.Label(prompt_tab, text="Part 1 제출용 시스템 프롬프트", style="PanelTitle.TLabel").pack(anchor="w")
        self.prompt_box = tk.Text(prompt_tab, wrap="word", relief="solid", bd=1, bg="#111827",
                                  fg="#e5e7eb", font=("Menlo", 10))
        self.prompt_box.pack(fill="both", expand=True, pady=(8, 10))
        ttk.Button(prompt_tab, text="프롬프트 새로고침", command=self.refresh_prompt).pack(anchor="w")

    def append_chat(self, speaker: str, text: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{speaker}\n{text}\n\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def refresh_prompt(self) -> None:
        self.prompt_box.configure(state="normal")
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.insert("1.0", build_prompt(self.name.get(), self.goal.get(),
                                                     self.interest.get(), self.start_level.get()))
        self.prompt_box.configure(state="disabled")

    def start_session(self) -> None:
        self.active = True
        self.turns = 0
        self.current_level = ""
        self.messages = []
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.end_button.configure(state="normal")
        self.send_button.configure(state="normal")
        self.append_chat("SpeakWise", f"Hi {self.name.get()}! We'll practice {self.goal.get()}.\n"
                                      f"What is one recent experience related to {self.interest.get()}?")
        self.refresh_prompt()
        self.input.focus_set()

    def end_session(self) -> None:
        if not self.active:
            return
        self.active = False
        self.start_button.configure(state="normal")
        self.end_button.configure(state="disabled")
        self.send_button.configure(state="disabled")
        final = self.current_level or self.start_level.get()
        self.append_chat("SpeakWise", f"Session complete.\n\nFinal assessment: CEFR: {final}\n"
                                      "Strengths: You kept the conversation going and shared personal meaning.\n"
                                      "Priorities: Add specific details and review one recurring grammar pattern.\n"
                                      "Practice plan: 1) speak for 60 seconds, 2) add two connectors, "
                                      "3) reuse one new expression tomorrow.")

    def send_message(self) -> None:
        text = self.input.get("1.0", "end").strip()
        if not text or not self.active or self.request_in_progress:
            return
        self.input.delete("1.0", "end")
        self.append_chat("You", text)
        self.messages.append({"role": "user", "content": text})
        self.request_in_progress = True
        self.send_button.configure(state="disabled")
        if self.api_key.get().strip():
            api_key = self.api_key.get().strip()
            endpoint = self.endpoint.get().strip()
            model = self.model.get().strip()
            system_prompt = build_prompt(
                self.name.get(), self.goal.get(), self.interest.get(), self.start_level.get()
            )
            conversation = list(self.messages)
            threading.Thread(
                target=self._request_api,
                args=(api_key, endpoint, model, system_prompt, conversation),
                daemon=True,
            ).start()
        else:
            self._finish_reply(self.local_reply(text))

    def local_reply(self, text: str) -> str:
        self.turns += 1
        word_count = len(text.split())
        if word_count < 7:
            inferred = "A1"
        elif word_count < 14:
            inferred = "A2"
        elif word_count < 26:
            inferred = "B1"
        elif word_count < 42:
            inferred = "B2"
        else:
            inferred = "C1"
        if self.turns == 1:
            inferred = self.start_level.get()
        reason = f"Your response used {word_count} words and showed "
        reason += "connected ideas." if word_count > 20 else "short, familiar sentences."
        self.set_level(inferred, reason)
        if re.search(r"\bi am agree\b", text, re.I):
            correction = 'Say “I agree” rather than “I am agree.”'
        elif re.search(r"\bhe go\b", text, re.I):
            correction = 'Say “He goes” for third-person singular present tense.'
        else:
            correction = "Try adding one detail to make your answer clearer."
        assessment = f"\nAssessment: CEFR: {inferred} — {reason}"
        return (f"Thanks for sharing that. Tell me one more detail about it.\n\n"
                f"Feedback: {correction}\n"
                "More natural: “I would like to talk more about it.”\n"
                f"Useful expression: “One reason is that …”{assessment}")

    def set_level(self, level: str, reason: str) -> None:
        if level not in LEVELS:
            return
        previous = self.current_level
        self.current_level = level
        self.level_label.configure(text=level)
        self.assessment.configure(text=reason)
        if previous and previous != level:
            self.append_chat("SpeakWise", f"LEVEL CHANGE: {previous} → {level}\nEvidence: {reason}")

    def _request_api(
        self,
        api_key: str,
        endpoint: str,
        model: str,
        system_prompt: str,
        conversation: list[dict[str, str]],
    ) -> None:
        payload = {
            "model": model,
            "temperature": 0.4,
            "messages": [{"role": "system", "content": system_prompt}, *conversation],
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
            reply = data["choices"][0]["message"]["content"]
            self.after(0, lambda: self._finish_reply(reply))
        except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError, OSError) as error:
            error_message = str(error)
            self.after(
                0,
                lambda message=error_message: self._finish_reply(
                    f"연결 오류: {message}\nAPI 설정을 확인하거나 key 없이 데모 모드를 사용하세요."
                ),
            )

    def _finish_reply(self, reply: str) -> None:
        self.request_in_progress = False
        self.messages.append({"role": "assistant", "content": reply})
        self.append_chat("SpeakWise", reply)
        found = re.search(r"\b(A1|A2|B1|B2|C1|C2)\b", reply)
        if found:
            self.set_level(found.group(1), "The tutor's latest assessment is based on recent text evidence.")
        self.send_button.configure(state="normal" if self.active else "disabled")


if __name__ == "__main__":
    app = SpeakWiseApp()
    app.mainloop()
