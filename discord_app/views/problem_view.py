import discord
from discord.ui import View, Button, Modal, TextInput
from datetime import datetime
from typing import Optional
from core.models.problem import Problem
from core.models.user import ProgressRecord
from core.services.study_manager import StudyManager
from core.services.streak_service import StreakService
from core.interfaces.verifier import ISubmissionVerifier
from core.interfaces.ai_tutor import IAITutor

DIFF_BADGES = {
    "easy": "🟢 Easy",
    "medium": "🟡 Medium",
    "hard": "🔴 Hard",
}

DIFF_COLORS = {
    "easy": discord.Color.green(),
    "medium": discord.Color.gold(),
    "hard": discord.Color.red(),
}

def create_problem_embed(
    problem: Problem,
    user_streak: int = 0,
    is_solved: bool = False,
    pattern_progress_text: Optional[str] = None
) -> discord.Embed:
    diff_key = (problem.difficulty or "medium").lower()
    badge = DIFF_BADGES.get(diff_key, f"⚪ {problem.difficulty}")
    color = discord.Color.purple() if is_solved else DIFF_COLORS.get(diff_key, discord.Color.blue())

    status_prefix = "✅ [SOLVED] " if is_solved else "🎯 "
    embed = discord.Embed(
        title=f"{status_prefix}{problem.title}",
        url=problem.url or "https://takeuforward.org",
        color=color
    )

    # Core meta line
    lines = [
        f"{badge}  •  📚 **{problem.step_title}** › `{problem.pattern}`",
        f"⏱️ Est: `{problem.duration or '15 min'}`  •  🔥 Streak: **{user_streak} Days**"
    ]

    # Pattern Progress
    if pattern_progress_text:
        lines.append(f"📊 **Pattern Progress**: `{pattern_progress_text}`")

    # Clean inline markdown resource links
    links = []
    if problem.url:
        links.append(f"[💻 Solve on {problem.platform.capitalize()}]({problem.url})")
    if problem.article:
        links.append(f"[📖 Article]({problem.article})")
    if problem.video:
        links.append(f"[🎥 Video]({problem.video})")

    if links:
        lines.append("\n" + "  •  ".join(links))

    embed.description = "\n".join(lines)
    embed.set_footer(text=f"Striver's A2Z DSA • ID: {problem.id}")
    return embed

class HintModal(Modal, title="Ask AI for a Socratic Hint"):
    query = TextInput(
        label="What is your current thought or approach?",
        style=discord.TextStyle.paragraph,
        placeholder="e.g., I'm considering using Two Pointers, but the array has negative numbers...",
        required=True,
        max_length=500
    )

    def __init__(self, ai_tutor: IAITutor, problem: Problem):
        super().__init__()
        self.ai_tutor = ai_tutor
        self.problem = problem

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        hint = await self.ai_tutor.get_socratic_hint(self.problem, self.query.value)
        embed = discord.Embed(
            title=f"💡 Socratic Hint: {self.problem.title}",
            description=hint,
            color=discord.Color.teal()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

class ProblemCardView(View):
    """
    Sleek minimalist action bar with at most 4 primary buttons in a single row.
    """
    def __init__(
        self,
        problem: Problem,
        user_id: int,
        study_manager: StudyManager,
        streak_service: StreakService,
        verifier: ISubmissionVerifier,
        ai_tutor: Optional[IAITutor] = None
    ):
        super().__init__(timeout=None)
        self.problem = problem
        self.user_id = user_id
        self.study_manager = study_manager
        self.streak_service = streak_service
        self.verifier = verifier
        self.ai_tutor = ai_tutor
        self._setup_buttons()

    def _setup_buttons(self):
        # 1. Verify LeetCode (Primary Action)
        if self.problem.lc_slug:
            btn_verify = Button(
                label="Verify LeetCode",
                style=discord.ButtonStyle.primary,
                emoji="⚡",
                custom_id=f"verify_{self.problem.id}"
            )
            btn_verify.callback = self.on_verify_click
            self.add_item(btn_verify)

        # 2. Mark Done (Success Action)
        btn_manual = Button(
            label="Mark Done",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id=f"manual_{self.problem.id}"
        )
        btn_manual.callback = self.on_manual_click
        self.add_item(btn_manual)

        # 3. Socratic AI Hint (Helper Action)
        if self.ai_tutor:
            btn_hint = Button(
                label="Hint",
                style=discord.ButtonStyle.secondary,
                emoji="💡",
                custom_id=f"hint_{self.problem.id}"
            )
            btn_hint.callback = self.on_hint_click
            self.add_item(btn_hint)

        # 4. Skip (Navigation Action)
        btn_skip = Button(
            label="Skip",
            style=discord.ButtonStyle.secondary,
            emoji="⏩",
            custom_id=f"skip_{self.problem.id}"
        )
        btn_skip.callback = self.on_skip_click
        self.add_item(btn_skip)

    async def on_verify_click(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This card is for another user!", ephemeral=True)
            return

        user_data = await self.study_manager.repository.get_user(self.user_id)
        handle = user_data.leetcode_username if user_data else None

        if not handle:
            await interaction.response.send_message(
                "⚠️ You haven't linked your LeetCode handle yet! Run `/set-handle <username>` first.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        is_verified, msg = await self.verifier.verify(handle, self.problem)
        if is_verified:
            record = ProgressRecord(
                user_id=self.user_id,
                problem_id=self.problem.id,
                slug=self.problem.lc_slug or self.problem.id,
                status="SOLVED",
                solved_at=datetime.now().isoformat(),
                source="LEETCODE"
            )
            await self.study_manager.repository.save_progress(record)
            streak, longest = await self.streak_service.update_user_streak(self.user_id)

            updated_embed = create_problem_embed(self.problem, user_streak=streak, is_solved=True)
            await interaction.message.edit(embed=updated_embed, view=None)

            await interaction.followup.send(
                f"🎉 **Verified!** Great work solving `{self.problem.title}` on LeetCode!\n"
                f"🔥 Current Streak: **{streak} Days** (Record: {longest} Days)",
                ephemeral=True
            )
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    async def on_manual_click(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This card is for another user!", ephemeral=True)
            return

        record = ProgressRecord(
            user_id=self.user_id,
            problem_id=self.problem.id,
            slug=self.problem.lc_slug or self.problem.id,
            status="SOLVED",
            solved_at=datetime.now().isoformat(),
            source="MANUAL"
        )
        await self.study_manager.repository.save_progress(record)
        streak, longest = await self.streak_service.update_user_streak(self.user_id)

        updated_embed = create_problem_embed(self.problem, user_streak=streak, is_solved=True)
        await interaction.message.edit(embed=updated_embed, view=None)

        await interaction.response.send_message(
            f"✅ Marked `{self.problem.title}` as solved!\n"
            f"🔥 Current Streak: **{streak} Days** (Record: {longest} Days)",
            ephemeral=True
        )

    async def on_hint_click(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This card is for another user!", ephemeral=True)
            return
        if not self.ai_tutor:
            await interaction.response.send_message("AI Tutor is not configured.", ephemeral=True)
            return

        await interaction.response.send_modal(HintModal(self.ai_tutor, self.problem))

    async def on_skip_click(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This card is for another user!", ephemeral=True)
            return

        record = ProgressRecord(
            user_id=self.user_id,
            problem_id=self.problem.id,
            slug=self.problem.lc_slug or self.problem.id,
            status="SKIPPED",
            solved_at=datetime.now().isoformat(),
            source="MANUAL"
        )
        await self.study_manager.repository.save_progress(record)
        await interaction.response.send_message(
            f"⏩ Skipped `{self.problem.title}`. Run `/next` or `/daily` to get your next problem!",
            ephemeral=True
        )
