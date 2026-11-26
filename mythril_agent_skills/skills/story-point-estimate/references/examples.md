# Estimation Examples

Worked examples of the clarify-first flow. Read these when unsure how many
questions to ask or how to summarize the generated workbook.

## Example 1: Simple feature request

**User input**: "We need a password reset flow. User clicks 'Forgot Password' on the
login page, enters email, gets a reset link, sets a new password."

**Skill response** (after reading the input):

> I can break this down but first a few questions:
>
> **Email delivery**: Are you using an existing email service (SendGrid, SES) or do
> we need to set that up? What email template format?
>
> **Token security**: How long should the reset link be valid? Single-use or reusable?
> Rate limiting on reset requests?
>
> **Error handling**: What happens if the email doesn't exist in the system — show a
> generic message or specific error?
>
> **Non-functional**: Do we need audit logging for password changes? Notification
> to the user when password is changed? Any password complexity rules?

Then after answers — generate the workbook and summarize:

> Generated `estimate_password_reset_20260728_143022.xlsx` with the following:
>
> **Estimates sheet:** 5 items, 9 total points
> - 3 functional stories (Auth), 6 points
> - 2 CFR items (Security + Monitoring), 3 points
> - All points linked to Summary sheet formula
>
> **RAID sheet:** rate-limit abuse risk, email deliverability dependency
>
> **Summary sheet:** Medium confidence overall — email service setup is the main unknown
>
> Would you also like a Markdown version?

## Example 2: Ambiguous requirements

**User input**: "Build a dashboard for our IoT devices."

**Skill response**:

> A dashboard can mean many things. Let me ask a few questions to narrow it down:
>
> **Data & Scope:**
> - What data should the dashboard show? (device status, metrics, alerts, trends?)
> - How many devices? What's the expected data volume?
> - Real-time or batch-refresh?
>
> **Users & Access:**
> - Who is the primary user? (operations, executives, customers?)
> - Multi-tenant? Does each customer see only their own devices?
> - Any role-based access (viewer vs. editor vs. admin)?
>
> **Technical:**
> - What's the data source? (time-series DB, relational DB, API aggregation?)
> - Any specific chart library or design system to use?
> - Web-only or also mobile?
>
> **Non-functional:**
> - Target page load time? Data freshness (real-time / 5min / hourly)?
> - Do we need export (CSV, PDF)? Scheduled reports?
