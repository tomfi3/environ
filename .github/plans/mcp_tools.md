# MCP Blueprint for London Environmental Dashboard

## 1  Typical user intents

| Cluster                      | Example utterances                                                                        | Assistant response type                        |
| ---------------------------- | ----------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **Explore data**             | “Show me PM2.5 in Richmond for 2021.”<br>“Compare NO₂ levels across boroughs last month.” | Update filters & charts                        |
| **Compliance / exceedances** | “Which sites breached the UK limit in 2023?”                                              | Data query → summary → highlight on map        |
| **Spatial focus**            | “Zoom into Putney High Street area.”                                                      | Map zoom + optional borough overlay            |
| **Temporal trends**          | “Has air quality in Merton improved since 2010?”                                          | Run multi-year query → line chart + commentary |
| **Policy reference**         | “What does the 2023 Air Quality Action Plan say about PM10?”                              | Retrieve relevant document paragraphs          |
| **Mixed requests**           | “According to the plan, is Wandsworth on track to hit its NO₂ target?”                    | Combine data + policy synthesis                |

---

## 2  Tool catalogue

All tools are declared in MCP’s `tools` block. Each action the assistant can take is expressed as a deterministic tool.

| Tool                     | Purpose                                              | Key parameters (JSON Schema properties)                             |
| ------------------------ | ---------------------------------------------------- | ------------------------------------------------------------------- |
| `update_filters`         | Change dashboard filters and refresh graphs.         | `borough`, `pollutant`, `sensor_type`, `year`, `month`, `averaging` |
| `zoom_map`               | Re-centre & zoom the Plotly Mapbox map.              | `lat`, `lon`, `zoom`                                                |
| `toggle_borough_overlay` | Show / hide shapefile overlays.                      | `borough`, `show`                                                   |
| `get_summary_stats`      | Return mean, max, min, exceedances for a filter set. | `years`, `boroughs`, `pollutants`                                   |
| `highlight_sites`        | Visually emphasise sensors meeting a condition.      | `condition` (field, operator, value)                                |
| `query_policy_doc`       | Semantic / keyword search within stored documents.   | `doc_id`, `query`                                                   |
| `open_policy_section`    | Embed a policy paragraph in the UI.                  | `doc_id`, `section_heading`                                         |
| `export_current_view`    | Download the current dataset as CSV.                 | —                                                                   |
| `download_chart_png`     | Export current chart to PNG/SVG.                     | `chart_id`                                                          |
| `ask_llm_freeform`       | Pure language answer without changing UI.            | `query`                                                             |

---

## 3  Schemas (example)

```jsonc
{
  "name": "update_filters",
  "description": "Change dashboard filters",
  "parameters": {
    "type": "object",
    "properties": {
      "borough":   { "type": "string", "enum": ["Merton","Wandsworth","Richmond"] },
      "pollutant": { "type": "string", "enum": ["NO2","PM2.5","PM10"] },
      "sensor_type": {
        "anyOf": [
          { "type": "string" },
          { "type": "array", "items": { "type": "string" } }
        ]
      },
      "year":      { "type": "integer", "minimum": 2000, "maximum": 2100 },
      "month":     { "type": "integer", "minimum": 1,    "maximum": 12 },
      "averaging": { "type": "string", "enum": ["hourly","daily","monthly","annual"] }
    },
    "additionalProperties": false
  }
}
```

Provide similar JSON-Schema blocks for every tool.

---

## 4  Memory / context objects

### 4.1  Static context (cached)

```json
{
  "boroughs": ["Merton", "Wandsworth", "Richmond"],
  "sensor_types": ["DT","Clarity","Automatic"],
  "first_year": 2000,
  "current_year": 2025,
  "policy_docs": [
    { "id": "AQAP_2023", "title": "Air Quality Action Plan 2023-2028" },
    { "id": "London_WHO_Report", "title": "WHO Guidelines Alignment Report 2024" }
  ]
}
```

### 4.2  Session context (changes during chat)

```json
{
  "current_filters": {
    "borough": ["Merton","Wandsworth"],
    "pollutant": "NO2",
    "year": 2024,
    "month": null,
    "averaging": "annual"
  },
  "map_view": { "lat": 51.445, "lon": -0.22, "zoom": 11.3 },
  "overlays": { "Richmond": false, "Merton": true, "Wandsworth": false },
  "last_tool_calls": []
}
```

### 4.3  Short-term memory

Store the last *N* user/assistant turns so the model can follow the conversation.

---

## 5  Goals and policies for the assistant

1. **Primary goal** – Enable users to understand and act on London borough air-quality data.
2. **Secondary goal** – Provide authoritative policy context on request.
3. Never disclose database credentials or entire large documents.
4. Prefer tool calls over freeform answers when a UI change is helpful.
5. If a request is purely informational → use `ask_llm_freeform`.
6. Cite policy documents by id and section heading when used.
7. Warn politely if the user requests data outside 2000-present.

Instruction snippet:

```
• Use a tool whenever a dashboard change is needed.
• Keep explanations under 100 words unless the user asks for detail.
• Cite policy docs by id and section.
• If a request mixes data and policy, handle data first.
```

---

## 6  Example dialogue

| Step | User                                | Assistant reasoning | Assistant output                                                                                   |
| ---- | ----------------------------------- | ------------------- | -------------------------------------------------------------------------------------------------- |
| 1    | Show me PM2.5 in Richmond for 2022. | Must set filters    | `update_filters` → `{ "borough":"Richmond","pollutant":"PM2.5","year":2022,"averaging":"annual" }` |
|      |                                     |                     | Brief textual summary after UI refresh                                                             |
| 2    | Zoom into Teddington.               | Map change          | `zoom_map` → `{ "lat":51.424, "lon":-0.331, "zoom":14 }`                                           |
| 3    | Is that above WHO limits?           | Info only           | `ask_llm_freeform` with guideline comparison                                                       |
| 4    | What does the AQAP say about PM2.5? | Need doc search     | `query_policy_doc` then `open_policy_section`                                                      |

---

## 7  Implementation steps

1. **Expose tool endpoints** in your Dash/Flask backend.
2. **Register tools** with the Model Context Protocol (or OpenAI `functions`).
3. **Send current context** with every chat completion call.
4. **Execute returned tool calls** server-side, then loop the result back to the user/chat.
5. **Embed policy docs** using a vector store (e.g. pgvector) for `query_policy_doc`.
6. Optional future: integrate voice input (STT) and TTS output; underlying MCP logic remains identical.

---

This design lets the assistant handle free-form queries **and** drive the dashboard interactively, without hard-coding specific SQL statements.
