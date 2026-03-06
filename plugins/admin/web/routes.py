import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from bot.database.manager import db_manager
from bot.database.models import Guild, Permission, RolePermission

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from ..plugin import AdminPlugin

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _get_auth(plugin: "AdminPlugin"):
    """Return the DiscordAuth instance or None."""
    web_app = getattr(plugin.web_panel, "web_app", None)
    return getattr(web_app, "auth", None)


def _require_auth(request: Request, plugin: "AdminPlugin") -> Dict[str, Any]:
    """Raise 401 if the request is not authenticated, else return current_user dict."""
    auth = _get_auth(plugin)
    if not auth or not auth.is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")
    return auth.get_current_user(request)


def _require_guild_admin(request: Request, plugin: "AdminPlugin", guild_id: int) -> Dict[str, Any]:
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

                session.add(Guild(id=guild_id, name=guild_name, prefix="!", language="en", settings={}))
                await session.commit()
                logger.info(f"Created guild record for {guild_id} ({guild_name})")

            return True

    except Exception as e:
        logger.error(f"Error ensuring guild exists: {e}")
        return False


async def get_all_permissions() -> List[Permission]:
    """Get all available permissions from the database."""
    try:
        async with db_manager.session() as session:
            from sqlalchemy import select
            result = await session.execute(select(Permission).order_by(Permission.category, Permission.node))
            return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Error getting permissions: {e}")
        return []


async def get_role_granted_permissions(guild_id: int, role_id: int) -> List[str]:
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
        permissions_by_category: Dict[str, List] = {}
        for perm in all_permissions:
            permissions_by_category.setdefault(perm.category, []).append(perm)

        return plugin.render_plugin_template(request, "panel.html", {
            "permissions_by_category": permissions_by_category,
            "total_permissions": len(all_permissions),
        })

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
                        roles.append({
                            "id": str(role.id),
                            "name": role.name,
                            "color": f"#{role.color:06x}" if role.color else "#99aab5",
                            "position": role.position,
                        })

                roles.sort(key=lambda r: r["position"], reverse=True)

                roles_html = '<div class="roles-list">'
                for role in roles:
                    roles_html += (
                        f'<div class="role-item" data-role-id="{role["id"]}" '
                        f'onclick="selectRole(\'{role["id"]}\', \'{role["name"].replace(chr(39), "")}\', \'{role["color"]}\')">'
                        f'<div class="role-color" style="background-color:{role["color"]};"></div>'
                        f'<div class="role-name">{role["name"]}</div>'
                        '</div>'
                    )
                roles_html += '</div>'
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
            raise HTTPException(status_code=500, detail="Failed to get role permissions")

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
                {"success": False, "granted": granted, "failed": failed,
                 "message": f"Failed to grant: {', '.join(failed)}"},
                status_code=400,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error granting role permission: {e}")
            raise HTTPException(status_code=500, detail="Failed to grant permission")

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
                {"success": False, "revoked": revoked, "failed": failed,
                 "message": f"Failed to revoke: {', '.join(failed)}"},
                status_code=400,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error revoking role permission: {e}")
            raise HTTPException(status_code=500, detail="Failed to revoke permission")

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
                members.append({
                    "id": str(member.id),
                    "username": member.username,
                    "display_name": display,
                    "avatar": (
                        str(member.make_avatar_url())
                        if member.make_avatar_url()
                        else f"https://cdn.discordapp.com/embed/avatars/{int(member.id) % 5}.png"
                    ),
                })
                if len(members) >= 50:
                    break

            members.sort(key=lambda m: m["display_name"].lower())

            html = '<div class="members-list">'
            for m in members:
                html += (
                    f'<div class="member-item" data-user-id="{m["id"]}" '
                    f'onclick="selectUser(\'{m["id"]}\', \'{m["display_name"].replace(chr(39), "")}\', \'{m["username"].replace(chr(39), "")}\', \'{m["avatar"]}\')">'
                    f'<img src="{m["avatar"]}" class="member-avatar" alt="" />'
                    f'<div class="member-info">'
                    f'<div class="member-name">{m["display_name"]}</div>'
                    f'<div class="member-tag">{m["username"]}</div>'
                    '</div></div>'
                )
            html += '</div>'
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
            raise HTTPException(status_code=500, detail="Failed to get user permissions")

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
                {"success": False, "granted": granted, "failed": failed,
                 "message": f"Failed to grant: {', '.join(failed)}"},
                status_code=400,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error granting user permission: {e}")
            raise HTTPException(status_code=500, detail="Failed to grant permission")

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
                {"success": False, "revoked": revoked, "failed": failed,
                 "message": f"Failed to revoke: {', '.join(failed)}"},
                status_code=400,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error revoking user permission: {e}")
            raise HTTPException(status_code=500, detail="Failed to revoke permission")

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
            return JSONResponse({"permissions": [
                {"id": p.id, "node": p.node, "description": p.description, "category": p.category}
                for p in permissions
            ]})
        except Exception as e:
            logger.error(f"Error getting all permissions: {e}")
            raise HTTPException(status_code=500, detail="Failed to get permissions")
