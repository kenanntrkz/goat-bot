"""Mentor — Agency Guide Agent

Answers business questions using DOA classroom content.
Uses Claude CLI if available, otherwise serves static content.
"""

from pathlib import Path

from agents.base import BaseAgent, DATA_DIR


class MentorAgent(BaseAgent):
    agent_id = "mentor"
    name = "Mentor"
    role = "Agency guide — answers any business question"
    category = "education"

    def run(self) -> dict:
        """Returns overview of available classroom content."""
        self.log("Loading classroom content...")

        content = self._load_classroom()
        topics = list(content.keys())

        results = {
            "status": "ok",
            "summary": f"Mentor ready with {len(topics)} guides: {', '.join(topics)}",
            "metrics": {
                "topics_available": len(topics),
                "topics": topics,
            },
            "recommendations": [
                "Ajansını kurmak hakkında her şeyi sorabilirsin",
                "Dene: 'İlk müşterimi nasıl bulurum?'",
                "Dene: 'Hizmetlerimi ne kadar fiyatlandırmalıyım?'",
                "Dene: 'Şirketimi nasıl kurarım?'",
            ],
        }

        self.save_output("mentor_report.json", results)
        return results

    def answer(self, question: str) -> str:
        """Answer a question using classroom content + Claude CLI."""
        content = self._load_classroom()

        # First try: find the most relevant classroom file and use Claude with just that
        best_topic, best_text = self._find_best_topic(question, content)

        if best_text:
            prompt = f"""Sen Mentor'sun — sıfırdan otomasyon ajansı kuran kişilere yardım ediyorsun.

İşte ilgili eğitim içeriği:

{best_text[:3000]}

Bu soruyu pratik ve somut adımlarla yanıtla. Türkçe cevap ver. Kısa ve net ol.

Soru: {question}"""

            response = self.call_claude(prompt, timeout=30)
            if response:
                return response

        # Fallback: serve the relevant content directly
        return self._static_answer(question, content)

    def _load_classroom(self) -> dict:
        """Load all classroom markdown files."""
        classroom_dir = DATA_DIR / "classroom"
        content = {}
        if classroom_dir.exists():
            for f in sorted(classroom_dir.glob("*.md")):
                topic = f.stem.replace("_", " ").title()
                content[topic] = f.read_text(encoding="utf-8")
        return content

    def _find_best_topic(self, question: str, content: dict):
        """Find the most relevant classroom topic for a question."""
        q = question.lower()
        keyword_map = {
            "getting started": ["başla", "start", "nasıl", "sıfır", "zero", "kurulum", "setup", "ne yapmalı", "yapma", "lazım", "ilk adım", "nereden"],
            "pricing guide": ["fiyat", "price", "ücret", "charge", "pricing", "para", "money", "kaç", "maliyet", "paket"],
            "client acquisition": ["müşteri", "client", "customer", "bul", "find", "satış", "sales", "ulaş", "email", "outreach", "lead", "soğuk", "cold", "iletişim", "reach"],
            "tools guide": ["araç", "tool", "n8n", "make", "claude", "automation", "otomasyon", "yazılım", "platform"],
            "service catalog": ["hizmet", "service", "teklif", "offer", "ne yapabilirim", "sun", "paket", "ne satabilirim"],
        }
        best_key = None
        best_score = 0
        for topic_key, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if kw in q)
            if score > best_score:
                best_score = score
                best_key = topic_key

        # Default to getting_started for generic questions
        if not best_key:
            best_key = "getting started"

        for topic_name, text in content.items():
            if best_key.replace("_", " ") in topic_name.lower():
                return topic_name, text
        # Return first available
        if content:
            name = list(content.keys())[0]
            return name, content[name]
        return None, None

    def _static_answer(self, question: str, content: dict) -> str:
        """Serve relevant classroom content directly when Claude CLI is unavailable."""
        topic_name, text = self._find_best_topic(question, content)

        if text:
            # Trim to a reasonable length and return
            lines = text.strip().split('\n')
            trimmed = '\n'.join(lines[:60])
            return f"{topic_name}\n\n{trimmed}"

        return ("Şu konularda rehberlerim var:\n"
                "- Başlangıç Rehberi\n"
                "- Fiyatlandırma\n"
                "- Müşteri Bulma\n"
                "- Araçlar\n"
                "- Hizmet Kataloğu\n\n"
                "Bu konulardan birini sor!")
