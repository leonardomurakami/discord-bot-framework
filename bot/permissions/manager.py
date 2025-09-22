import logging

import hikari
from sqlalchemy import select

from ..database.manager import DatabaseManager
from ..database.models import Permission, RolePermission

logger = logging.getLogger(__name__)


class PermissionManager:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        self._permission_cache: dict[int, dict[int, set[str]]] = {}
        self._bot = None  # Will be set by the bot during initialization

    def set_bot(self, bot) -> None:
        """Set the bot instance for dynamic permission discovery."""
        self._bot = bot

    async def initialize(self) -> None:
        await self._create_default_permissions()
        logger.info("Permission system initialized")

    async def _create_default_permissions(self) -> None:
        """Discover permissions dynamically from loaded plugins and create them in database."""
        discovered_permissions = await self._discover_plugin_permissions()

        async with self.db.session() as session:
            existing_permissions = await session.execute(select(Permission))
            existing_nodes = {perm.node for perm in existing_permissions.scalars()}

            new_permissions = []
            for node, description in discovered_permissions.items():
                if node not in existing_nodes:
                    category = node.split(".")[0]
                    new_permissions.append(Permission(node=node, description=description, category=category))

            if new_permissions:
                session.add_all(new_permissions)
                await session.commit()
                logger.info(f"Created {len(new_permissions)} new permissions")

    async def _discover_plugin_permissions(self) -> dict[str, str]:
        """Dynamically discover permissions from all loaded plugins."""
        permissions = {}

        if not self._bot or not hasattr(self._bot, "plugin_loader"):
            logger.warning("Bot or plugin loader not available for permission discovery")
            return permissions

        # Iterate through all loaded plugins
        for plugin_name, plugin in self._bot.plugin_loader.plugins.items():
            try:
                # Look for methods with _unified_command metadata
                for attr_name in dir(plugin):
                    if attr_name.startswith("_"):
                        continue

                    attr = getattr(plugin, attr_name)
                    if hasattr(attr, "_unified_command"):
                        cmd_meta = attr._unified_command
                        permission_node = cmd_meta.get("permission_node")

                        if permission_node:
                            # Generate description from command info
                            cmd_name = cmd_meta.get("name", attr_name)
                            cmd_desc = cmd_meta.get("description", "")

                            if cmd_desc:
                                description = f"{cmd_desc}"
                            else:
                                # Generate description from permission node
                                action = permission_node.split(".")[-1]
                                description = f"{action.replace('_', ' ').title()} command"

                            permissions[permission_node] = description
                            logger.debug(f"Discovered permission: {permission_node} - {description}")

            except Exception as e:
                logger.error(f"Error discovering permissions from plugin {plugin_name}: {e}")

        logger.info(f"Discovered {len(permissions)} permissions from plugins")
        return permissions

    async def refresh_permissions(self) -> None:
        """Refresh permissions by re-discovering them from plugins."""
        await self._create_default_permissions()
        self.clear_cache()
        logger.info("Permissions refreshed from plugins")

    def _match_wildcard_pattern(self, pattern: str, permission_node: str) -> bool:
        """Check if a permission node matches a wildcard pattern."""
        if "*" not in pattern:
            return pattern == permission_node

        # Handle different wildcard patterns
        if pattern.endswith(".*"):
            # Pattern like "moderation.*" matches "moderation.kick", "moderation.ban", etc.
            prefix = pattern[:-2]
            return permission_node.startswith(prefix + ".")
        elif pattern.startswith("*."):
            # Pattern like "*.play" matches "music.play", "audio.play", etc.
            suffix = pattern[2:]
            return permission_node.endswith("." + suffix)
        elif pattern == "*":
            # Pattern "*" matches everything
            return True
        else:
            # More complex patterns could be added here if needed
            # For now, treat as exact match if no standard wildcard pattern
            return pattern == permission_node

    async def _resolve_wildcard_permissions(self, pattern: str) -> list[str]:
        """Resolve a wildcard pattern to a list of actual permission nodes."""
        if "*" not in pattern:
            # Not a wildcard, return as-is
            return [pattern]

        # Get all available permissions
        all_permissions = await self.get_all_permissions()

        # Filter permissions that match the pattern
        matching_nodes = []
        for perm in all_permissions:
            if self._match_wildcard_pattern(pattern, perm.node):
                matching_nodes.append(perm.node)

        return matching_nodes

    async def grant_permission(self, guild_id: int, role_id: int, permission_pattern: str) -> tuple[bool, list[str], list[str]]:
        """
        Grant permission(s) to a role. Supports wildcard patterns.

        Returns:
            tuple: (success, granted_permissions, failed_permissions)
        """
        try:
            # Resolve wildcard pattern to actual permission nodes
            permission_nodes = await self._resolve_wildcard_permissions(permission_pattern)

            if not permission_nodes:
                logger.error(f"No permissions found matching pattern: {permission_pattern}")
                return False, [], [permission_pattern]

            granted_permissions = []
            failed_permissions = []

            # Use a single transaction for all operations (atomic)
            async with self.db.session() as session:
                for permission_node in permission_nodes:
                    try:
                        # Get permission
                        permission_result = await session.execute(select(Permission).where(Permission.node == permission_node))
                        permission = permission_result.scalar_one_or_none()

                        if not permission:
                            failed_permissions.append(permission_node)
                            continue

                        # Check if role permission already exists
                        existing = await session.execute(
                            select(RolePermission).where(
                                RolePermission.guild_id == guild_id,
                                RolePermission.role_id == role_id,
                                RolePermission.permission_id == permission.id,
                            )
                        )

                        role_perm = existing.scalar_one_or_none()
                        if role_perm:
                            if not role_perm.granted:
                                role_perm.granted = True
                                granted_permissions.append(permission_node)
                            # If already granted, don't add to granted list
                        else:
                            role_perm = RolePermission(
                                guild_id=guild_id,
                                role_id=role_id,
                                permission_id=permission.id,
                                granted=True,
                            )
                            session.add(role_perm)
                            granted_permissions.append(permission_node)

                    except Exception as e:
                        logger.error(f"Error processing permission {permission_node}: {e}")
                        failed_permissions.append(permission_node)

                # Commit all changes atomically
                await session.commit()

                # Clear cache
                self._clear_guild_cache(guild_id)

                success = len(granted_permissions) > 0
                logger.info(
                    f"Granted {len(granted_permissions)} permissions to role {role_id} in guild {guild_id}: {granted_permissions}"
                )
                if failed_permissions:
                    logger.warning(f"Failed to grant {len(failed_permissions)} permissions: {failed_permissions}")

                return success, granted_permissions, failed_permissions

        except Exception as e:
            logger.error(f"Error in grant_permission: {e}")
            return False, [], permission_nodes if "permission_nodes" in locals() else [permission_pattern]

    async def revoke_permission(self, guild_id: int, role_id: int, permission_pattern: str) -> tuple[bool, list[str], list[str]]:
        """
        Revoke permission(s) from a role. Supports wildcard patterns.

        Returns:
            tuple: (success, revoked_permissions, failed_permissions)
        """
        try:
            # Resolve wildcard pattern to actual permission nodes
            permission_nodes = await self._resolve_wildcard_permissions(permission_pattern)

            if not permission_nodes:
                logger.error(f"No permissions found matching pattern: {permission_pattern}")
                return False, [], [permission_pattern]

            revoked_permissions = []
            failed_permissions = []

            # Use a single transaction for all operations (atomic)
            async with self.db.session() as session:
                for permission_node in permission_nodes:
                    try:
                        # Get permission
                        permission_result = await session.execute(select(Permission).where(Permission.node == permission_node))
                        permission = permission_result.scalar_one_or_none()

                        if not permission:
                            failed_permissions.append(permission_node)
                            continue

                        # Update or create role permission as denied
                        existing = await session.execute(
                            select(RolePermission).where(
                                RolePermission.guild_id == guild_id,
                                RolePermission.role_id == role_id,
                                RolePermission.permission_id == permission.id,
                            )
                        )

                        role_perm = existing.scalar_one_or_none()
                        if role_perm:
                            if role_perm.granted:
                                role_perm.granted = False
                                revoked_permissions.append(permission_node)
                            # If already revoked, don't add to revoked list
                        else:
                            role_perm = RolePermission(
                                guild_id=guild_id,
                                role_id=role_id,
                                permission_id=permission.id,
                                granted=False,
                            )
                            session.add(role_perm)
                            revoked_permissions.append(permission_node)

                    except Exception as e:
                        logger.error(f"Error processing permission {permission_node}: {e}")
                        failed_permissions.append(permission_node)

                # Commit all changes atomically
                await session.commit()

                # Clear cache
                self._clear_guild_cache(guild_id)

                success = len(revoked_permissions) > 0
                logger.info(
                    f"Revoked {len(revoked_permissions)} permissions from role {role_id} in guild {guild_id}: {revoked_permissions}"
                )
                if failed_permissions:
                    logger.warning(f"Failed to revoke {len(failed_permissions)} permissions: {failed_permissions}")

                return success, revoked_permissions, failed_permissions

        except Exception as e:
            logger.error(f"Error in revoke_permission: {e}")
            return False, [], permission_nodes if "permission_nodes" in locals() else [permission_pattern]

    async def has_permission(self, guild_id: int, user: hikari.Member, permission_node: str) -> bool:
        logger.debug(f"Checking permission '{permission_node}' for user {user.username} ({user.id}) in guild {guild_id}")

        # Server owner always has all permissions
        guild = user.get_guild()
        if guild and user.id == guild.owner_id:
            logger.debug(f"User {user.username} is server owner - granting all permissions")
            return True

        # Users with Administrator permission have all permissions
        try:
            from ..core.utils import calculate_member_permissions

            member_permissions = calculate_member_permissions(user, guild)
            if member_permissions & hikari.Permissions.ADMINISTRATOR:
                logger.debug(f"User {user.username} has Administrator permission - granting all permissions")
                return True
        except Exception as e:
            logger.debug(f"Could not calculate member permissions: {e}")

        # Check if this permission is granted by default to all users
        if self._has_default_permission(permission_node):
            logger.debug(f"Permission '{permission_node}' is granted by default - allowing access")
            return True

        # Get user's roles
        user_role_ids = user.role_ids

        # Check for role-based permission hierarchy
        if await self._has_hierarchical_permission(guild_id, user_role_ids, permission_node):
            return True

        # Check cached permissions
        if guild_id in self._permission_cache:
            for role_id in user_role_ids:
                if role_id in self._permission_cache[guild_id]:
                    if permission_node in self._permission_cache[guild_id][role_id]:
                        return True

        # Fetch permissions from database
        permissions = await self._get_role_permissions(guild_id, list(user_role_ids))

        # Cache the results
        if guild_id not in self._permission_cache:
            self._permission_cache[guild_id] = {}

        for role_id, role_permissions in permissions.items():
            self._permission_cache[guild_id][role_id] = role_permissions

        # Check if user has permission
        for role_id in user_role_ids:
            if role_id in permissions and permission_node in permissions[role_id]:
                return True

        return False

    def _has_default_permission(self, permission_node: str) -> bool:
        """Check if this permission should be granted by default to all users."""
        if permission_node.startswith("basic."):
            return True
        # Permissions that are available to everyone by default
        default_permissions = {
            # Fun commands - available to all
            "fun.games",
            "fun.images",
            # Basic utility commands - available to all
            "utility.info",
            "utility.stats",
            # Music commands (basic usage) - available to all
            "music.play",
            "music.queue",
        }

        return permission_node in default_permissions

    async def _has_hierarchical_permission(self, guild_id: int, role_ids: list[int], permission_node: str) -> bool:
        """Check if user has permission through role hierarchy."""
        try:
            # Permission hierarchy rules:
            # 1. admin.* permissions grant all permissions
            # 2. moderation.* permissions grant utility.* and fun.* permissions
            # 3. Higher-level permissions inherit lower-level ones

            # Get all permissions for user's roles
            permissions = await self._get_role_permissions(guild_id, role_ids)
            all_user_permissions = set()

            for role_permissions in permissions.values():
                all_user_permissions.update(role_permissions)

            # Check for direct permission
            if permission_node in all_user_permissions:
                return True

            # Check hierarchy rules
            permission_parts = permission_node.split(".")
            if len(permission_parts) >= 2:
                category, _action = permission_parts[0], permission_parts[1]

                # Admin permissions grant everything
                if any(perm.startswith("admin.") for perm in all_user_permissions):
                    return True

                # Moderation permissions grant utility and fun permissions
                if category in ["utility", "fun"] and any(perm.startswith("moderation.") for perm in all_user_permissions):
                    return True

                # Category-wide permissions (e.g., "admin.*" grants "admin.config")
                category_wildcard = f"{category}.*"
                if category_wildcard in all_user_permissions:
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking hierarchical permissions: {e}")
            return False

    async def _get_role_permissions(self, guild_id: int, role_ids: list[int]) -> dict[int, set[str]]:
        try:
            async with self.db.session() as session:
                result = await session.execute(
                    select(RolePermission, Permission.node)
                    .join(Permission)
                    .where(
                        RolePermission.guild_id == guild_id,
                        RolePermission.role_id.in_(role_ids),
                        RolePermission.granted,
                    )
                )

                permissions_by_role: dict[int, set[str]] = {}
                for role_permission, node in result:
                    role_id = role_permission.role_id
                    if role_id not in permissions_by_role:
                        permissions_by_role[role_id] = set()
                    permissions_by_role[role_id].add(node)

                return permissions_by_role

        except Exception as e:
            logger.error(f"Error fetching role permissions: {e}")
            return {}

    async def get_all_permissions(self) -> list[Permission]:
        try:
            async with self.db.session() as session:
                result = await session.execute(select(Permission))
                return list(result.scalars())
        except Exception as e:
            logger.error(f"Error fetching all permissions: {e}")
            return []

    async def get_role_permissions(self, guild_id: int, role_id: int) -> list[str]:
        try:
            permissions = await self._get_role_permissions(guild_id, [role_id])
            return list(permissions.get(role_id, set()))
        except Exception as e:
            logger.error(f"Error fetching role permissions: {e}")
            return []

    def _clear_guild_cache(self, guild_id: int) -> None:
        if guild_id in self._permission_cache:
            del self._permission_cache[guild_id]

    def clear_cache(self) -> None:
        self._permission_cache.clear()
        logger.info("Permission cache cleared")
