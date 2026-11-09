import discord
from core.models.pattern import PatternNote

def create_pattern_notes_embed(note: PatternNote) -> discord.Embed:
    embed = discord.Embed(
        title=f"🎓 Pattern Primer: {note.pattern_name}",
        description=f"**Topic**: `{note.topic}`\n\n💡 **Core Intuition**\n{note.core_intuition}",
        color=discord.Color.teal()
    )

    if note.template_code:
        code_block = f"```python\n{note.template_code}\n```"
        embed.add_field(name="📐 Standard Blueprint / Template", value=code_block, inline=False)

    if note.key_questions:
        q_text = "\n".join([f"• {q}" for q in note.key_questions])
        embed.add_field(name="❓ Mental Checklist to Ask Yourself", value=q_text, inline=False)

    if note.common_pitfalls:
        pit_text = "\n".join([f"⚠️ {p}" for p in note.common_pitfalls])
        embed.add_field(name="🚨 Common Traps & Edge Cases", value=pit_text, inline=False)

    embed.set_footer(text="Master the pattern, not just the problem!")
    return embed
