"""Miru views for the admin plugin."""

import logging
from typing import TYPE_CHECKING

import hikari
import miru

if TYPE_CHECKING:
    from .admin_plugin import AdminPlugin

logger = logging.getLogger(__name__)


class PermissionsPaginationView(miru.View):
    """Pagination view for permissions list."""

    def __init__(self, admin_plugin: "AdminPlugin", permissions: list, page_size: int = 10, initial_page: int = 0) -> None:
        super().__init__(timeout=300)  # 5 minute timeout
        self.admin_plugin = admin_plugin
        self.permissions = permissions
        self.page_size = page_size
        self.current_page = initial_page
        self.total_pages = (len(permissions) + page_size - 1) // page_size if permissions else 1
        self._setup_buttons()

        # Start the view with the miru client
        self._start_view()

    def _start_view(self) -> None:
        """Start the view with the miru client."""
        try:
            # Get miru client from bot
            if hasattr(self.admin_plugin, "bot") and hasattr(self.admin_plugin.bot, "miru_client"):
                self.admin_plugin.bot.miru_client.start_view(self)
        except Exception as e:
            logger.error(f"Failed to start miru view: {e}")

    def _setup_buttons(self) -> None:
        """Setup pagination buttons."""
        # Previous page button
        prev_button = miru.Button(
            style=hikari.ButtonStyle.SECONDARY,
            emoji="⬅️",
            custom_id="permissions_prev_page",
            disabled=self.current_page <= 0,
        )
        prev_button.callback = self.on_previous_page
        self.add_item(prev_button)

        # Page indicator button (non-clickable)
        page_button = miru.Button(
            style=hikari.ButtonStyle.PRIMARY,
            label=f"{self.current_page + 1}/{self.total_pages}",
            custom_id="permissions_page_indicator",
            disabled=True,
        )
        self.add_item(page_button)

        # Next page button
        next_button = miru.Button(
            style=hikari.ButtonStyle.SECONDARY,
            emoji="➡️",
            custom_id="permissions_next_page",
            disabled=self.current_page >= self.total_pages - 1,
        )
        next_button.callback = self.on_next_page
        self.add_item(next_button)

    def get_current_page_embed(self) -> hikari.Embed:
        """Generate the embed for the current page."""
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.permissions))
        current_perms = self.permissions[start_idx:end_idx]

        from .config import SERVER_INFO_COLOR

        if not current_perms:
            return self.admin_plugin.create_embed(
                title="🔑 Available Permissions",
                description="No permissions found.",
                color=SERVER_INFO_COLOR,
            )

        perm_list = "\n".join(f"• `{perm.node}` - {perm.description}" for perm in current_perms)

        embed = self.admin_plugin.create_embed(
            title="🔑 Available Permissions",
            description=perm_list,
            color=SERVER_INFO_COLOR,
        )

        # Add footer with pagination info
        embed.set_footer(f"Page {self.current_page + 1} of {self.total_pages} • Total: {len(self.permissions)} permissions")

        return embed

    async def on_previous_page(self, ctx: miru.ViewContext) -> None:
        """Handle previous page button click."""
        try:
            if self.current_page <= 0:
                await ctx.respond("Already on the first page.", flags=hikari.MessageFlag.EPHEMERAL)
                return

            self.current_page -= 1

            # Update button states
            self._update_button_states()

            # Generate new embed
            new_embed = self.get_current_page_embed()
            await ctx.edit_response(embed=new_embed, components=self)

        except Exception as e:
            logger.error(f"Error in previous page callback: {e}")
            await ctx.respond("An error occurred while navigating pages.", flags=hikari.MessageFlag.EPHEMERAL)

    async def on_next_page(self, ctx: miru.ViewContext) -> None:
        """Handle next page button click."""
        try:
            if self.current_page >= self.total_pages - 1:
                await ctx.respond("Already on the last page.", flags=hikari.MessageFlag.EPHEMERAL)
                return

            self.current_page += 1

            # Update button states
            self._update_button_states()

            # Generate new embed
            new_embed = self.get_current_page_embed()
            await ctx.edit_response(embed=new_embed, components=self)

        except Exception as e:
            logger.error(f"Error in next page callback: {e}")
            await ctx.respond("An error occurred while navigating pages.", flags=hikari.MessageFlag.EPHEMERAL)

    def _update_button_states(self) -> None:
        """Update the enabled/disabled state of buttons based on current page."""
        for item in self.children:
            if isinstance(item, miru.Button):
                if item.custom_id == "permissions_prev_page":
                    item.disabled = self.current_page <= 0
                elif item.custom_id == "permissions_next_page":
                    item.disabled = self.current_page >= self.total_pages - 1
                elif item.custom_id == "permissions_page_indicator":
                    item.label = f"{self.current_page + 1}/{self.total_pages}"


class RolePermissionsPaginationView(miru.View):
    """Pagination view for role-specific permissions list."""

    def __init__(
        self, admin_plugin: "AdminPlugin", role: hikari.Role, permissions: list[str], page_size: int = 10, initial_page: int = 0
    ) -> None:
        super().__init__(timeout=300)  # 5 minute timeout
        self.admin_plugin = admin_plugin
        self.role = role
        self.permissions = permissions
        self.page_size = page_size
        self.current_page = initial_page
        self.total_pages = (len(permissions) + page_size - 1) // page_size if permissions else 1
        self._setup_buttons()

        # Start the view with the miru client
        self._start_view()

    def _start_view(self) -> None:
        """Start the view with the miru client."""
        try:
            # Get miru client from bot
            if hasattr(self.admin_plugin, "bot") and hasattr(self.admin_plugin.bot, "miru_client"):
                self.admin_plugin.bot.miru_client.start_view(self)
        except Exception as e:
            logger.error(f"Failed to start miru view: {e}")

    def _setup_buttons(self) -> None:
        """Setup pagination buttons."""
        # Previous page button
        prev_button = miru.Button(
            style=hikari.ButtonStyle.SECONDARY,
            emoji="⬅️",
            custom_id="role_permissions_prev_page",
            disabled=self.current_page <= 0,
        )
        prev_button.callback = self.on_previous_page
        self.add_item(prev_button)

        # Page indicator button (non-clickable)
        page_button = miru.Button(
            style=hikari.ButtonStyle.PRIMARY,
            label=f"{self.current_page + 1}/{self.total_pages}",
            custom_id="role_permissions_page_indicator",
            disabled=True,
        )
        self.add_item(page_button)

        # Next page button
        next_button = miru.Button(
            style=hikari.ButtonStyle.SECONDARY,
            emoji="➡️",
            custom_id="role_permissions_next_page",
            disabled=self.current_page >= self.total_pages - 1,
        )
        next_button.callback = self.on_next_page
        self.add_item(next_button)

    def get_current_page_embed(self) -> hikari.Embed:
        """Generate the embed for the current page."""
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.permissions))
        current_perms = self.permissions[start_idx:end_idx]

        from .config import SERVER_INFO_COLOR, WARNING_COLOR

        if not current_perms:
            return self.admin_plugin.create_embed(
                title=f"🔑 Permissions for @{self.role.name}",
                description="No permissions granted.",
                color=WARNING_COLOR,
            )

        perm_list = "\n".join(f"• {perm}" for perm in current_perms)

        embed = self.admin_plugin.create_embed(
            title=f"🔑 Permissions for @{self.role.name}",
            description=perm_list,
            color=SERVER_INFO_COLOR,
        )

        # Add footer with pagination info
        embed.set_footer(f"Page {self.current_page + 1} of {self.total_pages} • Total: {len(self.permissions)} permissions")

        return embed

    async def on_previous_page(self, ctx: miru.ViewContext) -> None:
        """Handle previous page button click."""
        try:
            if self.current_page <= 0:
                await ctx.respond("Already on the first page.", flags=hikari.MessageFlag.EPHEMERAL)
                return

            self.current_page -= 1

            # Update button states
            self._update_button_states()

            # Generate new embed
            new_embed = self.get_current_page_embed()
            await ctx.edit_response(embed=new_embed, components=self)

        except Exception as e:
            logger.error(f"Error in previous page callback: {e}")
            await ctx.respond("An error occurred while navigating pages.", flags=hikari.MessageFlag.EPHEMERAL)

    async def on_next_page(self, ctx: miru.ViewContext) -> None:
        """Handle next page button click."""
        try:
            if self.current_page >= self.total_pages - 1:
                await ctx.respond("Already on the last page.", flags=hikari.MessageFlag.EPHEMERAL)
                return

            self.current_page += 1

            # Update button states
            self._update_button_states()

            # Generate new embed
            new_embed = self.get_current_page_embed()
            await ctx.edit_response(embed=new_embed, components=self)

        except Exception as e:
            logger.error(f"Error in next page callback: {e}")
            await ctx.respond("An error occurred while navigating pages.", flags=hikari.MessageFlag.EPHEMERAL)

    def _update_button_states(self) -> None:
        """Update the enabled/disabled state of buttons based on current page."""
        for item in self.children:
            if isinstance(item, miru.Button):
                if item.custom_id == "role_permissions_prev_page":
                    item.disabled = self.current_page <= 0
                elif item.custom_id == "role_permissions_next_page":
                    item.disabled = self.current_page >= self.total_pages - 1
                elif item.custom_id == "role_permissions_page_indicator":
                    item.label = f"{self.current_page + 1}/{self.total_pages}"
