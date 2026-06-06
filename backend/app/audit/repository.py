"""In-memory audit repository for admin audit records."""

from __future__ import annotations

from backend.app.audit.models import AdminAuditAction, AdminAuditRecord


class InMemoryAuditRepository:
    """Simple list-based store for AdminAuditRecord."""

    def __init__(self) -> None:
        self._records: list[AdminAuditRecord] = []

    def add_record(self, record: AdminAuditRecord) -> None:
        self._records.append(record)

    def list_records(
        self,
        account_id: str | None = None,
        action: AdminAuditAction | None = None,
        limit: int = 50,
    ) -> list[AdminAuditRecord]:
        results = list(self._records)
        if account_id is not None:
            results = [r for r in results if r.actor_account_id == account_id]
        if action is not None:
            results = [r for r in results if r.action is action]
        return results[:limit]

    def get_records_for_farm(
        self,
        farm_id: str,
        limit: int = 50,
    ) -> list[AdminAuditRecord]:
        results = [r for r in self._records if r.farm_id == farm_id]
        return results[:limit]
