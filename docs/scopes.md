# Credentials and scopes

Three credentials, created once in the n8n UI (**Credentials → Add**). The workflow JSON
references them **by these exact names**; `n8n import:workflow` links them by name.

| Credential name (exact)  | n8n type      | What goes in it                                  | Used by                                                          |
|--------------------------|---------------|--------------------------------------------------|------------------------------------------------------------------|
| `HRIS Webhook Token`     | Header Auth   | Name `X-HRIS-Token`, Value = `HRIS_WEBHOOK_TOKEN` from `.env` | `HRIS webhook` (ingress gate: wrong/missing header → 403, no execution) |
| `Slack Bot (n8n-hris)`   | Slack API     | Bot User OAuth Token `xoxb-…` from the app built with `docs/slack-app-manifest.yml` | approval request, channel invite, summary, error alert, `users.lookupByEmail` |
| `Notion (n8n-hris)`      | Notion API    | Internal Integration Secret                       | `Notion: create People row`                                      |

## Slack bot scopes (from the manifest)

| Scope                | Why                                                        |
|----------------------|------------------------------------------------------------|
| `chat:write`         | post the approval request, the summary, the alert          |
| `chat:write.public`  | post to public channels the bot was not invited to         |
| `channels:read`      | resolve channel ids                                        |
| `channels:manage`    | `conversations.invite` into public channels                |
| `groups:write`       | `conversations.invite` into private channels               |
| `users:read`, `users:read.email` | `users.lookupByEmail`                          |
| `users.profile:read` | n8n's credential test                                      |

The bot still has to be **a member** of a channel to invite someone into it: `/invite @n8n-hris`.

## Notion

Internal integration with *Read content* + *Insert content*, **connected to the `People`
database** (`•••` → Connections). The node addresses the database by its **data-source id**
(`NOTION_DATA_SOURCE_ID`), see `docs/notion-people-schema.md`.

## Google Workspace (mocked here)

The two Directory calls are plain HTTP Request nodes against `GOOGLE_ADMIN_BASE_URL`.
To run them against a real tenant:

1. Set `GOOGLE_ADMIN_BASE_URL=https://admin.googleapis.com`.
2. Create a **Google OAuth2 API** credential in n8n with scopes
   `https://www.googleapis.com/auth/admin.directory.user` and
   `https://www.googleapis.com/auth/admin.directory.group.member`, authorized as a
   Workspace **admin** of that tenant (or a service account with domain-wide delegation).
3. On `Google: lookup user`, `Google: create user`, `Google: add to group` set
   *Authentication → Predefined Credential Type → Google OAuth2 API* and pick it.

The request bodies already match the Directory API `users.insert` and `members.insert`
resources. Do this against a test tenant, never a tenant you care about — `users.insert`
creates real accounts.
