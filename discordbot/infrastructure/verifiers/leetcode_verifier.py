import aiohttp
from typing import Tuple, Optional
from core.models.problem import Problem
from core.interfaces.verifier import ISubmissionVerifier

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

RECENT_SUBMISSIONS_QUERY = """
query getRecentSubmissions($username: String!, $limit: Int!) {
  recentSubmissionList(username: $username, limit: $limit) {
    titleSlug
    statusDisplay
    timestamp
  }
}
"""

USER_PROFILE_QUERY = """
query getUserProfile($username: String!) {
  matchedUser(username: $username) {
    username
    profile {
      realName
      ranking
    }
    submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
  }
}
"""

class LeetCodeVerifier(ISubmissionVerifier):
    async def verify(self, username: str, problem: Problem) -> Tuple[bool, Optional[str]]:
        if not problem.lc_slug:
            return False, "This problem does not have a LeetCode slug configured."

        payload = {
            "query": RECENT_SUBMISSIONS_QUERY,
            "variables": {
                "username": username,
                "limit": 20
            }
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(LEETCODE_GRAPHQL_URL, json=payload, headers=headers, timeout=8) as resp:
                    if resp.status != 200:
                        return False, "Could not contact LeetCode API."

                    data = await resp.json()
                    submissions = data.get("data", {}).get("recentSubmissionList") or []

                    target = problem.lc_slug.strip().lower()
                    for sub in submissions:
                        if sub.get("titleSlug", "").strip().lower() == target:
                            if sub.get("statusDisplay", "").lower() == "accepted":
                                return True, "Accepted"

                    return False, f"No 'Accepted' submission found for '{problem.lc_slug}' in your last 20 submissions."
        except Exception as e:
            return False, f"Verification request failed: {e}"

    @staticmethod
    async def get_user_stats(username: str) -> Optional[dict]:
        """Fetches user ranking and problem counts (Easy/Medium/Hard)."""
        payload = {
            "query": USER_PROFILE_QUERY,
            "variables": {
                "username": username
            }
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(LEETCODE_GRAPHQL_URL, json=payload, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    matched = data.get("data", {}).get("matchedUser")
                    if not matched:
                        return None

                    stats = {}
                    for item in matched.get("submitStatsGlobal", {}).get("acSubmissionNum", []):
                        stats[item.get("difficulty")] = item.get("count", 0)

                    return {
                        "username": matched.get("username"),
                        "ranking": matched.get("profile", {}).get("ranking"),
                        "total_solved": stats.get("All", 0),
                        "easy": stats.get("Easy", 0),
                        "medium": stats.get("Medium", 0),
                        "hard": stats.get("Hard", 0)
                    }
        except Exception:
            return None
