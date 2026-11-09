import os
import aiohttp
import json
import re
from typing import Optional, List
from core.models.problem import Problem
from core.interfaces.ai_tutor import IAITutor

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

class GeminiAdapter(IAITutor):
    def __init__(self, api_key: str = GEMINI_API_KEY, model: str = GEMINI_MODEL):
        self.api_key = api_key
        self.model = model

    @property
    def api_url(self) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    async def _generate(self, system_instruction: str, prompt: str) -> str:
        if not self.api_key:
            return (
                "⚠️ **AI Tutor is currently disabled.**\n"
                "To enable Socratic hints, code reviews, and AI problem generation, add `GEMINI_API_KEY=your_key` to your `.env` file! "
                "(You can get a free key at https://aistudio.google.com/)"
            )

        url = f"{self.api_url}?key={self.api_key}"
        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 800
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=12) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            return candidates[0]["content"]["parts"][0]["text"]
                        return "Received empty response from AI model."
                    else:
                        error_text = await resp.text()
                        return f"AI Service error ({resp.status}): {error_text[:200]}"
        except Exception as e:
            return f"Failed to contact AI service: {e}"

    async def get_socratic_hint(self, problem: Problem, user_query: str, hint_level: int = 1) -> str:
        sys_prompt = (
            "You are a friendly, expert DSA technical interviewer. Your goal is to guide the student "
            "using the Socratic method. NEVER provide the complete code, full algorithm name, or answer upfront. "
            "Instead, ask leading questions, point out invariants, or suggest a mental model to help them realize "
            "the next step on their own. Keep your response concise (3-4 bullet points maximum)."
        )
        prompt = (
            f"Problem: {problem.title} ({problem.difficulty})\n"
            f"Pattern / Topic: {problem.pattern} in {problem.step_title}\n"
            f"Student's question/idea: {user_query}\n"
            f"Hint Level requested: {hint_level} (1=Intuition/brute-force check, 2=Data structure clue, 3=Algorithm sketch)"
        )
        return await self._generate(sys_prompt, prompt)

    async def review_code(self, problem: Problem, code: str) -> str:
        sys_prompt = (
            "You are a Senior Software Engineer conducting a DSA code review. "
            "Analyze the student's solution. Format your response strictly into:\n"
            "1. **Time Complexity**: Big-O with explanation\n"
            "2. **Space Complexity**: Big-O with explanation\n"
            "3. **Edge Case Audit**: Check for empty inputs, negative numbers, overflow, single elements\n"
            "4. **Optimization / Follow-up**: One follow-up question or optimization tip.\n"
            "Keep the feedback encouraging, sharp, and concise."
        )
        prompt = (
            f"Problem: {problem.title}\n"
            f"Code snippet:\n```\n{code}\n```"
        )
        return await self._generate(sys_prompt, prompt)

    async def ask_concept(self, topic_or_pattern: str, question: str) -> str:
        sys_prompt = (
            "You are an intuitive DSA educator like Striver or NeetCode. Explain the concept cleanly, "
            "using simple analogies, visual ASCII diagrams where appropriate, and a small Python pseudocode snippet."
        )
        prompt = f"Topic/Pattern: {topic_or_pattern}\nStudent Question: {question}"
        return await self._generate(sys_prompt, prompt)

    async def generate_pattern_insight(self, pattern_name: str, topic: str, problem_title: str) -> str:
        sys_prompt = (
            "You are a Principal Software Engineer and competitive programmer. Provide one bite-sized, "
            "high-yield insight about this DSA pattern. It could be an interview trap, a clever invariant to look for, "
            "or an optimization tip. Format cleanly with:\n"
            "• **Key Invariant / Trick**: 1-2 punchy sentences\n"
            "• **Interview Trap**: A classic mistake candidates make\n"
            "• **Follow-up Question to ponder**: A small mental challenge.\n"
            "Keep it under 150 words, sharp and motivating!"
        )
        prompt = (
            f"Topic: {topic}\n"
            f"Pattern: {pattern_name}\n"
            f"Currently Practicing Problem: {problem_title}"
        )
        return await self._generate(sys_prompt, prompt)

    async def generate_drill_problems(self, pattern_name: str, topic: str, count: int = 3) -> List[dict]:
        sys_prompt = (
            "You are a Senior Technical Recruiter and DSA Coach. Curate realistic coding interview problems "
            "strictly for the requested pattern. Return ONLY a valid JSON array of objects with no markdown fences, "
            "containing: title, difficulty (Easy, Medium, or Hard), and slug (leetcode url slug)."
        )
        prompt = (
            f"Recommend {count} top LeetCode coding interview problems for:\n"
            f"Topic: {topic}\n"
            f"Pattern: {pattern_name}\n\n"
            f"Return JSON format:\n"
            f'[{{"title": "Search in Rotated Sorted Array", "difficulty": "Medium", "slug": "search-in-rotated-sorted-array"}}]'
        )
        raw = await self._generate(sys_prompt, prompt)
        try:
            cleaned = re.sub(r"```(?:json)?\n?", "", raw).strip().rstrip("`")
            data = json.loads(cleaned)
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []
