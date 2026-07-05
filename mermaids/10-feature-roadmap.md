# 10. Feature roadmap MVP

Концептуальная зависимость product slices. Это не task scheduler graph.

```mermaid
flowchart LR
    F0[FT-000 Foundation]
    F1[FT-001 Accounts Sessions ActorContext]

    subgraph Access[EP-001 Access and Admin]
        F2[FT-002 Farm Plant lifecycle and grants]
        F3[FT-003 Boss Admin and audit]
    end

    subgraph Operations[EP-002 Plant Operations]
        F4[FT-004 Daily check-in]
        F5[FT-005 Photo intake]
        F6[FT-006 Runtime state and history]
    end

    subgraph Agents[EP-003 Agent Runtime]
        F7[FT-007 Runtime decisions and MessageEnvelope]
        F8[FT-008 Agent Chat Bus and UI Feed]
        F9[FT-009 Vision observation]
        F10[FT-010 Advisor missing-data policy]
    end

    subgraph Safety[EP-004 Safety and Follow-up]
        F11[FT-011 Safety Gate]
        F12[FT-012 Human tasks and outcomes]
    end

    subgraph Governance[EP-005 Companion Governance]
        F13[FT-013 Companion proposals and decisions]
    end

    subgraph Surface[EP-006 Privacy and Operator Surface]
        F14[FT-014 Dataset governance]
        F15[FT-015 Local security and storage]
        Demo{First demo readiness}
        F16[FT-016 Web App PWA]
    end

    F0 --> F1
    F1 --> F2 --> F3
    F2 --> F4 --> F5 --> F6
    F6 --> F7 --> F8
    F5 --> F9 --> F10
    F10 --> F11 --> F12
    F8 --> F13
    F5 --> F14
    F1 --> F15
    F3 --> Demo
    F6 --> Demo
    F8 --> Demo
    F9 --> Demo
    F10 --> Demo
    F12 --> Demo
    F13 --> Demo
    F14 --> Demo
    F15 --> Demo
    Demo --> F16

    classDef done fill:#d9f7df,stroke:#238636,color:#111;
    classDef planned fill:#eef1f4,stroke:#6e7781,color:#333,stroke-dasharray:5 5;
    class F0,F1 done;
    class F2,F3,F4,F5,F6,F7,F8,F9,F10,F11,F12,F13,F14,F15,F16,Demo planned;
```

На текущий момент реализованы Foundation и FT-001. Остальные product features
остаются в состоянии planning/specification.

