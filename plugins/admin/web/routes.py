import html
import logging
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from bot.database.manager import db_manager
from bot.database.models import Guild, Permission, RolePermission
from config.settings import settings

from ..config import SERVER_FEATURE_MAPPING, check_autorole_hierarchy, validate_prefix

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from ..plugin import AdminPlugin

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Server-side HTML escaping helper
# ---------------------------------------------------------------------------


def esc_html(value: str) -> str:
    """Escape a user-supplied string for safe inclusion in HTML.

    Uses :func:`html.escape` with ``quote=True`` so that single quotes,
    double quotes, angle brackets, and ampersands are all converted to
    their entity equivalents, preventing XSS in server-rendered fragments.
    """
    return html.escape(str(value), quote=True)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _get_auth(plugin: "AdminPlugin"):
    """Return the DiscordAuth instance or None."""
    web_app = getattr(plugin.web_panel, "web_app", None)
    return getattr(web_app, "auth", None)


def _require_auth(request: Request, plugin: "AdminPlugin") -> dict[str, Any]:
    """Raise 401 if the request is not authenticated, else return current_user dict."""
    auth = _get_auth(plugin)
    if not auth or not auth.is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")
    return auth.get_current_user(request)


def _require_guild_admin(request: Request, plugin: "AdminPlugin", guild_id: int) -> dict[str, Any]:
    """
    Require the authenticated user to be Discord Administrator or Manage-Guild
    in the given guild.  Raises 401/403 on failure.
    """
    current_user = _require_auth(request, plugin)
    for guild in current_user.get("guilds", []):
        if str(guild["id"]) == str(guild_id):
            perms = int(guild.get("permissions", 0))
            if perms & 0x8 or perms & 0x20:  # Administrator | Manage Guild
                return current_user
    raise HTTPException(
        status_code=403,
        detail="You need Administrator or Manage Guild permission in this server.",
    )


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


async def ensure_guild_exists(guild_id: int, plugin: "AdminPlugin") -> bool:
    """Ensure the guild exists in the database."""
    try:
        async with db_manager.session() as session:
            from sqlalchemy import select

            result = await session.execute(select(Guild).where(Guild.id == guild_id))
            guild = result.scalar_one_or_none()

            if not guild:
                guild_name = "Unknown Guild"
                if plugin.cache:
                    hikari_guild = plugin.cache.get_guild(guild_id)
                    if hikari_guild:
                        guild_name = hikari_guild.name

                session.add(Guild(id=guild_id, name=guild_name, prefix=settings.bot_prefix, language="en", settings={}))
                await session.commit()
                logger.info(f"Created guild record for {guild_id} ({guild_name})")

            return True

    except Exception as e:
        logger.error(f"Error ensuring guild exists: {e}")
        return False


async def get_all_permissions() -> list[Permission]:
    """Get all available permissions from the database."""
    try:
        async with db_manager.session() as session:
            from sqlalchemy import select

            result = await session.execute(select(Permission).order_by(Permission.category, Permission.node))
            return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Error getting permissions: {e}")
        return []


async def get_role_granted_permissions(guild_id: int, role_id: int) -> list[str]:
    """Get explicitly-granted permission nodes for a role in a guild."""
    try:
        async with db_manager.session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(Permission.node)
                .join(RolePermission)
                .where(
                    RolePermission.guild_id == guild_id,
                    RolePermission.role_id == role_id,
                    RolePermission.granted == True,  # noqa: E712
                )
                .order_by(Permission.node)
            )
            return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Error getting role permissions: {e}")
        return []


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def register_admin_routes(app: FastAPI, plugin: "AdminPlugin") -> None:
    """Register all admin web routes."""

    # ------------------------------------------------------------------
    # Main panel page
    # ------------------------------------------------------------------

    @app.get("/plugin/admin", response_class=HTMLResponse)
    async def admin_panel(request: Request):
        """Main admin panel interface — requires Discord admin in at least one guild."""
        auth = _get_auth(plugin)
        if not auth or not auth.is_authenticated(request):
            return plugin.render_plugin_template(request, "auth_required.html", {})

        current_user = auth.get_current_user(request)
        # Check that the user is admin in at least one guild
        is_any_admin = False
        for guild in (current_user or {}).get("guilds", []):
            perms = int(guild.get("permissions", 0))
            if perms & 0x8 or perms & 0x20:
                is_any_admin = True
                break

        if not is_any_admin:
            raise HTTPException(status_code=403, detail="Access denied")

        all_permissions = await get_all_permissions()
        permissions_by_category: dict[str, list] = {}
        for perm in all_permissions:
            permissions_by_category.setdefault(perm.category, []).append(perm)

        return plugin.render_plugin_template(
            request,
            "panel.html",
            {
                "permissions_by_category": permissions_by_category,
                "total_permissions": len(all_permissions),
            },
        )

    # ------------------------------------------------------------------
    # Guild access check
    # ------------------------------------------------------------------

    @app.get("/plugin/admin/check-access/{guild_id}")
    async def check_guild_access(request: Request, guild_id: int):
        """Check if the authenticated user has admin access to a guild."""
        auth = _get_auth(plugin)
        if not auth or not auth.is_authenticated(request):
            return JSONResponse({"error": "Not authenticated"}, status_code=401)

        try:
            current_user = auth.get_current_user(request)
            user_guilds = current_user.get("guilds", []) if current_user else []

            has_access = False
            guild_info = None
            for guild in user_guilds:
                if str(guild["id"]) == str(guild_id):
                    perms = int(guild.get("permissions", 0))
                    if perms & 0x8 or perms & 0x20:
                        has_access = True
                        guild_info = guild
                    break

            if not has_access:
                return JSONResponse(
                    {"error": "Access denied", "message": "You need Administrator or Manage Guild permission."},
                    status_code=403,
                )

            # Enrich with bot cache data
            bot_guild_info = None
            if plugin.cache:
                cached = plugin.cache.get_guild(guild_id)
                if cached:
                    icon_url = cached.make_icon_url()
                    bot_guild_info = {
                        "id": str(cached.id),
                        "name": cached.name,
                        "icon": str(icon_url) if icon_url else None,
                    }

            return JSONResponse({"success": True, "guild_info": bot_guild_info or guild_info})

        except Exception as e:
            logger.error(f"Error checking guild access: {e}")
            return JSONResponse({"error": "Failed to check access"}, status_code=500)

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------

    @app.get("/plugin/admin/api/guild/{guild_id}/roles")
    async def get_guild_roles(request: Request, guild_id: int):
        """Get roles for a specific guild — returns HTML for HTMX."""
        _require_guild_admin(request, plugin, guild_id)
        try:
            hikari_bot = plugin.gateway
            if hikari_bot:
                guild = hikari_bot.cache.get_guild(guild_id)
                if not guild:
                    return HTMLResponse('<div class="error-message">Guild not found or bot is not in this server.</div>')

                roles = []
                for role in guild.get_roles().values():
                    if role.id != guild.id:  # Skip @everyone
                        roles.append(
                            {
                                "id": str(role.id),
                                "name": role.name,
                                "color": f"#{role.color:06x}" if role.color else "#99aab5",
                                "position": role.position,
                            }
                        )

                roles.sort(key=lambda r: r["position"], reverse=True)

                roles_html = '<div class="roles-list">'
                for role in roles:
                    safe_name = esc_html(role["name"])
                    roles_html += (
                        f'<div class="role-item" data-role-id="{role["id"]}" '
                        f'data-role-name="{safe_name}" '
                        f'data-role-color="{role["color"]}" '
                        f'onclick="selectRole(\'{role["id"]}\', \'{safe_name}\', \'{role["color"]}\')">'
                        f'<div class="role-color" style="background-color:{role["color"]};"></div>'
                        f'<div class="role-name">{safe_name}</div>'
                        "</div>"
                    )
                roles_html += "</div>"
                return HTMLResponse(roles_html)
            else:
                return HTMLResponse('<div class="error-message">Bot gateway not available.</div>')

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting guild roles: {e}")
            return HTMLResponse('<div class="error-message">Failed to load roles.</div>')

    # ------------------------------------------------------------------
    # Role permission endpoints
    # ------------------------------------------------------------------

    @app.get("/plugin/admin/api/guild/{guild_id}/role/{role_id}/permissions")
    async def get_role_permissions_api(request: Request, guild_id: int, role_id: int):
        """Get the granted permissions for a specific role."""
        _require_guild_admin(request, plugin, guild_id)
        try:
            permissions = await get_role_granted_permissions(guild_id, role_id)
            return JSONResponse({"permissions": permissions})
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting role permissions: {e}")
            raise HTTPException(status_code=500, detail="Failed to get role permissions") from e

    @app.post("/plugin/admin/api/guild/{guild_id}/role/{role_id}/permissions/grant")
    async def grant_role_permission_api(
        request: Request,
        guild_id: int,
        role_id: int,
        permission_node: str = Form(...),
    ):
        """Grant a permission (or wildcard pattern) to a role."""
        _require_guild_admin(request, plugin, guild_id)
        try:
            if not await ensure_guild_exists(guild_id, plugin):
                raise HTTPException(status_code=500, detail="Failed to ensure guild exists in database")

            success, granted, failed = await plugin.permissions.grant_permission(guild_id, role_id, permission_node)

            if not failed:
                msg = f"Granted {len(granted)} permission(s)" if granted else "Already granted"
                return JSONResponse({"success": True, "granted": granted, "failed": failed, "message": msg})
            return JSONResponse(
                {"success": False, "granted": granted, "failed": failed, "message": f"Failed to grant: {', '.join(failed)}"},
                status_code=400,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error granting role permission: {e}")
            raise HTTPException(status_code=500, detail="Failed to grant permission") from e

    @app.post("/plugin/admin/api/guild/{guild_id}/role/{role_id}/permissions/revoke")
    async def revoke_role_permission_api(
        request: Request,
        guild_id: int,
        role_id: int,
        permission_node: str = Form(...),
    ):
        """Revoke a permission (or wildcard pattern) from a role."""
        _require_guild_admin(request, plugin, guild_id)
        try:
            if not await ensure_guild_exists(guild_id, plugin):
                raise HTTPException(status_code=500, detail="Failed to ensure guild exists in database")

            success, revoked, failed = await plugin.permissions.revoke_permission(guild_id, role_id, permission_node)

            if not failed:
                msg = f"Revoked {len(revoked)} permission(s)" if revoked else "Already revoked"
                return JSONResponse({"success": True, "revoked": revoked, "failed": failed, "message": msg})
            return JSONResponse(
                {"success": False, "revoked": revoked, "failed": failed, "message": f"Failed to revoke: {', '.join(failed)}"},
                status_code=400,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error revoking role permission: {e}")
            raise HTTPException(status_code=500, detail="Failed to revoke permission") from e

    # ------------------------------------------------------------------
    # Guild members (for user permission management)
    # ------------------------------------------------------------------

    @app.get("/plugin/admin/api/guild/{guild_id}/members")
    async def get_guild_members(request: Request, guild_id: int, search: str = ""):
        """Return up to 50 members, optionally filtered by search term — HTML for HTMX."""
        _require_guild_admin(request, plugin, guild_id)
        try:
            hikari_bot = plugin.gateway
            if not hikari_bot:
                return HTMLResponse('<div class="error-message">Bot gateway not available.</div>')

            guild = hikari_bot.cache.get_guild(guild_id)
            if not guild:
                return HTMLResponse('<div class="error-message">Guild not found.</div>')

            search_lower = search.strip().lower()
            members = []
            for member in guild.get_members().values():
                display = member.display_name or member.username
                if search_lower and search_lower not in display.lower() and search_lower not in member.username.lower():
                    continue
                members.append(
                    {
                        "id": str(member.id),
                        "username": member.username,
                        "display_name": display,
                        "avatar": (
                            str(member.make_avatar_url())
                            if member.make_avatar_url()
                            else f"https://cdn.discordapp.com/embed/avatars/{int(member.id) % 5}.png"
                        ),
                    }
                )
                if len(members) >= 50:
                    break

            members.sort(key=lambda m: m["display_name"].lower())

            html = '<div class="members-list">'
            for m in members:
                safe_display = esc_html(m["display_name"])
                safe_username = esc_html(m["username"])
                html += (
                    f'<div class="member-item" data-user-id="{m["id"]}" '
                    f'data-display-name="{safe_display}" '
                    f'data-username="{safe_username}" '
                    f'data-avatar="{m["avatar"]}" '
                    f'onclick="selectUser(\'{m["id"]}\', \'{safe_display}\', \'{safe_username}\', \'{m["avatar"]}\')">'
                    f'<img src="{m["avatar"]}" class="member-avatar" alt="" />'
                    f'<div class="member-info">'
                    f'<div class="member-name">{safe_display}</div>'
                    f'<div class="member-tag">{safe_username}</div>'
                    "</div></div>"
                )
            html += "</div>"
            if not members:
                html = '<div class="empty-state">No members found.</div>'
            return HTMLResponse(html)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting guild members: {e}")
            return HTMLResponse('<div class="error-message">Failed to load members.</div>')

    # ------------------------------------------------------------------
    # User permission endpoints
    # ------------------------------------------------------------------

    @app.get("/plugin/admin/api/guild/{guild_id}/user/{user_id}/permissions")
    async def get_user_permissions_api(request: Request, guild_id: int, user_id: int):
        """Get the directly-granted permissions for a specific user."""
        _require_guild_admin(request, plugin, guild_id)
        try:
            permissions = await plugin.permissions.get_user_direct_permissions(guild_id, user_id)
            return JSONResponse({"permissions": permissions})
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting user permissions: {e}")
            raise HTTPException(status_code=500, detail="Failed to get user permissions") from e

    @app.post("/plugin/admin/api/guild/{guild_id}/user/{user_id}/permissions/grant")
    async def grant_user_permission_api(
        request: Request,
        guild_id: int,
        user_id: int,
        permission_node: str = Form(...),
    ):
        """Grant a permission (or wildcard pattern) directly to a user."""
        _require_guild_admin(request, plugin, guild_id)
        try:
            if not await ensure_guild_exists(guild_id, plugin):
                raise HTTPException(status_code=500, detail="Failed to ensure guild exists in database")

            success, granted, failed = await plugin.permissions.grant_user_permission(guild_id, user_id, permission_node)

            if not failed:
                msg = f"Granted {len(granted)} permission(s)" if granted else "Already granted"
                return JSONResponse({"success": True, "granted": granted, "failed": failed, "message": msg})
            return JSONResponse(
                {"success": False, "granted": granted, "failed": failed, "message": f"Failed to grant: {', '.join(failed)}"},
                status_code=400,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error granting user permission: {e}")
            raise HTTPException(status_code=500, detail="Failed to grant permission") from e

    @app.post("/plugin/admin/api/guild/{guild_id}/user/{user_id}/permissions/revoke")
    async def revoke_user_permission_api(
        request: Request,
        guild_id: int,
        user_id: int,
        permission_node: str = Form(...),
    ):
        """Revoke a permission (or wildcard pattern) from a user."""
        _require_guild_admin(request, plugin, guild_id)
        try:
            if not await ensure_guild_exists(guild_id, plugin):
                raise HTTPException(status_code=500, detail="Failed to ensure guild exists in database")

            success, revoked, failed = await plugin.permissions.revoke_user_permission(guild_id, user_id, permission_node)

            if not failed:
                msg = f"Revoked {len(revoked)} permission(s)" if revoked else "Already revoked"
                return JSONResponse({"success": True, "revoked": revoked, "failed": failed, "message": msg})
            return JSONResponse(
                {"success": False, "revoked": revoked, "failed": failed, "message": f"Failed to revoke: {', '.join(failed)}"},
                status_code=400,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error revoking user permission: {e}")
            raise HTTPException(status_code=500, detail="Failed to revoke permission") from e

    # ------------------------------------------------------------------
    # All permissions list (used by JS to populate toggles)
    # ------------------------------------------------------------------

    @app.get("/plugin/admin/api/permissions")
    async def get_all_permissions_api(request: Request):
        """Get all available permission nodes (requires authentication)."""
        auth = _get_auth(plugin)
        if not auth or not auth.is_authenticated(request):
            raise HTTPException(status_code=401, detail="Authentication required")
        try:
            permissions = await get_all_permissions()
            return JSONResponse(
                {
                    "permissions": [
                        {"id": p.id, "node": p.node, "description": p.description, "category": p.category} for p in permissions
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error getting all permissions: {e}")
            raise HTTPException(status_code=500, detail="Failed to get permissions") from e

    # ------------------------------------------------------------------
    # Prefix management endpoints
    # ------------------------------------------------------------------

    @app.get("/plugin/admin/api/guild/{guild_id}/prefix")
    async def get_guild_prefix_api(request: Request, guild_id: int):
        """Get the current guild prefix (guild-admin gated)."""
        _require_guild_admin(request, plugin, guild_id)
        try:
            prefix = await plugin.get_guild_prefix(guild_id)
            return JSONResponse({"prefix": prefix, "max_length": 5})
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting guild prefix: {e}")
            raise HTTPException(status_code=500, detail="Failed to get prefix") from e

    @app.post("/plugin/admin/api/guild/{guild_id}/prefix")
    async def set_guild_prefix_api(request: Request, guild_id: int, new_prefix: str = Form(...)):
        """Set the guild prefix (guild-admin gated)."""
        _require_guild_admin(request, plugin, guild_id)
        try:
            is_valid, error_msg = validate_prefix(new_prefix)
            if not is_valid:
                return JSONResponse({"success": False, "message": error_msg}, status_code=400)

            if not await ensure_guild_exists(guild_id, plugin):
                raise HTTPException(status_code=500, detail="Failed to ensure guild exists in database")

            async with db_manager.session() as session:
                from sqlalchemy import select

                result = await session.execute(select(Guild).where(Guild.id == guild_id))
                guild = result.scalar_one_or_none()
                if guild:
                    guild.prefix = new_prefix
                else:
                    session.add(Guild(id=guild_id, name="Unknown Guild", prefix=new_prefix, language="en", settings={}))
                await session.commit()

            return JSONResponse({"success": True, "prefix": new_prefix, "message": f"Prefix updated to: {new_prefix}"})
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error setting guild prefix: {e}")
            raise HTTPException(status_code=500, detail="Failed to set prefix") from e

    # ------------------------------------------------------------------
    # Autorole management endpoints
    # ------------------------------------------------------------------

    @app.get("/plugin/admin/api/guild/{guild_id}/autoroles")
    async def get_guild_autoroles_api(request: Request, guild_id: int):
        """Get the configured autoroles for a guild (guild-admin gated)."""
        _require_guild_admin(request, plugin, guild_id)
        try:
            autoroles = await plugin.get_setting(guild_id, "autoroles", [])
            roles_data = []
            hikari_bot = plugin.gateway
            if hikari_bot:
                guild = hikari_bot.cache.get_guild(guild_id)
                if guild:
                    for role_id in autoroles:
                        role = guild.get_role(role_id)
                        if role:
                            roles_data.append(
                                {
                                    "id": str(role.id),
                                    "name": role.name,
                                    "color": f"#{role.color:06x}" if role.color else "#99aab5",
                                    "position": role.position,
                                }
                            )
                        else:
                            roles_data.append({"id": str(role_id), "name": "Deleted Role", "color": "#99aab5", "position": -1})
                else:
                    roles_data = [{"id": str(rid), "name": "Unknown Role", "color": "#99aab5", "position": -1} for rid in autoroles]
            return JSONResponse({"autoroles": roles_data})
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting autoroles: {e}")
            raise HTTPException(status_code=500, detail="Failed to get autoroles") from e

    @app.post("/plugin/admin/api/guild/{guild_id}/autoroles")
    async def add_guild_autorole_api(request: Request, guild_id: int, role_id: int = Form(...)):
        """Add an autorole for a guild (guild-admin gated)."""
        _require_guild_admin(request, plugin, guild_id)
        try:
            hikari_bot = plugin.gateway
            if not hikari_bot:
                raise HTTPException(status_code=500, detail="Bot gateway not available")

            guild = hikari_bot.cache.get_guild(guild_id)
            if not guild:
                raise HTTPException(status_code=404, detail="Guild not found in bot cache")

            role = guild.get_role(role_id)
            if not role:
                return JSONResponse({"success": False, "message": "Role not found in this guild."}, status_code=400)

            current_autoroles = await plugin.get_setting(guild_id, "autoroles", [])
            if role_id in current_autoroles:
                return JSONResponse({"success": False, "message": "This role is already configured as an autorole."}, status_code=400)

            bot_id = hikari_bot.get_me().id
            hierarchy_ok, hierarchy_error = await check_autorole_hierarchy(guild, role, bot_id)
            if not hierarchy_ok:
                return JSONResponse({"success": False, "message": hierarchy_error}, status_code=400)

            current_autoroles.append(role_id)
            await plugin.set_setting(guild_id, "autoroles", current_autoroles)

            return JSONResponse(
                {
                    "success": True,
                    "message": f"Added {role.name} as an autorole.",
                    "role": {"id": str(role.id), "name": role.name, "color": f"#{role.color:06x}" if role.color else "#99aab5"},
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding autorole: {e}")
            raise HTTPException(status_code=500, detail="Failed to add autorole") from e

    @app.delete("/plugin/admin/api/guild/{guild_id}/autoroles/{role_id}")
    async def remove_guild_autorole_api(request: Request, guild_id: int, role_id: int):
        """Remove an autorole from a guild (guild-admin gated)."""
        _require_guild_admin(request, plugin, guild_id)
        try:
            current_autoroles = await plugin.get_setting(guild_id, "autoroles", [])
            if role_id not in current_autoroles:
                return JSONResponse({"success": False, "message": "This role is not configured as an autorole."}, status_code=400)

            current_autoroles.remove(role_id)
            await plugin.set_setting(guild_id, "autoroles", current_autoroles)

            return JSONResponse({"success": True, "message": "Autorole removed."})
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error removing autorole: {e}")
            raise HTTPException(status_code=500, detail="Failed to remove autorole") from e

    # ------------------------------------------------------------------
    # Bot info endpoint (auth required, not guild-admin gated)
    # ------------------------------------------------------------------

    @app.get("/plugin/admin/api/bot-info")
    async def get_bot_info_api(request: Request):
        """Get bot overview data (requires authentication)."""
        _require_auth(request, plugin)
        try:
            overview = await plugin.bot.get_bot_overview()
            bot_user = overview.user
            created_at = None
            if hasattr(bot_user, "created_at") and bot_user.created_at:
                created_at = bot_user.created_at.isoformat()
            return JSONResponse(
                {
                    "username": getattr(bot_user, "username", "Unknown"),
                    "display_name": getattr(bot_user, "display_name", getattr(bot_user, "username", "Unknown")),
                    "guild_count": overview.guild_count,
                    "plugin_count": overview.plugin_count,
                    "database_connected": overview.database_connected,
                    "created_at": created_at,
                    "avatar_url": str(bot_user.display_avatar_url) if hasattr(bot_user, "display_avatar_url") else None,
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
            raise HTTPException(status_code=500, detail="Failed to get bot info") from e

    # ------------------------------------------------------------------
    # Server info endpoint (guild-admin gated)
    # ------------------------------------------------------------------

    @app.get("/plugin/admin/api/guild/{guild_id}/server-info")
    async def get_guild_server_info_api(request: Request, guild_id: int):
        """Get guild summary data (guild-admin gated)."""
        _require_guild_admin(request, plugin, guild_id)
        try:
            hikari_bot = plugin.gateway
            if not hikari_bot:
                raise HTTPException(status_code=500, detail="Bot gateway not available")

            guild = hikari_bot.cache.get_guild(guild_id)
            if not guild:
                return JSONResponse({"error": "Guild not found in bot cache.", "available": False}, status_code=200)

            summary = plugin.bot.summarise_guild(guild)

            features = []
            for feature in guild.features:
                if feature in SERVER_FEATURE_MAPPING:
                    features.append(SERVER_FEATURE_MAPPING[feature])
                else:
                    features.append(feature.replace("_", " ").title())

            icon_url = guild.make_icon_url() if guild.make_icon_url() else None
            banner_url = guild.make_banner_url() if guild.make_banner_url() else None

            return JSONResponse(
                {
                    "available": True,
                    "id": str(guild.id),
                    "name": guild.name,
                    "owner_id": str(guild.owner_id),
                    "created_at": guild.created_at.isoformat() if guild.created_at else None,
                    "member_count": summary.member_count,
                    "channel_count": summary.channel_count,
                    "text_channels": summary.text_channels,
                    "voice_channels": summary.voice_channels,
                    "category_channels": summary.category_channels,
                    "role_count": summary.role_count,
                    "emoji_count": summary.emoji_count,
                    "features": features,
                    "icon_url": str(icon_url) if icon_url else None,
                    "banner_url": str(banner_url) if banner_url else None,
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting server info: {e}")
            raise HTTPException(status_code=500, detail="Failed to get server info") from e

    # ------------------------------------------------------------------
    # Status / uptime endpoint (auth required)
    # ------------------------------------------------------------------

    @app.get("/plugin/admin/api/status")
    async def get_status_api(request: Request):
        """Get bot uptime and system status (requires authentication)."""
        _require_auth(request, plugin)
        try:
            import time
            from datetime import datetime

            data: dict[str, Any] = {
                "psutil_available": False,
                "guild_count": len(plugin.cache.get_guilds_view()) if plugin.cache else 0,
            }

            try:
                latency = plugin.gateway.heartbeat_latency * 1000
                data["latency_ms"] = round(latency, 1)
            except Exception:
                data["latency_ms"] = None

            try:
                import psutil  # type: ignore

                process = psutil.Process()
                process_start_time = process.create_time()
                bot_start_time = datetime.fromtimestamp(process_start_time)
                current_time = datetime.now()
                uptime_delta = current_time - bot_start_time

                data["psutil_available"] = True
                data["start_time"] = bot_start_time.isoformat()
                data["current_time"] = current_time.isoformat()
                data["uptime_seconds"] = int(uptime_delta.total_seconds())
                data["pid"] = process.pid

                try:
                    cpu_percent = process.cpu_percent()
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    data["cpu_percent"] = round(cpu_percent, 1)
                    data["memory_mb"] = round(memory_mb, 1)
                except Exception:
                    pass

                try:
                    system_uptime = time.time() - psutil.boot_time()
                    data["system_uptime_seconds"] = int(system_uptime)
                except Exception:
                    pass

            except ImportError:
                data["psutil_available"] = False
                data["note"] = "Install 'psutil' for detailed system information."

            return JSONResponse(data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            raise HTTPException(status_code=500, detail="Failed to get status") from e
