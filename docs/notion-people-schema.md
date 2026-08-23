# Notion `People` database — schema contract

The workflow's **Notion: create People row** node writes these properties by
name. Names and types must match exactly (the node addresses them as
`<Name>|<type>`).

| Property     | Type   | Written as                               |
|--------------|--------|------------------------------------------|
| `Name`       | Title  | `First Last`                             |
| `Work Email` | Email  | `first.last@<DEMO_DOMAIN>`               |
| `Department` | Select | from the HRIS payload (option auto-created) |
| `Role`       | Text   | HRIS `employee.title`                    |
| `Manager`    | Email  | HRIS `employee.manager_email`            |
| `Start Date` | Date   | HRIS `employee.start_date` (date only)   |
| `Status`     | Select | always `Provisioned`                     |
| `Employee ID`| Text   | HRIS `employee.id`                       |

## Setup (≈10 minutes, free workspace)

1. New page → `/database` → **Table - Full page**, name it `People`. Rename the
   default `Name` title column if needed; add the seven other properties above
   (type matters: Email, Select, Text, Email, Date, Select, Text).
2. <https://www.notion.so/my-integrations> → **New integration** → name
   `n8n-hris`, associated workspace = this one, type **Internal**. Capabilities:
   *Read content* + *Insert content* (Update not needed). Save → copy the
   **Internal Integration Secret** → it goes into the n8n credential named
   exactly **`Notion (n8n-hris)`** (type: Notion API).
3. Back on the `People` database page: `•••` (top right) → **Connections** →
   **Connect to** → `n8n-hris`. Skipping this is the classic
   `object_not_found` / "Could not find data source" error.
4. Get the **data-source id** (Notion API 2025-09+ addresses databases through
   their data sources; this is *not* the 32-hex database id in the URL):

   ```bash
   curl -s -H "Authorization: Bearer <integration secret>" \
        -H "Notion-Version: 2025-09-03" \
        https://api.notion.com/v1/databases/<database_id>
   ```

   `database_id` = the 32-hex string in the database URL before `?v=`.
   Read `data_sources[0].id` from the response and put it in `.env` as
   `NOTION_DATA_SOURCE_ID`. (Alternative without curl: open the imported
   workflow in n8n, on the Notion node switch *Data Source* to "From list",
   pick `People`, copy the id it shows, then switch back to the expression.)

## Reused by the tool-familiarity spike

The same workspace gets `Assets` (asset tag, model, assigned to → relation to
People, status) and `Tickets` (title, requester → relation to People, status,
priority, asset → relation to Assets), a linked view "My open tickets", and one
automation (Status → Resolved sets `Resolved At`). Those are not used by the
workflow.
