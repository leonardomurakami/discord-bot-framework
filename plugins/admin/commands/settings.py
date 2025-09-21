from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

import hikari
import lightbulb

from bot.database.models import Guild
from bot.plugins.commands import CommandArgument, command
from sqlalchemy import select

from ..config import (
    AUTOROLE_VALID_ACTIONS,
    ERROR_COLOR,
    PERMISSION_LIST_LIMIT,
    PREFIX_DISALLOWED_CHARS,
    PREFIX_MAX_LENGTH,
    SERVER_INFO_COLOR,
    SUCCESS_COLOR,
    WARNING_COLOR,
)

if TYPE_CHECKING:
    from ..admin_plugin import AdminPlugin

logger = logging.getLogger(__name__)


def setup_settings_commands(plugin: "AdminPlugin") -> list[Callable[..., Any]]:
    """Register admin configuration commands."""

    @command(
        name="permission",
        description="Manage role permissions",
        permission_node="admin.permissions",
        arguments=[
            CommandArgument(
                "action",
                hikari.OptionType.STRING,
                "Action: grant, revoke, or list",
                required=False,
                default="list",
            ),
            CommandArgument(
                "role",
                hikari.OptionType.ROLE,
                "Role to manage permissions for",
                required=False,
            ),
            CommandArgument(
                "permission",
                hikari.OptionType.STRING,
                "Permission node to grant/revoke",
                required=False,
            ),
        ],
    )
    async def manage_permissions(ctx: lightbulb.Context, action: str = "list", role: hikari.Role | None = None, permission: str | None = None) -> None:

        try:
            if action == "list":
                if role:
                    permissions = await plugin.bot.permission_manager.get_role_permissions(ctx.guild_id, role.id)
                    if permissions:
                        perm_list = "\n".join(f"• {perm}" for perm in permissions)
                        embed = plugin.create_embed(
                            title=f"🔑 Permissions for @{role.name}",
                            description=perm_list,
                            color=SERVER_INFO_COLOR,
                        )
                    else:
                        embed = plugin.create_embed(
                            title=f"🔑 Permissions for @{role.name}",
                            description="No permissions granted.",
                            color=WARNING_COLOR,
                        )
                else:
                    all_perms = await plugin.bot.permission_manager.get_all_permissions()
                    if all_perms:
                        perm_list = "\n".join(
                            f"• `{perm.node}` - {perm.description}" for perm in all_perms[:PERMISSION_LIST_LIMIT]
                        )
                        if len(all_perms) > PERMISSION_LIST_LIMIT:
                            perm_list += f"\n... and {len(all_perms) - PERMISSION_LIST_LIMIT} more"
                        embed = plugin.create_embed(
                            title="🔑 Available Permissions",
                            description=perm_list,
                            color=SERVER_INFO_COLOR,
                        )
                    else:
                        embed = plugin.create_embed(
                            title="🔑 Available Permissions",
                            description="No permissions found.",
                            color=WARNING_COLOR,
                        )

            elif action in {"grant", "revoke"}:
                if not role or not permission:
                    embed = plugin.create_embed(
                        title="❌ Invalid Parameters",
                        description=f"Both role and permission are required for {action} action.",
                        color=ERROR_COLOR,
                    )
                else:
                    if action == "grant":
                        success = await plugin.bot.permission_manager.grant_permission(ctx.guild_id, role.id, permission)
                        action_text = "granted to"
                    else:
                        success = await plugin.bot.permission_manager.revoke_permission(ctx.guild_id, role.id, permission)
                        action_text = "revoked from"

                    if success:
                        embed = plugin.create_embed(
                            title="✅ Permission Updated",
                            description=f"Permission `{permission}` has been {action_text} @{role.name}",
                            color=SUCCESS_COLOR,
                        )
                    else:
                        embed = plugin.create_embed(
                            title="❌ Permission Update Failed",
                            description="Failed to update permission. Check if permission exists.",
                            color=ERROR_COLOR,
                        )
            else:
                embed = plugin.create_embed(
                    title="❌ Invalid Action",
                    description="Valid actions are: grant, revoke, list",
                    color=ERROR_COLOR,
                )

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "permission", True)

        except Exception as exc:
            logger.error("Error in permission command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"An error occurred: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "permission", False, str(exc))

    @command(
        name="prefix",
        description="View or set the bot's prefix for this server",
        permission_node="admin.config",
        arguments=[
            CommandArgument(
                "new_prefix",
                hikari.OptionType.STRING,
                "New prefix to set (leave empty to view current prefix)",
                required=False,
            )
        ],
    )
    async def manage_prefix(ctx: lightbulb.Context, new_prefix: str | None = None) -> None:
        try:
            if not ctx.guild_id:
                embed = plugin.create_embed(
                    title="❌ Server Only",
                    description="This command can only be used in a server.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if new_prefix is None:
                current_prefix = await plugin.bot.get_guild_prefix(ctx.guild_id)
                embed = plugin.create_embed(
                    title="🔧 Current Server Prefix",
                    description=f"The current prefix for this server is: `{current_prefix}`",
                    color=SERVER_INFO_COLOR,
                )
                embed.add_field(
                    "Usage",
                    f"Use `{current_prefix}help` to see all commands\nUse `/prefix <new_prefix>` to change the prefix",
                    inline=False,
                )
            else:
                if len(new_prefix) > PREFIX_MAX_LENGTH:
                    embed = plugin.create_embed(
                        title="❌ Invalid Prefix",
                        description=f"Prefix must be {PREFIX_MAX_LENGTH} characters or less.",
                        color=ERROR_COLOR,
                    )
                    await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                if len(new_prefix.strip()) == 0:
                    embed = plugin.create_embed(
                        title="❌ Invalid Prefix",
                        description="Prefix cannot be empty or only whitespace.",
                        color=ERROR_COLOR,
                    )
                    await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                if any(char in new_prefix for char in PREFIX_DISALLOWED_CHARS):
                    embed = plugin.create_embed(
                        title="❌ Invalid Prefix",
                        description="Prefix cannot contain quotes, backticks, or whitespace characters.",
                        color=ERROR_COLOR,
                    )
                    await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                async with plugin.bot.db.session() as session:
                    result = await session.execute(select(Guild).where(Guild.id == ctx.guild_id))
                    guild = result.scalar_one_or_none()

                    if not guild:
                        guild_obj = ctx.get_guild()
                        guild = Guild(
                            id=ctx.guild_id,
                            name=guild_obj.name if guild_obj else "Unknown",
                            prefix=new_prefix,
                        )
                        session.add(guild)
                    else:
                        guild.prefix = new_prefix

                    await session.commit()

                embed = plugin.create_embed(
                    title="✅ Prefix Updated",
                    description=f"Server prefix has been changed to: `{new_prefix}`",
                    color=SUCCESS_COLOR,
                )
                embed.add_field(
                    "Usage",
                    f"Use `{new_prefix}help` to see all commands",
                    inline=False,
                )
                embed.add_field("Changed by", ctx.author.mention, inline=True)

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "prefix", True)

        except Exception as exc:
            logger.error("Error in prefix command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to manage prefix: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "prefix", False, str(exc))

    @command(
        name="autorole",
        description="Configure roles automatically assigned to new members",
        permission_node="admin.config",
        arguments=[
            CommandArgument(
                "action",
                hikari.OptionType.STRING,
                "Action: add, remove, list, or clear",
            ),
            CommandArgument(
                "role",
                hikari.OptionType.ROLE,
                "Role to add/remove (not needed for list/clear)",
                required=False,
            ),
        ],
    )
    async def autorole(ctx: lightbulb.Context, action: str, role: hikari.Role | None = None) -> None:
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

            current_autoroles = await plugin.get_setting(ctx.guild_id, "autoroles", [])

            if action == "list":
                if not current_autoroles:
                    embed = plugin.create_embed(
                        title="📋 Auto Roles",
                        description="No auto roles are currently configured.",
                        color=SERVER_INFO_COLOR,
                    )
                else:
                    role_mentions: list[str] = []
                    for role_id in current_autoroles:
                        try:
                            role_obj = ctx.get_guild().get_role(role_id)
                            if role_obj:
                                role_mentions.append(role_obj.mention)
                        except Exception:
                            pass

                    if role_mentions:
                        embed = plugin.create_embed(
                            title="📋 Auto Roles",
                            description="New members automatically receive:\n" + "\n".join(f"• {r}" for r in role_mentions),
                            color=SERVER_INFO_COLOR,
                        )
                    else:
                        embed = plugin.create_embed(
                            title="📋 Auto Roles",
                            description="No valid auto roles found (they may have been deleted).",
                            color=WARNING_COLOR,
                        )

            elif action == "clear":
                await plugin.set_setting(ctx.guild_id, "autoroles", [])
                embed = plugin.create_embed(
                    title="✅ Auto Roles Cleared",
                    description="All auto roles have been removed.",
                    color=SUCCESS_COLOR,
                )

            elif action in {"add", "remove"}:
                if not role:
                    embed = plugin.create_embed(
                        title="❌ Missing Role",
                        description=f"Please specify a role to {action}.",
                        color=ERROR_COLOR,
                    )
                    await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                guild = ctx.get_guild()
                bot_id = plugin.bot.hikari_bot.get_me().id
                bot_member = guild.get_member(bot_id) if guild else None

                if not bot_member:
                    embed = plugin.create_embed(
                        title="❌ Bot Permission Error",
                        description="Cannot verify bot permissions.",
                        color=ERROR_COLOR,
                    )
                    await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                bot_role_ids = bot_member.role_ids or []
                bot_roles = [guild.get_role(rid) for rid in bot_role_ids] if guild else []
                bot_roles = [r for r in bot_roles if r is not None]
                bot_top_role_position = max((r.position for r in bot_roles), default=-1)

                if role.position >= bot_top_role_position and bot_roles:
                    embed = plugin.create_embed(
                        title="❌ Role Hierarchy Error",
                        description=f"I cannot assign {role.mention} because it's higher than or equal to my highest role.",
                        color=ERROR_COLOR,
                    )
                    await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                if action == "add":
                    if role.id in current_autoroles:
                        embed = plugin.create_embed(
                            title="❌ Already Configured",
                            description=f"{role.mention} is already an auto role.",
                            color=ERROR_COLOR,
                        )
                    else:
                        current_autoroles.append(role.id)
                        await plugin.set_setting(ctx.guild_id, "autoroles", current_autoroles)
                        embed = plugin.create_embed(
                            title="✅ Auto Role Added",
                            description=f"{role.mention} will now be automatically assigned to new members.",
                            color=SUCCESS_COLOR,
                        )

                else:  # remove
                    if role.id not in current_autoroles:
                        embed = plugin.create_embed(
                            title="❌ Not Configured",
                            description=f"{role.mention} is not an auto role.",
                            color=ERROR_COLOR,
                        )
                    else:
                        current_autoroles.remove(role.id)
                        await plugin.set_setting(ctx.guild_id, "autoroles", current_autoroles)
                        embed = plugin.create_embed(
                            title="✅ Auto Role Removed",
                            description=f"{role.mention} will no longer be automatically assigned to new members.",
                            color=SUCCESS_COLOR,
                        )

            else:
                embed = plugin.create_embed(
                    title="❌ Invalid Action",
                    description="Valid actions are: `add`, `remove`, `list`, `clear`",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "autorole", True)

        except Exception as exc:
            logger.error("Error in autorole command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to manage auto roles: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "autorole", False, str(exc))

    return [manage_permissions, manage_prefix, autorole]

