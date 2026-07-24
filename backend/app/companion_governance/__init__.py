"""Plant-scoped Companion IssueStack and proposal authority."""

from .contracts import (
    AttentionStatus,
    CompanionGovernanceError,
    CompanionGovernanceErrorCode,
    CompanionGovernanceValidationError,
    CompanionIssueDetailV1,
    IssueStackPageV1,
    IssueStatus,
    PersistCompanionProposalCommandV1,
    ProposalEffect,
    ProposalPersistenceResultV1,
    ProposalState,
    SuggestedResolution,
)
from .models import (
    CompanionHumanAttention,
    CompanionIssue,
    CompanionProposal,
    DecisionRecord,
)
from .repository import CompanionGovernanceRepository, CurrentGovernanceScope
from .service import CompanionGovernanceService

__all__ = [
    "AttentionStatus",
    "CompanionGovernanceError",
    "CompanionGovernanceErrorCode",
    "CompanionGovernanceRepository",
    "CompanionGovernanceService",
    "CompanionGovernanceValidationError",
    "CompanionHumanAttention",
    "CompanionIssue",
    "CompanionIssueDetailV1",
    "CompanionProposal",
    "CurrentGovernanceScope",
    "DecisionRecord",
    "IssueStackPageV1",
    "IssueStatus",
    "PersistCompanionProposalCommandV1",
    "ProposalEffect",
    "ProposalPersistenceResultV1",
    "ProposalState",
    "SuggestedResolution",
]
