import aiohttp
from typing import Optional, List, Dict, Tuple

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com"
}

RECENT_SUBMISSIONS_QUERY = """
query getRecentSubmissions($username: String!, $limit: Int!) {
  recentSubmissionList(username: $username, limit: $limit) {
    title
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

class LeetCodeService:
    @staticmethod
    async def get_recent_submissions(username: str, limit: int = 20) -> List[dict]:
        """Fetches the latest public submissions for a LeetCode user."""
        payload = {
            "query": RECENT_SUBMISSIONS_QUERY,
            "variables": {
                "username": username,
                "limit": limit
            }
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(LEETCODE_GRAPHQL_URL, json=payload, headers=HEADERS, timeout=10) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    return data.get("data", {}).get("recentSubmissionList") or []
            except Exception:
                return []

    @staticmethod
    async def verify_problem_solved(username: str, target_slug: str) -> Tuple[bool, Optional[dict]]:
        """
        Checks whether the user has an 'Accepted' submission for target_slug in their recent submissions.
        Returns: (is_solved, matching_submission)
        """
        submissions = await LeetCodeService.get_recent_submissions(username, limit=20)
        target_clean = target_slug.strip().lower()

        for sub in submissions:
            sub_slug = sub.get("titleSlug", "").strip().lower()
            status = sub.get("statusDisplay", "")
            if sub_slug == target_clean and status.lower() == "accepted":
                return True, sub

        return False, None

    @staticmethod
    async def get_user_stats(username: str) -> Optional[dict]:
        """Fetches user ranking and problem counts (Easy/Medium/Hard)."""
        payload = {
            "query": USER_PROFILE_QUERY,
            "variables": {
                "username": username
            }
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(LEETCODE_GRAPHQL_URL, json=payload, headers=HEADERS, timeout=10) as resp:
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
