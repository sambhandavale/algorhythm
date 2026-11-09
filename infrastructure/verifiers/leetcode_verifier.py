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
