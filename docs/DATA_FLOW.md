# Unified Message Data Flow

```mermaid
sequenceDiagram
  participant C as Customer
  participant API as Conversation API
  participant AI as Mock AI Provider
  participant Rules as Business Rule Services
  participant DB as Customer Intelligence Store
  participant Bank as Bank Portal
  C->>API: Customer message
  API->>DB: Persist message and context
  API->>AI: Intent, entities, sentiment, response
  AI-->>API: Normalized analysis
  API->>Rules: Service, lead, retention, routing evaluation
  Rules->>DB: Persist reusable intelligence
  API-->>C: Approved conversational response + safe actions
  DB-->>Bank: Customer 360, queues, leads, risks, opportunities
```

Processing order: receive and validate message; load or create conversation; classify intent; extract entities; analyze sentiment/emotion/urgency; detect service and lead needs; update context; score lead and retention risk; evaluate routing; generate an approved response; persist the complete interaction; expose safe customer actions and internal explainability.

Sales recommendations are suppressed conceptually when sentiment is highly negative or a serious complaint is unresolved. Communication always remains a reviewed employee action.

