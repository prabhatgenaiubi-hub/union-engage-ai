# Financial coaching

Start at Customer → Financial Goals → Start coaching conversation. Coach mode is sent explicitly to the API and is retained through the conversation's saved goal.

The dialogue collects a focus, income, spending excluding repayments, debt repayments, emergency savings, income stability, and dependants. Debt conversations add balance and annual rate; purchase goals add target, existing goal savings, and timeline. Customers can skip unknown figures. Zero is accepted as a real answer.

The coach shows a financial picture for confirmation, discusses priorities and timeline alternatives, and lets the customer choose an action. Agreed actions have a review date; later check-ins are saved. Resume through the Financial Goals card. Separate conversations support separate goals; contributions compete for the same surplus and are not automatically allocated across goals.

Calculations are deterministic; the configured response provider explains the saved state and answers the latest question. If unavailable, a state-specific response is used. Explicitly labelled amounts and answers to the pending question update financial facts; unrestricted language is not automatically treated as verified structured data.

Illustrations reserve 20% of surplus and show three months of expenses plus repayments for regular income, six for variable income. These are visible planning assumptions, not suitability determinations. No investment return or inflation is assumed. Skipped cash-flow facts disable contribution recommendations. Changed facts require confirmation again.

Admins can upload a PDF under **Financial coaching only**, then approve it. Retrieval requires approved status and the coaching audience. Sales/retention documents are excluded, and coaching does not create sales leads or product opportunities.

Example: “I want to save 500000 for a car”, income “50000”, expenses “30000”, repayments “10000”, emergency savings “0”, income “variable”, dependants “skip”, debt “100000”, rate “18”, goal savings “0”, timeline “24 months”. Confirm the picture, compare “what if 36 months”, and choose an action.

Progress reviews happen when the customer returns; review dates do not schedule notifications. The coach does not perform transactions or make investment/product suitability decisions.
