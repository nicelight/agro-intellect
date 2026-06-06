from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from backend.app.db.engine import async_session
from backend.app.db.models import Account, Farm, FarmMembership, Plant


async def seed_initial_data() -> None:
    async with async_session() as session:
        result = await session.execute(
            select(Farm).where(Farm.farm_id == "farm_local"),
        )
        existing_farm = result.scalar_one_or_none()
        if existing_farm is not None:
            return

        now = datetime.now(UTC)

        boss = Account(
            account_id="boss_001",
            display_name="Boss",
            login_identifier="boss",
            status="active",
            created_at=now,
            updated_at=now,
            created_by_account_id=None,
        )
        session.add(boss)
        await session.flush()

        farm = Farm(
            farm_id="farm_local",
            display_name="Local Farm",
            status="active",
            sync_status="local_only",
            one_farm_guard=True,
            created_at=now,
            updated_at=now,
        )
        session.add(farm)
        await session.flush()

        membership = FarmMembership(
            membership_id="mem_boss_farm_local",
            account_id="boss_001",
            farm_id="farm_local",
            role_preset="boss",
            status="active",
            created_at=now,
            updated_at=now,
        )
        session.add(membership)
        await session.flush()

        tomato = Plant(
            plant_id="tomato_001",
            farm_id="farm_local",
            canonical_label="Tomato 001",
            display_name="Tomato 001",
            state="active",
            created_by_actor_ref="system_seed",
            created_at=now,
        )
        session.add(tomato)
        await session.flush()

        await session.commit()
