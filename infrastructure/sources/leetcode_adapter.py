import aiohttp
import random
from typing import List, Optional
from core.models.problem import Problem
from core.interfaces.problem_source import IProblemSource
from core.interfaces.ai_tutor import IAITutor

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

# Topic/Pattern to LeetCode slug mappings
TOPIC_TAG_MAP = {
    "binary search": "binary-search",
    "on answers": "binary-search",
    "arrays": "array",
    "two pointer": "two-pointers",
    "sliding window": "sliding-window",
    "prefix sum": "prefix-sum",
    "logic building": "array",
    "hashing": "hash-table",
    "linked-list": "linked-list",
    "stack": "stack",
    "queue": "queue",
    "stack / queues": "stack",
    "binary trees": "tree",
    "binary search trees": "binary-search-tree",
    "heaps": "heap-priority-queue",
    "graphs": "graph",
    "dynamic programming": "dynamic-programming",
    "tries": "trie",
    "recursion": "recursion",
    "sorting": "sorting"
}

TOPIC_TAG_QUERY = """
query getTopicTag($slug: String!) {
  topicTag(slug: $slug) {
    name
    questions {
      title
      titleSlug
      difficulty
    }
  }
}
"""

class LeetCodeAdapter(IProblemSource):
    def __init__(self, ai_tutor: Optional[IAITutor] = None):
        self.ai_tutor = ai_tutor

    def get_all_problems(self) -> List[Problem]:
        return []

    def get_problem_by_id(self, problem_id: str) -> Optional[Problem]:
        return None

    async def fetch_extra_by_pattern(self, pattern_name: str, topic: str, limit: int = 3) -> List[Problem]:
        clean_pat = pattern_name.strip().lower()
        clean_top = topic.strip().lower()

        # Determine best LeetCode tag: check pattern first, then topic
        tag = None
        for k, v in TOPIC_TAG_MAP.items():
            if k in clean_pat:
                tag = v
                break

        if not tag:
            for k, v in TOPIC_TAG_MAP.items():
                if k in clean_top:
                    tag = v
                    break

        if not tag:
            tag = "binary-search" if "binary" in clean_top else "array"

        payload = {
            "query": TOPIC_TAG_QUERY,
            "variables": {
                "slug": tag
            }
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com"
        }

        # 1. Try Live LeetCode GraphQL
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(LEETCODE_GRAPHQL_URL, json=payload, headers=headers, timeout=6) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        questions = data.get("data", {}).get("topicTag", {}).get("questions", [])
                        if questions:
                            sample_size = min(limit, len(questions))
                            sampled = random.sample(questions, sample_size)
                            return [
                                Problem(
                                    id=f"extra-{q['titleSlug']}",
                                    order=9999,
                                    title=q["title"],
                                    step=0,
                                    step_title=topic,
                                    topic=pattern_name,
                                    pattern=pattern_name,
                                    difficulty=q.get("difficulty", "Medium"),
                                    platform="leetcode",
                                    url=f"https://leetcode.com/problems/{q['titleSlug']}/",
                                    lc_slug=q["titleSlug"],
                                    duration="20 min"
                                )
                                for q in sampled
                            ]
        except Exception as e:
            print(f"[LeetCodeAdapter Live Error]: {e}")

        # 2. Resilient AI Fallback (Gemini LLM)
        if self.ai_tutor:
            try:
                ai_drills = await self.ai_tutor.generate_drill_problems(pattern_name, topic, count=limit)
                if ai_drills:
                    return [
                        Problem(
                            id=f"extra-ai-{d.get('slug', 'problem')}",
                            order=9999,
                            title=d.get("title", "Practice Problem"),
                            step=0,
                            step_title=topic,
                            topic=pattern_name,
                            pattern=pattern_name,
                            difficulty=d.get("difficulty", "Medium"),
                            platform="leetcode",
                            url=f"https://leetcode.com/problems/{d.get('slug', '')}/",
                            lc_slug=d.get("slug"),
                            duration="20 min"
                        )
                        for d in ai_drills
                    ]
            except Exception as e:
                print(f"[AI Fallback Error]: {e}")

        return []
