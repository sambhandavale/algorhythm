import aiohttp
import random
from typing import List, Optional
from core.models.problem import Problem
from core.interfaces.problem_source import IProblemSource

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

# Pattern to LeetCode tag mappings
PATTERN_TAG_MAP = {
    "on answers": "binary-search",
    "binary search": "binary-search",
    "two pointer": "two-pointers",
    "sliding window": "sliding-window",
    "prefix sum": "prefix-sum",
    "logic building": "array",
    "faqs(medium)": "array",
    "faqs(hard)": "array",
    "fundamentals": "array",
    "learn linked list": "linked-list",
    "hard problems of ll": "linked-list",
    "medium problems of ll": "linked-list",
    "stack": "stack",
    "queue": "queue",
    "monotonic stack": "monotonic-stack",
    "binary trees": "tree",
    "binary search trees": "binary-search-tree",
    "graphs": "graph",
    "dynamic programming": "dynamic-programming",
    "dp on subsequences": "dynamic-programming",
    "dp on strings": "dynamic-programming",
    "dp on stocks": "dynamic-programming",
    "partition dp": "dynamic-programming"
}

# Curated high-yield drill bank for instant matching
CURATED_PATTERN_DRILLS = {
    "on answers": [
        Problem("extra-lc-1011", 9999, "Capacity To Ship Packages Within D Days", 4, "Binary Search", "Binary Search", "On answers", "Medium", "leetcode", "https://leetcode.com/problems/capacity-to-ship-packages-within-d-days/", lc_slug="capacity-to-ship-packages-within-d-days", duration="20 min"),
        Problem("extra-lc-410", 9999, "Split Array Largest Sum", 4, "Binary Search", "Binary Search", "On answers", "Hard", "leetcode", "https://leetcode.com/problems/split-array-largest-sum/", lc_slug="split-array-largest-sum", duration="25 min"),
        Problem("extra-lc-875", 9999, "Koko Eating Bananas", 4, "Binary Search", "Binary Search", "On answers", "Medium", "leetcode", "https://leetcode.com/problems/koko-eating-bananas/", lc_slug="koko-eating-bananas", duration="15 min"),
        Problem("extra-lc-1482", 9999, "Minimum Number of Days to Make m Bouquets", 4, "Binary Search", "Binary Search", "On answers", "Medium", "leetcode", "https://leetcode.com/problems/minimum-number-of-days-to-make-m-bouquets/", lc_slug="minimum-number-of-days-to-make-m-bouquets", duration="20 min")
    ],
    "sliding window": [
        Problem("extra-lc-3", 9999, "Longest Substring Without Repeating Characters", 10, "Sliding Window", "Sliding Window", "Sliding Window", "Medium", "leetcode", "https://leetcode.com/problems/longest-substring-without-repeating-characters/", lc_slug="longest-substring-without-repeating-characters", duration="15 min"),
        Problem("extra-lc-424", 9999, "Longest Repeating Character Replacement", 10, "Sliding Window", "Sliding Window", "Sliding Window", "Medium", "leetcode", "https://leetcode.com/problems/longest-repeating-character-replacement/", lc_slug="longest-repeating-character-replacement", duration="20 min"),
        Problem("extra-lc-76", 9999, "Minimum Window Substring", 10, "Sliding Window", "Sliding Window", "Sliding Window", "Hard", "leetcode", "https://leetcode.com/problems/minimum-window-substring/", lc_slug="minimum-window-substring", duration="30 min")
    ],
    "two pointer": [
        Problem("extra-lc-11", 9999, "Container With Most Water", 3, "Arrays", "Arrays", "Two Pointer", "Medium", "leetcode", "https://leetcode.com/problems/container-with-most-water/", lc_slug="container-with-most-water", duration="15 min"),
        Problem("extra-lc-15", 9999, "3Sum", 3, "Arrays", "Arrays", "Two Pointer", "Medium", "leetcode", "https://leetcode.com/problems/3sum/", lc_slug="3sum", duration="20 min"),
        Problem("extra-lc-42", 9999, "Trapping Rain Water", 3, "Arrays", "Arrays", "Two Pointer", "Hard", "leetcode", "https://leetcode.com/problems/trapping-rain-water/", lc_slug="trapping-rain-water", duration="25 min")
    ]
}

class LeetCodeAdapter(IProblemSource):
    def get_all_problems(self) -> List[Problem]:
        return []

    def get_problem_by_id(self, problem_id: str) -> Optional[Problem]:
        for drills in CURATED_PATTERN_DRILLS.values():
            for p in drills:
                if p.id == problem_id:
                    return p
        return None

    async def fetch_extra_by_pattern(self, pattern_name: str, topic: str, limit: int = 3) -> List[Problem]:
        clean_pat = pattern_name.strip().lower()

        # 1. Check curated bank first
        for key, drills in CURATED_PATTERN_DRILLS.items():
            if key in clean_pat:
                selected = random.sample(drills, min(limit, len(drills)))
                return selected

        # 2. Dynamic LeetCode GraphQL query by tag
        tag = PATTERN_TAG_MAP.get(clean_pat, "array")
        query = """
        query problemsetQuestionList($categorySlug: String, $filters: QuestionListFilterInput) {
          problemsetQuestionList(categorySlug: $categorySlug, filters: $filters) {
            questions {
              title
              titleSlug
              difficulty
            }
          }
        }
        """
        payload = {
            "query": query,
            "variables": {
              "categorySlug": "",
              "filters": {"tags": [tag]}
            }
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(LEETCODE_GRAPHQL_URL, json=payload, headers=headers, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        q_list = data.get("data", {}).get("problemsetQuestionList", {}).get("questions", [])
                        if q_list:
                            sample_size = min(limit, len(q_list))
                            sampled = random.sample(q_list, sample_size)
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
        except Exception:
            pass

        return []
