from __future__ import annotations

import logging
from typing import Any

import hikari

from bot.core.event_system import event_listener
from bot.plugins.base import BasePlugin
from bot.web.mixins import WebPanelMixin

from .commands import setup_info_commands, setup_settings_commands

logger = logging.getLogger(__name__)


class AdminPlugin(BasePlugin, WebPanelMixin):
    def __init__(self, bot: Any) -> None:
        super().__init__(bot)
        self._register_commands()

    def _register_commands(self) -> None:
        commands = setup_settings_commands(self) + setup_info_commands(self)
        for command_func in commands:
            setattr(self, command_func.__name__, command_func)

    @event_listener("member_join")
    async def on_member_join(self, member: hikari.Member) -> None:
        """Handle new member joins and assign auto roles."""
        try:
            autoroles = await self.get_setting(member.guild_id, "autoroles", [])
            if not autoroles:
                return

            guild = self.bot.hikari_bot.cache.get_guild(member.guild_id)
            if not guild:
                return

            roles_assigned: list[str] = []
            for role_id in autoroles:
                try:
                    role = guild.get_role(role_id)
                    if role:
                        await member.add_role(role, reason="Auto role assignment")
                        roles_assigned.append(role.name)
                        logger.info("Assigned auto role %s to %s in %s", role.name, member.username, guild.name)
                except Exception as exc:
                    logger.error(
                        "Failed to assign auto role %s to %s: %s",
                        role_id,
                        member.username,
                        exc,
                    )

            if roles_assigned:
                logger.info(
                    "Assigned %s auto roles to %s in %s",
                    len(roles_assigned),
                    member.username,
                    guild.name,
                )

        except Exception as exc:
            logger.error("Error in auto role assignment for %s: %s", member.username, exc)

    # Web Panel Implementation
    def get_panel_info(self) -> dict[str, Any]:
        """Return metadata about this plugin's web panel."""
        return {
            "name": "Admin Panel",
            "description": "Guild administration and permission management",
            "route": "/plugin/admin",
            "icon": "fa-solid fa-shield-halved",
            "nav_order": 1,
        }

    def register_web_routes(self, app) -> None:
        """Register web routes for the admin plugin."""
        from .web import register_admin_routes

        register_admin_routes(app, self)
