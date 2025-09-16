import functools
import logging
from collections.abc import Callable
from typing import Any

import hikari
import lightbulb

logger = logging.getLogger(__name__)

# Global bot instance registry (set by bot.py during initialization)
_bot_instance = None


def requires_permission(permission_node: str, error_message: str | None = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(ctx: lightbulb.Context, *args, **kwargs) -> Any:
            # Get bot instance from global registry
            bot = _bot_instance

            # Debug logging
            logger.info(f"Permission check: {ctx.author.username} trying to use command requiring '{permission_node}'")
            logger.debug(f"Bot instance: {type(bot)}, has permission_manager: {hasattr(bot, 'permission_manager') if bot else False}")
            logger.debug(f"Context member: {ctx.member}, is Member: {isinstance(ctx.member, hikari.Member)}")
            logger.debug(f"Guild ID: {ctx.guild_id}")

            # Check if user has permission
            if bot and hasattr(bot, "permission_manager") and isinstance(ctx.member, hikari.Member):
                has_perm = await bot.permission_manager.has_permission(ctx.guild_id, ctx.member, permission_node)

                logger.info(
                    f"Permission result: {ctx.author.username} {'HAS' if has_perm else 'DENIED'} permission '{permission_node}'"
                )

                if not has_perm:
                    error_msg = error_message or f"You don't have the required permission: `{permission_node}`"
                    logger.warning(f"Permission denied: {ctx.author.username} tried to use {permission_node}")
                    await ctx.respond(error_msg, flags=hikari.MessageFlag.EPHEMERAL)
                    return
            else:
                logger.warning("Permission check skipped: No permission manager or not a guild member")

            return await func(ctx, *args, **kwargs)

        # Store metadata for introspection
        wrapper._required_permission = permission_node
        return wrapper

    return decorator


def requires_role(role_ids: int | list[int], error_message: str | None = None) -> Callable:
    if isinstance(role_ids, int):
        role_ids = [role_ids]

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(ctx: lightbulb.Context, *args, **kwargs) -> Any:
            if not isinstance(ctx.member, hikari.Member):
                error_msg = "This command can only be used in servers."
                await ctx.respond(error_msg, flags=hikari.MessageFlag.EPHEMERAL)
                return

            # Check if user has any of the required roles
            user_roles = ctx.member.role_ids
            has_role = any(role_id in user_roles for role_id in role_ids)

            if not has_role:
                error_msg = error_message or "You don't have the required role to use this command."
                await ctx.respond(error_msg, flags=hikari.MessageFlag.EPHEMERAL)
                return

            return await func(ctx, *args, **kwargs)

        # Store metadata for introspection
        wrapper._required_roles = role_ids
        return wrapper

    return decorator


def requires_guild_owner(error_message: str | None = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(ctx: lightbulb.Context, *args, **kwargs) -> Any:
            if not ctx.guild_id:
                error_msg = "This command can only be used in servers."
                await ctx.respond(error_msg, flags=hikari.MessageFlag.EPHEMERAL)
                return

            guild = ctx.get_guild()
            if not guild or ctx.author.id != guild.owner_id:
                error_msg = error_message or "Only the server owner can use this command."
                await ctx.respond(error_msg, flags=hikari.MessageFlag.EPHEMERAL)
                return

            return await func(ctx, *args, **kwargs)

        # Store metadata for introspection
        wrapper._requires_guild_owner = True
        return wrapper

    return decorator


def requires_bot_permissions(*permissions: hikari.Permissions) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(ctx: lightbulb.Context, *args, **kwargs) -> Any:
            if not ctx.guild_id:
                return await func(ctx, *args, **kwargs)

            # Get bot's permissions in the guild
            guild = ctx.get_guild()
            if not guild:
                return await func(ctx, *args, **kwargs)

            bot_member = guild.get_member(ctx.client.get_me().id)
            if not bot_member:
                await ctx.respond(
                    "I couldn't determine my permissions in this server.",
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            # Check if bot has required permissions
            missing_perms = []
            for perm in permissions:
                if not (bot_member.permissions & perm):
                    missing_perms.append(perm.name)

            if missing_perms:
                perm_list = ", ".join(f"`{perm}`" for perm in missing_perms)
                await ctx.respond(
                    f"I'm missing the following permissions: {perm_list}",
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            return await func(ctx, *args, **kwargs)

        # Store metadata for introspection
        wrapper._required_bot_permissions = permissions
        return wrapper

    return decorator
