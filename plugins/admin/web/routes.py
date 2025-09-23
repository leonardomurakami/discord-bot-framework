import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from bot.database.manager import db_manager
from bot.database.models import Guild, Permission, RolePermission

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from ..plugin import AdminPlugin

logger = logging.getLogger(__name__)


async def ensure_guild_exists(guild_id: int, plugin: "AdminPlugin") -> bool:
    """Ensure the guild exists in the database."""
    try:
        async with db_manager.session() as session:
            from sqlalchemy import select
            from bot.database.models import Guild

            # Check if guild exists
            result = await session.execute(select(Guild).where(Guild.id == guild_id))
            guild = result.scalar_one_or_none()

            if not guild:
                # Guild doesn't exist, create it
                guild_name = "Unknown Guild"

                # Try to get guild name from bot cache
                if plugin.cache:
                    hikari_guild = plugin.cache.get_guild(guild_id)
                    if hikari_guild:
                        guild_name = hikari_guild.name

                new_guild = Guild(
                    id=guild_id,
                    name=guild_name,
                    prefix="!",  # Default prefix
                    language="en",  # Default language
                    settings={}  # Default empty settings
                )
                session.add(new_guild)
                await session.commit()
                logger.info(f"Created guild record for {guild_id} ({guild_name})")

            return True

    except Exception as e:
        logger.error(f"Error ensuring guild exists: {e}")
        return False


async def get_guild_data(guild_id: int) -> Optional[Dict[str, Any]]:
    """Get guild data including roles and permissions."""
    try:
        # Get guild from bot's cache
        # Note: We'll need to access the bot instance to get guild info
        return {
            "id": guild_id,
            "name": f"Guild {guild_id}",  # Placeholder - will be populated from Discord API
            "roles": [],  # Will be populated from Discord API
        }
    except Exception as e:
        logger.error(f"Error getting guild data: {e}")
        return None


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


async def get_role_permissions(guild_id: int, role_id: int) -> List[str]:
    """Get permissions for a specific role in a guild."""
    try:
        async with db_manager.session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Permission.node)
                .join(RolePermission)
                .where(
                    RolePermission.guild_id == guild_id,
                    RolePermission.role_id == role_id,
                    RolePermission.granted == True
                )
                .order_by(Permission.node)
            )
            return [node for node in result.scalars().all()]
    except Exception as e:
        logger.error(f"Error getting role permissions: {e}")
        return []


def register_admin_routes(app: FastAPI, plugin: "AdminPlugin") -> None:
    """Register all admin web routes."""

    @app.get("/plugin/admin", response_class=HTMLResponse)
    async def admin_panel(request: Request):
        """Main admin panel interface."""
        # Get auth instance from web app
        web_app = getattr(plugin.web_panel, "web_app", None)
        auth = getattr(web_app, "auth", None)

        # Check if user is authenticated
        if not auth or not auth.is_authenticated(request):
            return plugin.render_plugin_template(request, "auth_required.html", {})

        # Get all permissions grouped by category for the template
        all_permissions = await get_all_permissions()
        permissions_by_category = {}
        for perm in all_permissions:
            if perm.category not in permissions_by_category:
                permissions_by_category[perm.category] = []
            permissions_by_category[perm.category].append(perm)

        context = {
            "permissions_by_category": permissions_by_category,
            "total_permissions": len(all_permissions),
        }

        return plugin.render_plugin_template(request, "panel.html", context)

    @app.get("/plugin/admin/check-access/{guild_id}")
    async def check_guild_access(request: Request, guild_id: int):
        """Check if user has admin access to a guild."""
        # Get auth instance from web app
        web_app = getattr(plugin.web_panel, "web_app", None)
        auth = getattr(web_app, "auth", None)

        if not auth or not auth.is_authenticated(request):
            return JSONResponse({"error": "Not authenticated"}, status_code=401)

        try:
            current_user = auth.get_current_user(request)
            user_guilds = current_user.get("guilds", []) if current_user else []

            # Check if user is in the guild and has admin permissions
            has_access = False
            guild_info = None

            for guild in user_guilds:
                if str(guild["id"]) == str(guild_id):
                    permissions = guild.get("permissions", 0)
                    # Check for Administrator permission (0x8) or Manage Guild (0x20)
                    if permissions & (0x8 | 0x20):
                        has_access = True
                        guild_info = guild
                    break

            if not has_access:
                return JSONResponse({
                    "error": "Access denied",
                    "message": "You don't have administrator permissions for this server."
                }, status_code=403)

            # Get additional guild info from bot cache
            bot_guild_info = None
            if plugin.cache:
                guild = plugin.cache.get_guild(guild_id)
                if guild:
                    bot_guild_info = {
                        "id": guild.id,
                        "name": guild.name,
                        "icon": str(guild.icon_url) if guild.icon_url else None,
                    }

            return JSONResponse({
                "success": True,
                "guild_info": bot_guild_info or guild_info
            })

        except Exception as e:
            logger.error(f"Error checking guild access: {e}")
            return JSONResponse({"error": "Failed to check access"}, status_code=500)


    @app.get("/plugin/admin/api/guild/{guild_id}/roles")
    async def get_guild_roles(guild_id: int):
        """Get roles for a specific guild - returns HTML for HTMX."""
        try:
            # Get guild from bot's Discord client
            hikari_bot = plugin.gateway
                guild = hikari_bot.cache.get_guild(guild_id)
                if not guild:
                    return HTMLResponse('<div class="error-message">Guild not found</div>')

                roles = []
                for role in guild.get_roles().values():
                    if role.id != guild.id:  # Skip @everyone role for admin panel
                        roles.append({
                            "id": str(role.id),
                            "name": role.name,
                            "color": f"#{role.color:06x}" if role.color else "#99aab5",
                            "position": role.position,
                            "permissions": str(role.permissions.value),
                        })

                # Sort by position (higher position = higher in hierarchy)
                roles.sort(key=lambda x: x["position"], reverse=True)

                # Generate HTML for roles
                roles_html = '<div class="roles-list">'
                for role in roles:
                    roles_html += (
                        '<div class="role-item" '
                        f'data-role-id="{role["id"]}" '
                        f'onclick="selectRole(\'{role["id"]}\', \'{role["name"]}\', \'{role["color"]}\')">'
                        f"\n                        <div class=\"role-color\" style=\"background-color: {role['color']};\"></div>"
                        f"\n                        <div class=\"role-name\">{role['name']}</div>"
                        "\n                    </div>"
                    )
                roles_html += '</div>'

                return HTMLResponse(roles_html)
            else:
                return HTMLResponse('<div class="error-message">Bot not available</div>')

        except Exception as e:
            logger.error(f"Error getting guild roles: {e}")
            return HTMLResponse('<div class="error-message">Failed to load guild roles</div>')

    @app.get("/plugin/admin/api/guild/{guild_id}/role/{role_id}/permissions")
    async def get_role_permissions_api(guild_id: int, role_id: int):
        """Get permissions for a specific role."""
        try:
            permissions = await get_role_permissions(guild_id, role_id)
            return JSONResponse({"permissions": permissions})
        except Exception as e:
            logger.error(f"Error getting role permissions: {e}")
            raise HTTPException(status_code=500, detail="Failed to get role permissions")

    @app.post("/plugin/admin/api/guild/{guild_id}/role/{role_id}/permissions/grant")
    async def grant_permission_api(
        guild_id: int,
        role_id: int,
        permission_node: str = Form(...),
    ):
        """Grant a permission to a role."""
        try:
            # Ensure the guild exists in the database first
            if not await ensure_guild_exists(guild_id, plugin):
                raise HTTPException(status_code=500, detail="Failed to ensure guild exists in database")

            # Use the bot's permission manager
            permission_manager = plugin.permissions
            success, granted, failed = await permission_manager.grant_permission(
                guild_id, role_id, permission_node
            )

            if success:
                return JSONResponse({
                    "success": True,
                    "granted": granted,
                    "failed": failed,
                    "message": f"Granted {len(granted)} permission(s)"
                })
            else:
                return JSONResponse({
                    "success": False,
                    "granted": granted,
                    "failed": failed,
                    "message": f"Failed to grant permission(s): {', '.join(failed)}"
                }, status_code=400)

        except Exception as e:
            logger.error(f"Error granting permission: {e}")
            raise HTTPException(status_code=500, detail="Failed to grant permission")

    @app.post("/plugin/admin/api/guild/{guild_id}/role/{role_id}/permissions/revoke")
    async def revoke_permission_api(
        guild_id: int,
        role_id: int,
        permission_node: str = Form(...),
    ):
        """Revoke a permission from a role."""
        try:
            # Ensure the guild exists in the database first
            if not await ensure_guild_exists(guild_id, plugin):
                raise HTTPException(status_code=500, detail="Failed to ensure guild exists in database")

            # Use the bot's permission manager
            permission_manager = plugin.permissions
            success, revoked, failed = await permission_manager.revoke_permission(
                guild_id, role_id, permission_node
            )

            if success:
                return JSONResponse({
                    "success": True,
                    "revoked": revoked,
                    "failed": failed,
                    "message": f"Revoked {len(revoked)} permission(s)"
                })
            else:
                return JSONResponse({
                    "success": False,
                    "revoked": revoked,
                    "failed": failed,
                    "message": f"Failed to revoke permission(s): {', '.join(failed)}"
                }, status_code=400)

        except Exception as e:
            logger.error(f"Error revoking permission: {e}")
            raise HTTPException(status_code=500, detail="Failed to revoke permission")

    @app.get("/plugin/admin/api/permissions")
    async def get_all_permissions_api():
        """Get all available permissions."""
        try:
            permissions = await get_all_permissions()
            permissions_data = []
            for perm in permissions:
                permissions_data.append({
                    "id": perm.id,
                    "node": perm.node,
                    "description": perm.description,
                    "category": perm.category,
                })
            return JSONResponse({"permissions": permissions_data})
        except Exception as e:
            logger.error(f"Error getting all permissions: {e}")
            raise HTTPException(status_code=500, detail="Failed to get permissions")
