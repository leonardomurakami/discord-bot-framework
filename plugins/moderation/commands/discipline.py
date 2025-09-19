from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command

from ..config import (
    ERROR_COLOR,
    MODNOTE_ACTIONS,
    NOTICE_COLOR,
    NOTE_DISPLAY_LIMIT,
    SUCCESS_COLOR,
    WARN_DM_COLOR,
    WARNING_COLOR,
    WARN_DISPLAY_LIMIT,
)

if TYPE_CHECKING:
    from ..moderation_plugin import ModerationPlugin

logger = logging.getLogger(__name__)


def setup_discipline_commands(plugin: "ModerationPlugin") -> list[Callable[..., Any]]:
    """Register warning and moderator note commands."""

    @command(
        name="warn",
        description="Issue a warning to a member",
        permission_node="moderation.warn",
        arguments=[
            CommandArgument(
                "member",
                hikari.OptionType.USER,
                "Member to warn",
            ),
            CommandArgument(
                "reason",
                hikari.OptionType.STRING,
                "Reason for the warning",
                required=False,
                default="No reason provided",
            ),
        ],
    )
    async def warn_member(ctx: lightbulb.Context, member: hikari.User, reason: str = "No reason provided") -> None:
        try:
            if not ctx.guild_id:
                embed = plugin.create_embed(
                    title="❌ Server Only",
                    description="This command can only be used in a server.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if member.id in {ctx.author.id, ctx.client.get_me().id}:
                embed = plugin.create_embed(
                    title="❌ Invalid Target",
                    description="You cannot warn that member.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            current_warnings = await plugin.get_setting(ctx.guild_id, "user_warnings", {})
            user_warnings = current_warnings.get(str(member.id), [])

            warning_data = {
                "reason": reason,
                "moderator": ctx.author.id,
                "timestamp": int(datetime.now().timestamp()),
                "id": len(user_warnings) + 1,
            }
            user_warnings.append(warning_data)
            current_warnings[str(member.id)] = user_warnings
            await plugin.set_setting(ctx.guild_id, "user_warnings", current_warnings)

            try:
                dm_channel = await member.fetch_dm_channel()
                embed_dm = plugin.create_embed(
                    title="⚠️ You have been warned",
                    description=f"You have been warned in **{ctx.get_guild().name}**",
                    color=WARN_DM_COLOR,
                )
                embed_dm.add_field("Reason", reason, inline=False)
                embed_dm.add_field("Moderator", f"{ctx.author.mention}", inline=True)
                embed_dm.add_field("Warning Count", f"{len(user_warnings)}", inline=True)
                await dm_channel.send(embed=embed_dm)
            except Exception:
                pass

            embed = plugin.create_embed(
                title="✅ Member Warned",
                description=f"{member.mention} has been warned.",
                color=WARNING_COLOR,
            )
            embed.add_field("Reason", reason, inline=False)
            embed.add_field("Moderator", ctx.author.mention, inline=True)
            embed.add_field("Total Warnings", f"{len(user_warnings)}", inline=True)
            embed.add_field("Warning ID", f"#{warning_data['id']}", inline=True)

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "warn", True)

        except Exception as exc:
            logger.error("Error in warn command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to warn member: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "warn", False, str(exc))

    @command(
        name="warnings",
        description="View warnings for a member",
        aliases=["warns"],
        permission_node="moderation.warn",
        arguments=[
            CommandArgument(
                "member",
                hikari.OptionType.USER,
                "Member to view warnings for",
                required=False,
            ),
        ],
    )
    async def view_warnings(ctx: lightbulb.Context, member: hikari.User | None = None) -> None:
        try:
            if not ctx.guild_id:
                embed = plugin.create_embed(
                    title="❌ Server Only",
                    description="This command can only be used in a server.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            target_member = member or ctx.author
            current_warnings = await plugin.get_setting(ctx.guild_id, "user_warnings", {})
            user_warnings = current_warnings.get(str(target_member.id), [])

            if not user_warnings:
                embed = plugin.create_embed(
                    title="📋 No Warnings",
                    description=f"{target_member.mention} has no warnings.",
                    color=SUCCESS_COLOR,
                )
            else:
                embed = plugin.create_embed(
                    title=f"⚠️ Warnings for {getattr(target_member, 'display_name', target_member.username)}",
                    description=f"Total warnings: **{len(user_warnings)}**",
                    color=WARNING_COLOR,
                )

                recent_warnings = user_warnings[-WARN_DISPLAY_LIMIT:]
                for warning in recent_warnings:
                    moderator_id = warning.get("moderator", "Unknown")
                    timestamp = warning.get("timestamp", 0)
                    reason = warning.get("reason", "No reason provided")
                    warning_id = warning.get("id", "Unknown")

                    embed.add_field(
                        f"Warning #{warning_id}",
                        f"**Reason:** {reason}\n**Moderator:** <@{moderator_id}>\n**Date:** <t:{timestamp}:f>",
                        inline=False,
                    )

                if len(user_warnings) > WARN_DISPLAY_LIMIT:
                    embed.set_footer(
                        f"Showing {WARN_DISPLAY_LIMIT} most recent warnings out of {len(user_warnings)} total"
                    )

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "warnings", True)

        except Exception as exc:
            logger.error("Error in warnings command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to retrieve warnings: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "warnings", False, str(exc))

    @command(
        name="modnote",
        description="Add or view private moderator notes on users",
        permission_node="moderation.warn",
        arguments=[
            CommandArgument(
                "action",
                hikari.OptionType.STRING,
                "Action: add, view, or clear",
            ),
            CommandArgument(
                "member",
                hikari.OptionType.USER,
                "Member to add note for",
            ),
            CommandArgument(
                "note",
                hikari.OptionType.STRING,
                "Note content (required for 'add' action)",
                required=False,
            ),
        ],
    )
    async def mod_note(ctx: lightbulb.Context, action: str, member: hikari.User, note: str | None = None) -> None:
        try:
            if not ctx.guild_id:
                embed = plugin.create_embed(
                    title="❌ Server Only",
                    description="This command can only be used in a server.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            action = action.lower().strip()
            if action not in MODNOTE_ACTIONS:
                embed = plugin.create_embed(
                    title="❌ Invalid Action",
                    description="Valid actions are: `add`, `view`, `clear`",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            current_notes = await plugin.get_setting(ctx.guild_id, "user_notes", {})
            user_notes = current_notes.get(str(member.id), [])

            if action == "add":
                if not note:
                    embed = plugin.create_embed(
                        title="❌ Missing Note",
                        description="Please provide a note to add.",
                        color=ERROR_COLOR,
                    )
                    await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                note_data = {
                    "note": note,
                    "moderator": ctx.author.id,
                    "timestamp": int(datetime.now().timestamp()),
                    "id": len(user_notes) + 1,
                }
                user_notes.append(note_data)
                current_notes[str(member.id)] = user_notes
                await plugin.set_setting(ctx.guild_id, "user_notes", current_notes)

                embed = plugin.create_embed(
                    title="✅ Note Added",
                    description=f"Added moderator note for {member.mention}",
                    color=SUCCESS_COLOR,
                )
                embed.add_field("Note", note, inline=False)
                embed.add_field("Total Notes", f"{len(user_notes)}", inline=True)

            elif action == "view":
                if not user_notes:
                    embed = plugin.create_embed(
                        title="📋 No Notes",
                        description=f"No moderator notes found for {member.mention}.",
                        color=NOTICE_COLOR,
                    )
                else:
                    embed = plugin.create_embed(
                        title=f"📝 Moderator Notes for {getattr(member, 'display_name', member.username)}",
                        description=f"Total notes: **{len(user_notes)}**",
                        color=NOTICE_COLOR,
                    )

                    recent_notes = user_notes[-NOTE_DISPLAY_LIMIT:]
                    for note_data in recent_notes:
                        moderator_id = note_data.get("moderator", "Unknown")
                        timestamp = note_data.get("timestamp", 0)
                        note_content = note_data.get("note", "No content")
                        note_id = note_data.get("id", "Unknown")

                        embed.add_field(
                            f"Note #{note_id}",
                            f"**Content:** {note_content}\n**By:** <@{moderator_id}>\n**Date:** <t:{timestamp}:f>",
                            inline=False,
                        )

                    if len(user_notes) > NOTE_DISPLAY_LIMIT:
                        embed.set_footer(
                            f"Showing {NOTE_DISPLAY_LIMIT} most recent notes out of {len(user_notes)} total"
                        )

            else:  # clear
                if user_notes:
                    current_notes[str(member.id)] = []
                    await plugin.set_setting(ctx.guild_id, "user_notes", current_notes)

                    embed = plugin.create_embed(
                        title="✅ Notes Cleared",
                        description=f"Cleared all moderator notes for {member.mention}",
                        color=SUCCESS_COLOR,
                    )
                    embed.add_field("Notes Removed", f"{len(user_notes)}", inline=True)
                else:
                    embed = plugin.create_embed(
                        title="📋 No Notes",
                        description=f"No moderator notes found for {member.mention}.",
                        color=NOTICE_COLOR,
                    )

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "modnote", True)

        except Exception as exc:
            logger.error("Error in modnote command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to manage moderator note: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "modnote", False, str(exc))

    return [warn_member, view_warnings, mod_note]

