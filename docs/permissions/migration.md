# Permission Migration Guide

This guide helps existing deployments migrate stored permission data from the legacy node scheme to the new hierarchical
structure. The bot will automatically discover the new nodes after this change set, but database rows that reference the old
values must be updated to avoid orphaned grants.

## 1. Preparation
1. **Back up your database** – copy the SQLite file or take a snapshot of your PostgreSQL instance.
2. **Stop the bot** – prevent new permission changes while the migration is running.
3. **Pull the latest code** – ensure this commit is deployed so that the new permission names are available.

## 2. Let the bot discover the new nodes
Restart the bot once after deploying the code. During start-up the `PermissionManager` will scan loaded plugins and insert the new
permission rows (for example `basic.music.queue.view`, `music.queue.manage`, etc.).

## 3. Remap existing role grants
Run the following Python helper once inside your project environment (e.g. `uv run python migrate_permissions.py`). It copies
existing grants from legacy nodes to their replacements and removes obsolete entries.

```python
# save as migrate_permissions.py and execute with `uv run python migrate_permissions.py`
import asyncio

from bot.database import db_manager
from bot.database.models import Permission, RolePermission

# Only nodes that require explicit migration (basic.* nodes remain publicly accessible)
PERMISSION_MAP = {
    "admin.permissions": ["admin.permissions.manage"],
    "admin.config": ["admin.config.manage"],
    "admin.plugins": ["admin.plugins.manage"],
    "admin.music.settings": ["music.settings.manage"],
    "links.manage": ["links.collection.manage", "links.manage"],
    "moderation.kick": ["moderation.members.kick"],
    "moderation.ban": ["moderation.members.ban"],
    "moderation.timeout": ["moderation.members.timeout"],
    "moderation.warn": ["moderation.members.warn"],
    "moderation.nickname": ["moderation.members.nickname"],
    "moderation.mute": ["moderation.members.mute"],
    "moderation.purge": ["moderation.channels.purge"],
    "moderation.slowmode": ["moderation.channels.slowmode"],
    "moderation.music.manage": ["music.queue.manage", "music.voice.manage", "music.manage"],
    "music.manage": ["music.queue.manage", "music.voice.manage", "music.manage"],
    "music.settings": ["music.settings.manage"],
}

async def migrate() -> None:
    async with db_manager.session() as session:
        # Look up all permissions we need in a single query
        nodes_to_fetch = set(PERMISSION_MAP.keys()) | {n for repl in PERMISSION_MAP.values() for n in repl}
        permissions = await session.execute(Permission.__table__.select().where(Permission.node.in_(nodes_to_fetch)))
        perm_rows = {row["node"]: row for row in permissions.mappings()}

        for legacy, replacements in PERMISSION_MAP.items():
            legacy_perm = perm_rows.get(legacy)
            if not legacy_perm:
                continue

            # Identify all role grants that currently reference the legacy node
            role_perms = await session.execute(
                RolePermission.__table__.select().where(RolePermission.permission_id == legacy_perm["id"])
            )
            role_permissions = list(role_perms.mappings())

            for replacement in replacements:
                replacement_perm = perm_rows.get(replacement)
                if not replacement_perm:
                    print(f"Skipping {replacement} – ensure the bot has been started once to create it.")
                    continue

                for rp in role_permissions:
                    exists = await session.execute(
                        RolePermission.__table__.select().where(
                            (RolePermission.guild_id == rp["guild_id"]) &
                            (RolePermission.role_id == rp["role_id"]) &
                            (RolePermission.permission_id == replacement_perm["id"])
                        )
                    )
                    if exists.first() is None:
                        session.add(
                            RolePermission(
                                guild_id=rp["guild_id"],
                                role_id=rp["role_id"],
                                permission_id=replacement_perm["id"],
                                granted=rp["granted"],
                            )
                        )

            # Remove the legacy grant to keep the database tidy
            await session.execute(
                RolePermission.__table__.delete().where(RolePermission.permission_id == legacy_perm["id"])
            )
            await session.execute(Permission.__table__.delete().where(Permission.id == legacy_perm["id"]))

        await session.commit()

if __name__ == "__main__":
    asyncio.run(migrate())
    print("✅ Permission migration complete")
```

> **Tip:** If you operate on PostgreSQL, execute the script inside the same environment where the bot normally runs so that the
> configured database URL is reused.

The migration also seeds the new plugin-level aggregators (`admin.manage`, `moderation.manage`, `music.manage`, `links.manage`).
Granting these nodes to a role provides the entire plugin toolset without listing every individual permission.

## 4. Clear caches and verify
1. Start the bot again – the permission cache is automatically rebuilt on launch.
2. Use the admin panel (`/permission list`) to verify that only the new nodes appear and that roles still have the expected access.
3. Update any documentation or runbooks that referenced the old node names.

## 5. Optional clean-up
- Remove any manual grants for `basic.*` nodes – those permissions are implicitly available to everyone.
- If you manage permissions in infrastructure-as-code, update templates to the new naming scheme.
