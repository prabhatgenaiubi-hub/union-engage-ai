# Union Engage AI

A full-stack banking AI proof of concept demonstrating how one customer conversation creates reusable intelligence across customer service, sentiment, lead qualification, financial coaching, guided sales, retention, and service routing.

All names, balances, interactions, and scores are synthetic. This is not production banking software and lead scores are not underwriting decisions.

## Run with Docker

1. Copy `.env.example` to `.env` and change `JWT_SECRET`.
2. Run `docker compose up --build`.
3. Open the customer/bank experience at `http://localhost:3000`.
4. Open Swagger at `http://localhost:8000/docs`.

PostgreSQL migrations and the idempotent synthetic seed run automatically in the backend container.

## Demo credentials

| Experience | Login | Password | Role |
|---|---|---|---|
| Customer | `CUST001` | `Customer@001` | Customer |
| Customer | `CUST002` | `Customer@002` | Customer |
| Customer | `CUST003` | `Customer@003` | Customer |
| Bank | `ADMIN001` | `Admin@001` | Admin |
| Bank | `ADMIN002` | `Admin@002` | Admin |
| Bank | `ADMIN003` | `Admin@003` | Admin |

## Local development

Backend (Python 3.12): create a virtual environment, install `backend/requirements.txt`, set `DATABASE_URL`, then run `alembic upgrade head`, `python -m app.seed.seed`, and `uvicorn app.main:app --reload` from `backend/`.

Frontend (Node 22): from `frontend/`, run `npm install` then `npm run dev`. Set `NEXT_PUBLIC_API_URL=http://localhost:8000/api` when the default is unsuitable.

Tests: run `pytest` from `backend/`. Tests use SQLite and cover authentication, authorization, chat processing, lead scoring, attrition scoring, routing, and service-request creation.

## Demo prompts

- `What documents are required for a home loan?`
- `Mera debit card kal se kaam nahi kar raha hai.`
- `This is the third time I am contacting you and nobody has solved my problem.`
- `I am planning to buy a house. I need a ₹40 lakh home loan.`
- `I earn ₹70,000 monthly and want to save ₹5 lakh for a car.`
- `I am fed up with this bank. I want to close my account.`
- `My account was wrongly debited five days ago and nobody has helped.`

## Repository

`frontend/` contains the Next.js App Router interfaces and reusable components. `backend/app/` contains API, models, schemas, services, security, persistence, and seed domains. `backend/alembic/` holds migrations; `backend/tests/` holds logic and API tests; `docs/` contains architecture and data-flow diagrams.

## AI and business rules

The provider abstraction supports `AI_PROVIDER=sarvam` for multilingual customer chat and `AI_PROVIDER=ollama` for the locally installed `llama3:latest` model. Sarvam credentials remain server-side in `SARVAM_API_KEY`. Selected Indic-language input is translated for deterministic intent and routing rules, while Sarvam generates the customer-facing reply in the selected language. If an AI provider is unavailable, the backend falls back to safe deterministic responses.

To return to fully deterministic mode, set `AI_PROVIDER=mock`. For a local backend outside Docker, use `OLLAMA_BASE_URL=http://localhost:11434`.

Sentiment analysis is always performed on English text. Customer messages in Hindi or other languages are translated to English first (Sarvam for a selected supported Indic language, otherwise the configured local Ollama model), then classified locally with `cardiffnlp/twitter-roberta-base-sentiment-latest`. The classifier is downloaded on first use and cached by Hugging Face. Set `LOCAL_SENTIMENT_LOCAL_FILES_ONLY=true` after pre-downloading it for a fully offline deployment, or `LOCAL_SENTIMENT_ENABLED=false` to use the deterministic fallback.

Admins can upload PDF knowledge from `/bank/admin/knowledge`. The backend extracts page-aware chunks with `pypdf`, generates 768-dimensional vectors using local `nomic-embed-text`, and stores them in PostgreSQL with `pgvector`. Uploaded documents default to internal access; only documents explicitly approved for the customer audience are searched by customer chat. PDF matches are searched before curated article matches and responses include document/page citations.

The login-page assistant stores public conversations separately from signed-in customer chats. Bank employees can review them under **External Chats**. When a visitor expresses product interest, the assistant asks for name, phone, and email before continuing; completed contacts appear under **External Leads**. Visitors can type `Skip` to continue without creating a lead. The public session is resumed in the same browser using a random session token.

The separate public assistant reuses the signed-in assistant's PDF vector retriever and curated article search. It searches a wider pool of customer-approved knowledge, ranks the evidence, and shows document titles and page numbers with grounded replies. Internal-only documents and account data remain unavailable before sign-in.

Rules prioritize complaint resolution over selling, create attrition signals for closure intent, route negative repeat contacts to priority queues, generate leads from product interest, and attach a reason to every internal score or recommendation. Generated communications are never automatically sent.

## Environment variables

See `.env.example`. `DATABASE_URL`, `JWT_SECRET`, token lifetime, CORS, provider selection, and optional provider credentials are server configuration. Only `NEXT_PUBLIC_API_URL` is exposed to the frontend.

## Production gaps

Before real use, replace demo authentication with enterprise IAM/MFA; add field-level encryption and secrets management; formalize data residency, consent, retention, and audit immutability; add robust rate limiting and fraud controls; complete accessibility and penetration testing; establish human oversight and model-risk governance; integrate approved core-banking/service systems; and deploy with monitored backups, high availability, and disaster recovery.

See [architecture](docs/ARCHITECTURE.md) and [message data flow](docs/DATA_FLOW.md).
