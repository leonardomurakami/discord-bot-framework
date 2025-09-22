from __future__ import annotations

import logging
from typing import Any

import hikari
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from bot.database.models import Link
from bot.plugins.base import BasePlugin
from bot.plugins.commands.argument_types import CommandArgument
from bot.plugins.commands.decorators import command

from .config import links_settings

logger = logging.getLogger(__name__)


class LinksPlugin(BasePlugin):
    def __init__(self, bot: Any) -> None:
        super().__init__(bot)
        self._default_links = links_settings.default_links

    async def on_load(self) -> None:
        await super().on_load()
        logger.info("Links plugin loaded")

    async def on_unload(self) -> None:
        await super().on_unload()
        logger.info("Links plugin unloaded")

    @command(
        name="link",
        description="Display a custom server link",
        arguments=[
            CommandArgument(
                name="name",
                arg_type=hikari.OptionType.STRING,
                description="Name of the custom link to display",
                required=True,
            )
        ],
        permission_node="links.view",
    )
    async def show_link(self, ctx, name: str) -> None:
        """Display a custom link by name."""
        try:
            if not ctx.guild_id:
                await self.smart_respond(ctx, "This command can only be used in a server!")
                return

            async with self.bot.db.session() as session:
                # Check custom links only
                stmt = select(Link).where(Link.guild_id == ctx.guild_id, Link.name == name.lower())
                result = await session.execute(stmt)
                link_record = result.scalar_one_or_none()

                if link_record:
                    embed = self.create_embed(
                        title=f"🔗 {link_record.name.title()}",
                        description=link_record.description or "Custom server link",
                        color=hikari.Color(0x00FF00),
                    )
                    embed.add_field("URL", link_record.url, inline=False)
                    embed.add_field("📅 Added", f"{link_record.created_at.strftime('%Y-%m-%d %H:%M')} UTC", inline=True)
                    embed.set_footer(f"Created by {await self._get_username(link_record.created_by)}")
                    await self.smart_respond(ctx, embed=embed)
                    return

                # Check if it's a default link and suggest the specific command
                if name.lower() in self._default_links:
                    embed = self.create_embed(
                        title="💡 Use Dedicated Command",
                        description=f"For **{name}**, use the dedicated command for better information:",
                        color=hikari.Color(0xFFAA00),
                    )
                    embed.add_field("Recommended Command", f"`!{name.lower()}`", inline=False)
                    embed.add_field(
                        "Why?",
                        "Dedicated commands provide enhanced information, " "better styling, and contextual help!",
                        inline=False,
                    )
                    await self.smart_respond(ctx, embed=embed)
                    return

                # Link not found
                embed = self.create_embed(
                    title="❌ Custom Link Not Found",
                    description=f"No custom link named '{name}' found in this server.",
                    color=hikari.Color(0xFF0000),
                )
                embed.add_field("📋 View Available Links", "Use `!links` to see all custom links", inline=False)
                embed.add_field("🌟 Default Commands", "`!github` • `!panel` • `!docs` • `!support`", inline=False)
                await self.smart_respond(ctx, embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error displaying link {name}: {e}")
            await self.smart_respond(ctx, "❌ An error occurred while fetching the link.", ephemeral=True)

    @command(
        name="github",
        aliases=["gh", "source"],
        description="Show the GitHub repository link",
        permission_node="links.view",
    )
    async def github_link(self, ctx) -> None:
        """Display the GitHub repository link with enhanced styling."""
        try:
            embed = self.create_embed(
                title="🐙 GitHub Repository",
                description="Access the source code and contribute to the project",
                color=hikari.Color(0x24292F),  # GitHub dark color
            )
            embed.add_field("Repository", self._default_links["github"], inline=False)
            embed.add_field(
                "📝 What you can do", "• View source code\n• Report issues\n• Submit pull requests\n• Star the project", inline=False
            )
            embed.set_thumbnail("https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png")
            await self.smart_respond(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error displaying GitHub link: {e}")
            await self.smart_respond(ctx, "❌ An error occurred while fetching the GitHub link.", ephemeral=True)

    @command(
        name="panel",
        description="Show the web control panel link",
        permission_node="links.view",
    )
    async def panel_link(self, ctx) -> None:
        """Display the web control panel link with enhanced styling."""
        try:
            embed = self.create_embed(
                title="🎛️ Web Control Panel",
                description="Manage bot settings through the web interface",
                color=hikari.Color(0x5865F2),  # Discord blurple
            )
            embed.add_field("Panel URL", self._default_links["panel"], inline=False)
            embed.add_field(
                "🛠️ Features", "• Configure plugins\n• Manage permissions\n• View analytics\n• Server settings", inline=False
            )
            embed.add_field("🔐 Access", "Login with your Discord account", inline=False)
            await self.smart_respond(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error displaying panel link: {e}")
            await self.smart_respond(ctx, "❌ An error occurred while fetching the panel link.", ephemeral=True)

    @command(
        name="docs",
        description="Show the documentation link",
        permission_node="links.view",
    )
    async def docs_link(self, ctx) -> None:
        """Display the documentation link with enhanced styling."""
        try:
            embed = self.create_embed(
                title="📚 Documentation",
                description="Learn how to use and configure the bot",
                color=hikari.Color(0x00D4AA),  # Docs green
            )
            embed.add_field("Documentation", self._default_links["docs"], inline=False)
            embed.add_field(
                "📖 What you'll find",
                "• Setup guides\n• Command reference\n• Configuration options\n• Plugin development",
                inline=False,
            )
            embed.add_field("💡 Getting Started", "Perfect for new users and developers", inline=False)
            await self.smart_respond(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error displaying docs link: {e}")
            await self.smart_respond(ctx, "❌ An error occurred while fetching the docs link.", ephemeral=True)

    @command(
        name="support",
        description="Show the support Discord server link",
        permission_node="links.view",
    )
    async def support_link(self, ctx) -> None:
        """Display the support Discord server link with enhanced styling."""
        try:
            embed = self.create_embed(
                title="💬 Support Server",
                description="Get help and connect with the community",
                color=hikari.Color(0x7289DA),  # Discord classic color
            )
            embed.add_field("Discord Server", self._default_links["support"], inline=False)
            embed.add_field(
                "🤝 Community Support",
                "• Ask questions\n• Get help with setup\n• Share feedback\n• Connect with other users",
                inline=False,
            )
            embed.add_field("⚡ Quick Response", "Active community and developers", inline=False)
            await self.smart_respond(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error displaying support link: {e}")
            await self.smart_respond(ctx, "❌ An error occurred while fetching the support link.", ephemeral=True)

    @command(
        name="links",
        description="List all custom links for this server",
        permission_node="links.view",
    )
    async def list_links(self, ctx) -> None:
        """List custom server links."""
        try:
            embed = self.create_embed(
                title="🔗 Custom Server Links", description="Links specific to this server", color=hikari.Color(0x0099FF)
            )

            # Add custom links if in a guild
            if ctx.guild_id:
                async with self.bot.db.session() as session:
                    stmt = select(Link).where(Link.guild_id == ctx.guild_id).order_by(Link.name)
                    result = await session.execute(stmt)
                    custom_links = result.scalars().all()

                    if custom_links:
                        link_list = []
                        for link in custom_links:
                            desc = f" - {link.description}" if link.description else ""
                            link_list.append(f"• **{link.name}**{desc}")

                        embed.add_field("Available Links", "\n".join(link_list), inline=False)
                        embed.set_footer("Use !link <name> to display a specific link")
                    else:
                        embed.add_field(
                            "No Custom Links",
                            "No custom links have been added to this server yet.\n" "Use `!addlink <name> <url>` to add one!",
                            inline=False,
                        )
            else:
                embed.add_field("Server Only", "Custom links are only available in servers.", inline=False)

            # Add info about default commands
            embed.add_field(
                "🌟 Default Commands",
                "`!github` • `!panel` • `!docs` • `!support`\n" "These are always available with enhanced information!",
                inline=False,
            )

            await self.smart_respond(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error listing links: {e}")
            await self.smart_respond(ctx, "❌ An error occurred while listing links.", ephemeral=True)

    @command(
        name="addlink",
        description="Add a custom link",
        arguments=[
            CommandArgument(
                name="name",
                arg_type=hikari.OptionType.STRING,
                description="Name for the link",
                required=True,
            ),
            CommandArgument(
                name="url",
                arg_type=hikari.OptionType.STRING,
                description="The URL to store",
                required=True,
            ),
            CommandArgument(
                name="description",
                arg_type=hikari.OptionType.STRING,
                description="Optional description for the link",
                required=False,
            ),
        ],
        permission_node="links.manage",
    )
    async def add_link(self, ctx, name: str, url: str, description: str = None) -> None:
        """Add a custom link."""
        try:
            if not ctx.guild_id:
                await self.smart_respond(ctx, "This command can only be used in a server!", ephemeral=True)
                return

            # Validate URL format
            if not (url.startswith("http://") or url.startswith("https://")):
                await self.smart_respond(ctx, "❌ URL must start with http:// or https://", ephemeral=True)
                return

            # Check if name conflicts with default commands
            reserved_names = {"github", "docs", "panel", "support", "links", "link", "addlink", "removelink"}
            if name.lower() in reserved_names:
                await self.smart_respond(
                    ctx, f"❌ '{name}' is a reserved command name. Please choose a different name.", ephemeral=True
                )
                return

            async with self.bot.db.session() as session:
                new_link = Link(
                    guild_id=ctx.guild_id,
                    name=name.lower(),
                    url=url,
                    description=description,
                    created_by=ctx.author.id,
                )

                session.add(new_link)
                await session.commit()

                embed = self.create_embed(
                    title="✅ Link Added", description=f"Successfully added link '{name}'", color=hikari.Color(0x00FF00)
                )
                embed.add_field("Name", name.lower(), inline=True)
                embed.add_field("URL", url, inline=False)
                if description:
                    embed.add_field("Description", description, inline=False)

                await self.smart_respond(ctx, embed=embed)

        except IntegrityError:
            await self.smart_respond(ctx, f"❌ A link with the name '{name}' already exists in this server.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error adding link {name}: {e}")
            await self.smart_respond(ctx, "❌ An error occurred while adding the link.", ephemeral=True)

    @command(
        name="removelink",
        description="Remove a custom link",
        arguments=[
            CommandArgument(
                name="name",
                arg_type=hikari.OptionType.STRING,
                description="Name of the link to remove",
                required=True,
            )
        ],
        permission_node="links.manage",
    )
    async def remove_link(self, ctx, name: str) -> None:
        """Remove a custom link."""
        try:
            if not ctx.guild_id:
                await self.smart_respond(ctx, "This command can only be used in a server!", ephemeral=True)
                return

            # Prevent removal of reserved command names
            reserved_names = {"github", "docs", "panel", "support", "links", "link", "addlink", "removelink"}
            if name.lower() in reserved_names:
                await self.smart_respond(ctx, f"❌ '{name}' is a reserved command name and cannot be removed.", ephemeral=True)
                return

            async with self.bot.db.session() as session:
                stmt = select(Link).where(Link.guild_id == ctx.guild_id, Link.name == name.lower())
                result = await session.execute(stmt)
                link_record = result.scalar_one_or_none()

                if not link_record:
                    await self.smart_respond(ctx, f"❌ Link '{name}' not found.", ephemeral=True)
                    return

                await session.delete(link_record)
                await session.commit()

                embed = self.create_embed(
                    title="✅ Link Removed", description=f"Successfully removed link '{name}'", color=hikari.Color(0x00FF00)
                )
                await self.smart_respond(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error removing link {name}: {e}")
            await self.smart_respond(ctx, "❌ An error occurred while removing the link.", ephemeral=True)

    async def _get_username(self, user_id: int) -> str:
        """Get username for a user ID."""
        try:
            user = self.bot.hikari_bot.cache.get_user(user_id)
            if user:
                return user.username
            return f"User {user_id}"
        except Exception:
            return f"User {user_id}"
