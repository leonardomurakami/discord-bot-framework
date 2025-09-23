from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import hikari

from bot.plugins.commands.decorators import command

if TYPE_CHECKING:
    from ..plugin import LinksPlugin

logger = logging.getLogger(__name__)


class DefaultLinkCommands:
    """Commands for default system links (GitHub, panel, docs, support)."""

    def __init__(self, plugin: LinksPlugin) -> None:
        self.plugin = plugin

    @command(
        name="github",
        aliases=["gh", "source"],
        description="Show the GitHub repository link",
        permission_node="links.view",
    )
    async def github_link(self, ctx) -> None:
        """Display the GitHub repository link with enhanced styling."""
        try:
            embed = self.plugin.create_embed(
                title="🐙 GitHub Repository",
                description="Access the source code and contribute to the project",
                color=hikari.Color(0x24292F),  # GitHub dark color
            )
            embed.add_field("Repository", self.plugin._default_links["github"], inline=False)
            embed.add_field(
                "📝 What you can do", "• View source code\n• Report issues\n• Submit pull requests\n• Star the project", inline=False
            )
            embed.set_thumbnail("https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png")
            await self.plugin.smart_respond(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error displaying GitHub link: {e}")
            await self.plugin.smart_respond(ctx, "❌ An error occurred while fetching the GitHub link.", ephemeral=True)

    @command(
        name="panel",
        description="Show the web control panel link",
        permission_node="links.view",
    )
    async def panel_link(self, ctx) -> None:
        """Display the web control panel link with enhanced styling."""
        try:
            embed = self.plugin.create_embed(
                title="🎛️ Web Control Panel",
                description="Manage bot settings through the web interface",
                color=hikari.Color(0x5865F2),  # Discord blurple
            )
            embed.add_field("Panel URL", self.plugin._default_links["panel"], inline=False)
            embed.add_field(
                "🛠️ Features", "• Configure plugins\n• Manage permissions\n• View analytics\n• Server settings", inline=False
            )
            embed.add_field("🔐 Access", "Login with your Discord account", inline=False)
            await self.plugin.smart_respond(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error displaying panel link: {e}")
            await self.plugin.smart_respond(ctx, "❌ An error occurred while fetching the panel link.", ephemeral=True)

    @command(
        name="docs",
        description="Show the documentation link",
        permission_node="links.view",
    )
    async def docs_link(self, ctx) -> None:
        """Display the documentation link with enhanced styling."""
        try:
            embed = self.plugin.create_embed(
                title="📚 Documentation",
                description="Learn how to use and configure the bot",
                color=hikari.Color(0x00D4AA),  # Docs green
            )
            embed.add_field("Documentation", self.plugin._default_links["docs"], inline=False)
            embed.add_field(
                "📖 What you'll find",
                "• Setup guides\n• Command reference\n• Configuration options\n• Plugin development",
                inline=False,
            )
            embed.add_field("💡 Getting Started", "Perfect for new users and developers", inline=False)
            await self.plugin.smart_respond(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error displaying docs link: {e}")
            await self.plugin.smart_respond(ctx, "❌ An error occurred while fetching the docs link.", ephemeral=True)

    @command(
        name="support",
        description="Show the support Discord server link",
        permission_node="links.view",
    )
    async def support_link(self, ctx) -> None:
        """Display the support Discord server link with enhanced styling."""
        try:
            embed = self.plugin.create_embed(
                title="💬 Support Server",
                description="Get help and connect with the community",
                color=hikari.Color(0x7289DA),  # Discord classic color
            )
            embed.add_field("Discord Server", self.plugin._default_links["support"], inline=False)
            embed.add_field(
                "🤝 Community Support",
                "• Ask questions\n• Get help with setup\n• Share feedback\n• Connect with other users",
                inline=False,
            )
            embed.add_field("⚡ Quick Response", "Active community and developers", inline=False)
            await self.plugin.smart_respond(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error displaying support link: {e}")
            await self.plugin.smart_respond(ctx, "❌ An error occurred while fetching the support link.", ephemeral=True)