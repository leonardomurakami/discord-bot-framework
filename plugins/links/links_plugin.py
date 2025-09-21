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
        description="Display a stored link",
        arguments=[
            CommandArgument(
                name="name",
                arg_type=hikari.OptionType.STRING,
                description="Name of the link to display",
                required=True,
            )
        ],
        permission_node="links.view",
    )
    async def show_link(self, ctx, name: str) -> None:
        """Display a link by name."""
        try:
            if not ctx.guild_id:
                await self.smart_respond(ctx, "This command can only be used in a server!")
                return

            async with self.bot.db_manager.session() as session:
                # First check custom links
                stmt = select(Link).where(
                    Link.guild_id == ctx.guild_id,
                    Link.name == name.lower()
                )
                result = await session.execute(stmt)
                link_record = result.scalar_one_or_none()

                if link_record:
                    embed = self.create_embed(
                        title=f"🔗 {link_record.name.title()}",
                        description=link_record.description or "No description provided",
                        color=hikari.Color(0x00ff00)
                    )
                    embed.add_field("URL", link_record.url, inline=False)
                    embed.set_footer(f"Created by {await self._get_username(link_record.created_by)}")
                    await self.smart_respond(ctx, embed=embed)
                    return

                # Check default links
                if name.lower() in self._default_links:
                    url = self._default_links[name.lower()]
                    embed = self.create_embed(
                        title=f"🔗 {name.title()}",
                        description="Default system link",
                        color=hikari.Color(0x0099ff)
                    )
                    embed.add_field("URL", url, inline=False)
                    await self.smart_respond(ctx, embed=embed)
                    return

                # Link not found
                await self.smart_respond(
                    ctx,
                    f"❌ Link '{name}' not found. Use `!links` to see available links.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error displaying link {name}: {e}")
            await self.smart_respond(ctx, "❌ An error occurred while fetching the link.", ephemeral=True)

    @command(
        name="links",
        description="List all available links",
        permission_node="links.view",
    )
    async def list_links(self, ctx) -> None:
        """List all available links."""
        try:
            embed = self.create_embed(
                title="📋 Available Links",
                description="Here are all the available links:",
                color=hikari.Color(0x0099ff)
            )

            # Add default links
            default_list = "\n".join([f"• {name}" for name in self._default_links.keys()])
            embed.add_field("Default Links", default_list or "None", inline=True)

            # Add custom links if in a guild
            if ctx.guild_id:
                async with self.bot.db_manager.session() as session:
                    stmt = select(Link).where(Link.guild_id == ctx.guild_id).order_by(Link.name)
                    result = await session.execute(stmt)
                    custom_links = result.scalars().all()

                    if custom_links:
                        custom_list = "\n".join([f"• {link.name}" for link in custom_links])
                        embed.add_field("Custom Links", custom_list, inline=True)
                    else:
                        embed.add_field("Custom Links", "None", inline=True)

            embed.set_footer("Use !link <name> to display a specific link")
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

            # Check if name conflicts with default links
            if name.lower() in self._default_links:
                await self.smart_respond(
                    ctx,
                    f"❌ Cannot override default link '{name}'. Choose a different name.",
                    ephemeral=True
                )
                return

            async with self.bot.db_manager.session() as session:
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
                    title="✅ Link Added",
                    description=f"Successfully added link '{name}'",
                    color=hikari.Color(0x00ff00)
                )
                embed.add_field("Name", name.lower(), inline=True)
                embed.add_field("URL", url, inline=False)
                if description:
                    embed.add_field("Description", description, inline=False)

                await self.smart_respond(ctx, embed=embed)

        except IntegrityError:
            await self.smart_respond(
                ctx,
                f"❌ A link with the name '{name}' already exists in this server.",
                ephemeral=True
            )
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

            # Prevent removal of default links
            if name.lower() in self._default_links:
                await self.smart_respond(
                    ctx,
                    f"❌ Cannot remove default link '{name}'.",
                    ephemeral=True
                )
                return

            async with self.bot.db_manager.session() as session:
                stmt = select(Link).where(
                    Link.guild_id == ctx.guild_id,
                    Link.name == name.lower()
                )
                result = await session.execute(stmt)
                link_record = result.scalar_one_or_none()

                if not link_record:
                    await self.smart_respond(
                        ctx,
                        f"❌ Link '{name}' not found.",
                        ephemeral=True
                    )
                    return

                await session.delete(link_record)
                await session.commit()

                embed = self.create_embed(
                    title="✅ Link Removed",
                    description=f"Successfully removed link '{name}'",
                    color=hikari.Color(0x00ff00)
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