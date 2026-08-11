"""Immutable version-1 product-agent roster metadata."""

from __future__ import annotations

from dataclasses import dataclass


ROSTER_VERSION = 1

#: Generic pending-classification route used by every non-dataset roster member.
RUNTIME_ROUTE_GENERIC = "generic_pending_classification"
#: Registered advisory-only exception route for the two Dataset Agents (AD-011).
RUNTIME_ROUTE_DATASET_ADVISORY = "dataset_advisory_v1"


@dataclass(frozen=True, slots=True)
class RosterAgentV1:
    agent_id: str
    display_name: str
    competence_summary: str
    introduction_text: str
    owning_feature: str
    output_schema_version: int = 1
    runtime_route: str = RUNTIME_ROUTE_GENERIC

    def __post_init__(self) -> None:
        if self.runtime_route not in {
            RUNTIME_ROUTE_GENERIC,
            RUNTIME_ROUTE_DATASET_ADVISORY,
        }:
            raise ValueError("Unsupported runtime route.")


CANONICAL_ROSTER_V1 = (
    RosterAgentV1(
        "companion",
        "Companion Agent",
        "dialogue and governance coordination without replacing specialists, backend rules, or Safety Gate",
        "Я Companion Agent. Помогаю вести диалог и координировать вопросы по растению, не подменяя специалистов и правила безопасности.",
        "FT-013",
    ),
    RosterAgentV1(
        "vision_observation",
        "Vision Observation Agent",
        "photo quality and visual observation; no diagnosis or physical-action recommendation",
        "Я Vision Observation Agent. Проверяю фотографии и описываю только наблюдаемое, не ставя диагнозов и не назначая действий.",
        "FT-009",
    ),
    RosterAgentV1(
        "plant_state",
        "Plant State Agent",
        "trends, uncertainty, and evidence conflicts; no self-confirmation of hypotheses",
        "Я Plant State Agent. Отслеживаю состояние растения во времени, отмечаю неопределённость и противоречия в данных.",
        "FT-009",
    ),
    RosterAgentV1(
        "hydroponics_advisor",
        "Hydroponics Advisor Agent",
        "cautious hydroponic advice and missing-data requests; cannot bypass Safety Gate",
        "Я Hydroponics Advisor Agent. Даю осторожные рекомендации по гидропонике и запрашиваю недостающие данные перед выводами.",
        "FT-010",
    ),
    RosterAgentV1(
        "task_follow_up",
        "Task & Follow-up Agent",
        "checks, measurements, approved human tasks, and 1-3 day follow-up",
        "Я Task & Follow-up Agent. Помогаю вести проверки, измерения, разрешённые задачи и последующее наблюдение за результатом.",
        "FT-012",
    ),
    RosterAgentV1(
        "safety_gate",
        "Safety Gate Agent",
        "physical-action wording classification and approval routing; no actuation",
        "Я Safety Gate Agent. Проверяю рекомендации с физическими действиями и блокирую их до выполнения требований безопасности.",
        "FT-011",
    ),
    RosterAgentV1(
        "dataset_governance",
        "Dataset Governance Agent",
        "dataset lifecycle, evidence, split, and trainability policy",
        "Я Dataset Governance Agent. Контролирую происхождение данных и правила их допустимого использования для обучения.",
        "FT-014",
        runtime_route=RUNTIME_ROUTE_DATASET_ADVISORY,
    ),
    RosterAgentV1(
        "training_data_curator",
        "Training Data Curator Agent",
        "delayed evidence-based training selection; silent by default",
        "Я Training Data Curator Agent. Отбираю обучающие примеры только при наличии разрешённых evidence refs и обычно остаюсь безмолвным.",
        "FT-014",
        runtime_route=RUNTIME_ROUTE_DATASET_ADVISORY,
    ),
)

CANONICAL_AGENT_IDS = frozenset(item.agent_id for item in CANONICAL_ROSTER_V1)

ADVISORY_ONLY_AGENT_IDS = frozenset(
    item.agent_id
    for item in CANONICAL_ROSTER_V1
    if item.runtime_route == RUNTIME_ROUTE_DATASET_ADVISORY
)


def canonical_roster(version: int = ROSTER_VERSION) -> tuple[RosterAgentV1, ...]:
    """Return the immutable roster; unknown versions fail closed."""

    if version != ROSTER_VERSION:
        raise ValueError("Unsupported agent roster version.")
    return CANONICAL_ROSTER_V1


__all__ = [
    "ADVISORY_ONLY_AGENT_IDS",
    "CANONICAL_AGENT_IDS",
    "CANONICAL_ROSTER_V1",
    "ROSTER_VERSION",
    "RUNTIME_ROUTE_DATASET_ADVISORY",
    "RUNTIME_ROUTE_GENERIC",
    "RosterAgentV1",
    "canonical_roster",
]
