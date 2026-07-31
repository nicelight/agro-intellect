"""Plant-scoped Companion IssueStack and proposal authority."""

from .contracts import (
    ApprovedGovernanceSummaryV1,
    AttentionStatus,
    CloseCompanionIssueCommandV1,
    CompanionDecisionResultV1,
    CompanionGovernanceError,
    CompanionGovernanceErrorCode,
    CompanionGovernanceValidationError,
    CompanionIssueCloseResultV1,
    CompanionIssueDetailV1,
    DecideCompanionProposalCommandV1,
    DecisionValue,
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
    "ApprovedGovernanceSummaryV1",
    "AttentionStatus",
    "CloseCompanionIssueCommandV1",
    "CompanionDecisionResultV1",
    "CompanionGovernanceError",
    "CompanionGovernanceErrorCode",
    "CompanionGovernanceRepository",
    "CompanionGovernanceService",
    "CompanionGovernanceValidationError",
    "CompanionHumanAttention",
    "CompanionIssue",
    "CompanionIssueCloseResultV1",
    "CompanionIssueDetailV1",
    "CompanionProposal",
    "CurrentGovernanceScope",
    "DecisionRecord",
    "DecideCompanionProposalCommandV1",
    "DecisionValue",
    "IssueStackPageV1",
    "IssueStatus",
    "PersistCompanionProposalCommandV1",
    "ProposalEffect",
    "ProposalPersistenceResultV1",
    "ProposalState",
    "SuggestedResolution",
]
