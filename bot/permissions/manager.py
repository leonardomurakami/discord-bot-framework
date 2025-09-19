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
        self._default_permissions = {
            # Admin permissions
            "admin.config": "Configure bot settings",
            "admin.plugins": "Manage plugins",
            "admin.permissions": "Manage permissions",
            # Moderation permissions
            "moderation.kick": "Kick members",
            "moderation.ban": "Ban members",
            "moderation.mute": "Mute members",
            "moderation.warn": "Warn members",
            "moderation.purge": "Delete messages",
            "moderation.timeout": "Timeout members",
            # Utility permissions
            "utility.info": "View info commands",
            "utility.stats": "View statistics",
            # Fun permissions
            "fun.games": "Use fun games",
            "fun.images": "Use image commands",
            # Music permissions
            "music.play": "Play music",
            "music.skip": "Skip songs",
            "music.queue": "Manage queue",
            "music.volume": "Change volume",
        }

    async def initialize(self) -> None:
        await self._create_default_permissions()
        logger.info("Permission system initialized")

    async def _create_default_permissions(self) -> None:
        async with self.db.session() as session:
            existing_permissions = await session.execute(select(Permission))
            existing_nodes = {perm.node for perm in existing_permissions.scalars()}

            new_permissions = []
            for node, description in self._default_permissions.items():
                if node not in existing_nodes:
                    category = node.split(".")[0]
                    new_permissions.append(Permission(node=node, description=description, category=category))

            if new_permissions:
                session.add_all(new_permissions)
                await session.commit()
                logger.info(f"Created {len(new_permissions)} new permissions")

    async def grant_permission(self, guild_id: int, role_id: int, permission_node: str) -> bool:
        try:
            async with self.db.session() as session:
                # Get permission
                permission_result = await session.execute(select(Permission).where(Permission.node == permission_node))
                permission = permission_result.scalar_one_or_none()

                if not permission:
                    logger.error(f"Permission {permission_node} not found")
                    return False

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
                    role_perm.granted = True
                else:
                    role_perm = RolePermission(
                        guild_id=guild_id,
                        role_id=role_id,
                        permission_id=permission.id,
                        granted=True,
                    )
                    session.add(role_perm)

                await session.commit()

                # Clear cache
                self._clear_guild_cache(guild_id)

                logger.info(f"Granted {permission_node} to role {role_id} in guild {guild_id}")
                return True

        except Exception as e:
            logger.error(f"Error granting permission: {e}")
            return False

    async def revoke_permission(self, guild_id: int, role_id: int, permission_node: str) -> bool:
        try:
            async with self.db.session() as session:
                # Get permission
                permission_result = await session.execute(select(Permission).where(Permission.node == permission_node))
                permission = permission_result.scalar_one_or_none()

                if not permission:
                    return False

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
                    role_perm.granted = False
                else:
                    role_perm = RolePermission(
                        guild_id=guild_id,
                        role_id=role_id,
                        permission_id=permission.id,
                        granted=False,
                    )
                    session.add(role_perm)

                await session.commit()

                # Clear cache
                self._clear_guild_cache(guild_id)

                logger.info(f"Revoked {permission_node} from role {role_id} in guild {guild_id}")
                return True

        except Exception as e:
            logger.error(f"Error revoking permission: {e}")
            return False

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
