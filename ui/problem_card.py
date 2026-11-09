import discord
from discord.ui import View, Button
from datetime import date
from typing import Optional
from database.db import Database
from services.sheet_manager import SheetManager
from services.leetcode import LeetCodeService

DIFFICULTY_COLORS = {
    "easy": discord.Color.green(),
    "medium": discord.Color.gold(),
    "hard": discord.Color.red(),
}

def create_problem_embed(problem: dict, user_streak: int = 0, is_solved: bool = False) -> discord.Embed:
    diff_raw = (problem.get("difficulty") or "Medium").lower()
    color = discord.Color.purple() if is_solved else DIFFICULTY_COLORS.get(diff_raw, discord.Color.blue())

    status_tag = " [SOLVED ✅]" if is_solved else ""
    embed = discord.Embed(
        title=f"{problem.get('title', 'Unknown Problem')}{status_tag}",
        url=problem.get("url") or "https://takeuforward.org",
        color=color
    )

    step_info = f"Step {problem.get('step', '?')}: {problem.get('stepTitle', 'General')}"
    topic_info = problem.get("topic", "DSA")
    embed.add_field(name="📚 Topic", value=f"**{step_info}**\n↳ `{topic_info}`", inline=True)

    diff_display = problem.get("difficulty") or "Normal"
    embed.add_field(name="⚡ Difficulty", value=f"`{diff_display}`", inline=True)

    duration = problem.get("duration") or "15 min"
    embed.add_field(name="⏱️ Est. Time", value=f"`{duration}`", inline=True)

    streak_display = f"🔥 **{user_streak} Days**" if user_streak > 0 else "Start today!"
    embed.add_field(name="🎯 Your Streak", value=streak_display, inline=True)

    platform = problem.get("platform", "practice").capitalize()
    embed.add_field(name="💻 Platform", value=f"`{platform}`", inline=True)

    embed.set_footer(text=f"Striver's A2Z DSA Sheet • ID: {problem.get('id', 'N/A')}")
    return embed

class ProblemCardView(View):
    def __init__(self, db: Database, sheet_manager: SheetManager, problem: dict, user_id: int):
        super().__init__(timeout=None)
        self.db = db
        self.sheet_manager = sheet_manager
        self.problem = problem
        self.user_id = user_id
        self._add_action_buttons()

    def _add_action_buttons(self):
        # 1. Practice URL button (Link)
        if self.problem.get("url"):
            self.add_item(Button(
                label=f"Solve on {self.problem.get('platform', 'Web').capitalize()}",
                url=self.problem.get("url"),
                style=discord.ButtonStyle.link,
                emoji="💻"
            ))

        # 2. Check LeetCode (Interactive)
        if self.problem.get("lcSlug"):
            btn_verify = Button(
                label="Verify LeetCode",
                style=discord.ButtonStyle.primary,
                emoji="⚡",
                custom_id=f"verify_{self.problem['id']}"
            )
            btn_verify.callback = self.on_verify_click
            self.add_item(btn_verify)

        # 3. Manual Done (Interactive)
        btn_manual = Button(
            label="Mark Done",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id=f"manual_{self.problem['id']}"
        )
        btn_manual.callback = self.on_manual_click
        self.add_item(btn_manual)

        # 4. Skip Button (Interactive)
        btn_skip = Button(
            label="Skip",
            style=discord.ButtonStyle.secondary,
            emoji="⏩",
            custom_id=f"skip_{self.problem['id']}"
        )
        btn_skip.callback = self.on_skip_click
        self.add_item(btn_skip)

        # 5. Striver Article (Link)
        if self.problem.get("article"):
            self.add_item(Button(
                label="Article",
                url=self.problem.get("article"),
                style=discord.ButtonStyle.link,
                emoji="📖"
            ))

        # 6. YouTube Video (Link)
        if self.problem.get("video"):
            self.add_item(Button(
                label="Video",
                url=self.problem.get("video"),
                style=discord.ButtonStyle.link,
                emoji="🎥"
            ))

    async def on_verify_click(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This problem card is for another user!", ephemeral=True)
            return

        user_data = await self.db.get_user(self.user_id)
        handle = user_data.get("leetcode_username") if user_data else None

        if not handle:
            await interaction.response.send_message(
                "⚠️ You haven't linked your LeetCode handle yet! Use `/set-handle <your_leetcode_username>` first.",
                ephemeral=True
            )
            return

        lc_slug = self.problem.get("lcSlug")
        if not lc_slug:
            await interaction.response.send_message(
                "This problem is not on LeetCode. Use the **[Mark Done]** button instead!",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        is_solved, submission = await LeetCodeService.verify_problem_solved(handle, lc_slug)
        if is_solved:
            streak, longest = await self.db.mark_problem_solved(
                self.user_id, self.problem["id"], lc_slug, source="LEETCODE"
            )
            await self.db.schedule_revision(self.user_id, self.problem["id"])

            updated_embed = create_problem_embed(self.problem, user_streak=streak, is_solved=True)
            await interaction.message.edit(embed=updated_embed, view=None)

            await interaction.followup.send(
                f"🎉 **Verified!** Awesome job solving `{self.problem['title']}` on LeetCode!\n"
                f"🔥 Current Streak: **{streak} Days** (Record: {longest} Days)",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ No 'Accepted' submission found for `{lc_slug}` on your profile (`{handle}`).\n"
                f"Please ensure you've submitted the solution on LeetCode, then try again!",
                ephemeral=True
            )

    async def on_manual_click(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This problem card is for another user!", ephemeral=True)
            return

        slug = self.problem.get("lcSlug") or self.problem.get("slug", "unknown")
        streak, longest = await self.db.mark_problem_solved(
            self.user_id, self.problem["id"], slug, source="MANUAL"
        )
        await self.db.schedule_revision(self.user_id, self.problem["id"])

        updated_embed = create_problem_embed(self.problem, user_streak=streak, is_solved=True)
        await interaction.message.edit(embed=updated_embed, view=None)

        await interaction.response.send_message(
            f"✅ Marked `{self.problem['title']}` as solved!\n"
            f"🔥 Current Streak: **{streak} Days** (Record: {longest} Days)",
            ephemeral=True
        )

    async def on_skip_click(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This problem card is for another user!", ephemeral=True)
            return

        slug = self.problem.get("lcSlug") or self.problem.get("slug", "unknown")
        await self.db.mark_problem_skipped(self.user_id, self.problem["id"], slug)

        await interaction.response.send_message(
            f"⏩ Skipped `{self.problem['title']}`. Run `/daily` to get the next problem in sequence!",
            ephemeral=True
        )
