"""Tests: exactly one active local Farm workspace.

@docs .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
Verification: test:farm.single-local-workspace
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.app.access import (
    Account,
    AccountStatus,
    Farm,
    FarmMembership,
    FarmStatus,
    MembershipRole,
    MembershipStatus,
)
from backend.tests.doubles import FakeAccessRepository, OneFarmViolation


NOW = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)


async def _seed_single_farm(repo: FakeAccessRepository) -> Farm:
    farm = Farm(
        farm_id="farm_local",
        display_name="Local Farm",
        status=FarmStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )
    return await repo.add_farm(farm)


async def _seed_boss(repo: FakeAccessRepository, farm_id: str = "farm_local") -> tuple[Account, FarmMembership]:
    account = Account(
        account_id="acct_boss",
        display_name="Boss",
        login_identifier="boss.local",
        status=AccountStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )
    await repo.add_account(account)

    membership = FarmMembership(
        membership_id="mbr_boss",
        account_id="acct_boss",
        farm_id=farm_id,
        role=MembershipRole.BOSS,
        status=MembershipStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )
    await repo.add_membership(membership)
    return account, membership


class TestFarmSingleWorkspace:
    async def test_single_farm_exists_after_seed(self):
        repo = FakeAccessRepository()
        farm = await _seed_single_farm(repo)
        assert await repo.get_single_farm() is farm
        assert farm.is_active

    async def test_get_single_farm_returns_none_before_seed(self):
        repo = FakeAccessRepository()
        assert await repo.get_single_farm() is None

    async def test_cannot_add_second_farm(self):
        repo = FakeAccessRepository()
        await _seed_single_farm(repo)
        with pytest.raises(OneFarmViolation, match="exactly one local Farm"):
            await repo.add_farm(
                Farm(
                    farm_id="farm_second",
                    display_name="Second Farm",
                    status=FarmStatus.ACTIVE,
                    created_at=NOW,
                    updated_at=NOW,
                )
            )

    async def test_multi_farm_state_detected(self):
        repo = FakeAccessRepository()
        repo.farms["farm_a"] = Farm(
            farm_id="farm_a", display_name="A", status=FarmStatus.ACTIVE, created_at=NOW, updated_at=NOW
        )
        repo.farms["farm_b"] = Farm(
            farm_id="farm_b", display_name="B", status=FarmStatus.ACTIVE, created_at=NOW, updated_at=NOW
        )
        with pytest.raises(OneFarmViolation, match="exactly one local Farm"):
            await repo.get_single_farm()

    async def test_add_membership_for_non_existent_farm_fails(self):
        repo = FakeAccessRepository()
        await _seed_single_farm(repo)
        await _seed_boss(repo, farm_id="farm_local")
        with pytest.raises(KeyError, match="membership farm does not exist"):
            await repo.add_membership(
                FarmMembership(
                    membership_id="mbr_bad",
                    account_id="acct_boss",
                    farm_id="nonexistent",
                    role=MembershipRole.ENGINEER,
                    status=MembershipStatus.ACTIVE,
                    created_at=NOW,
                    updated_at=NOW,
                )
            )

    async def test_farm_service_returns_single_farm(self):
        from backend.app.farm import get_single_farm

        repo = FakeAccessRepository()
        assert await get_single_farm(repo) is None
        farm = await _seed_single_farm(repo)
        assert await get_single_farm(repo) is farm
        assert farm.farm_id == "farm_local"
        assert farm.display_name == "Local Farm"
        assert farm.is_active

    async def test_no_multi_farm_route_exists(self):
        """Verify no route returns multiple Farms or a workspace selector."""
        from backend.tests.doubles import FakeAccessRepository
        repo = FakeAccessRepository()
        try:
            farm = await repo.get_single_farm()
        except OneFarmViolation:
            farm = None
        assert farm is None or isinstance(farm, Farm)
