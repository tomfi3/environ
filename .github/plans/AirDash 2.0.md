# AirDash 2.0 — Comprehensive Project Specification

*A multimodal air-quality intelligence platform*

---

## 1. Vision

Create a single public web application that:

* Visualises live and historic air-quality data from the Supabase database.
* Lets users explore the data and relevant policy documents through natural-language chat (text and voice).
* Automatically ingests & parses new policy documents (AQAPs, ASRs, strategies) found on council websites and other sources.
* Produces structured knowledge (actions, targets, locations, dates) that the chatbot can cite and link back to original passages.
* Gives power-users (researchers, journalists, policy makers) programmatic access via an MCP-compliant API layer.

---

## 2. High-Level Architecture

```
          ┌──────────────────────┐
          │   Dash Front-End     │
          │  (Graphs + Chat UI)  │
          └───────▲────┬─────────┘
                  │    │WebSocket
                  │    ▼
          ┌──────────────────────┐
          │  Chat Orchestrator   │◄───────────── Local policy store (vector DB)
          │  (FastAPI + Llama-   │
          │   Index / LangChain) │
          └─────┬─▲────┬─────────┘
                │ │    │Tool calls (MCP)
 Sensors API    │ │    │                 Crawler Scheduler
  (Supabase)    │ │    │                     ▲
      ▲         │ │    │                     │
      │   SQL/REST│    │PostgREST            │
      │          ▼ ▼    ▼                    ▼
┌──────────────────────────────┐   ┌──────────────────────┐
│        Supabase DB           │   │  AQ Doc Crawler      │
│  (sensor tables + new policy │──▶│  (Python + httpx +   │
│   tables + action table)     │◄──│   BeautifulSoup)     │
└──────────────────────────────┘   └──────────────────────┘
```

---

## 3. Data Stores

| Store                                     | Purpose                                            | Technology                        | Notes                  |
| ----------------------------------------- | -------------------------------------------------- | --------------------------------- | ---------------------- |
| `sensors`, `*_averages`, `active_sensors` | Existing monitoring data                           | Supabase Postgres                 | Already live           |
| `policy_documents`                        | Raw PDFs and metadata                              | Supabase storage + Postgres table | Output of crawler      |
| `policy_chunks`                           | Text chunks, embeddings, source offsets            | Supabase Postgres + pgvector      | 1536-D OpenAI ada-002  |
| `parsed_actions`                          | Normalised actions (e.g. “Electrify bus route 73”) | Postgres                          | Produced by the parser |
| `vector_store`                            | Same as `policy_chunks`                            | pgvector via LlamaIndex           | Used at query time     |

---

## 4. Supabase Schema Additions

```sql
create table policy_documents (
  doc_id         uuid primary key default gen_random_uuid(),
  council_name   text,
  document_type  text,  -- AQAP, ASR, Strategy, Report
  year           int,
  source_url     text,
  file_path      text,
  file_hash      text unique,
  date_added     timestamptz default now(),
  status         text       -- pending | parsed | failed
);

create table policy_chunks (
  chunk_id       bigserial primary key,
  doc_id         uuid references policy_documents(doc_id),
  chunk_index    int,
  text           text,
  embedding      vector(1536),
  char_start     int,
  char_end       int
);

create table parsed_actions (
  action_id      bigserial primary key,
  doc_id         uuid references policy_documents(doc_id),
  action_type    text,       -- electrification, ULEZ, school street ...
  description    text,
  geo_entities   text[],     -- e.g. ["bus route 73"]
  start_year     int,
  end_year       int,
  status         text        -- proposed | in-progress | complete
);
```

---

## 5. Crawler & Ingestion Pipeline

### 5.1 Discovery

* Seed list of council air-quality pages (`council_targets.yml`).
* Google Custom Search fallback (`site:richmond.gov.uk "Air Quality Action Plan" filetype:pdf`).

### 5.2 Download & Fingerprint

* `httpx` stream to disk (tmp dir or S3).
* SHA-256 hash to avoid duplicates.

### 5.3 Metadata Extraction

* Regex and heuristics on filename and first page.
* Example: `Richmond_AQAP_2023.pdf` → council=`Richmond`, type=`AQAP`, year=2023.

### 5.4 Storage

* Upload to Supabase Storage bucket `policy_docs`.
* Insert `policy_documents` row with `status='pending'`.

### 5.5 Parsing Worker

* Runs on Render background worker or Supabase Edge Function (Python).
* PDF → text (`pdfplumber`).
* Chunking (LlamaIndex `RecursiveCharacterTextSplitter`, 512-token overlap).
* OpenAI embedding → `policy_chunks`.
* Rule-based + GPT function-calling parser extracts candidate actions → `parsed_actions`.
* Update `status='parsed'`.

### 5.6 Scheduling

* APScheduler job: every day 04:00 UTC.
* Manual “Sync now” button for admins in Dash.

---

## 6. Chat Module

### 6.1 Model Context Protocol (MCP)

We’ll expose the following **tools** to the LLM:

| Tool Name           | Description                                                        | Parameters                                  |
| ------------------- | ------------------------------------------------------------------ | ------------------------------------------- |
| `sql.run`           | Run SQL on Supabase and return rows                                | `query` (string)                            |
| `sensors.aggregate` | Wrapper that selects from `*_averages` with filters                | `pollutant` `id_sites` `year` `month` `agg` |
| `geo.zoom_map`      | Command for the front-end to re-centre & zoom                      | `lat` `lon` `zoom`                          |
| `filters.set`       | Change filter state (boroughs, pollutant, sensorType, year, month) | key / value pairs                           |
| `policy.search`     | Semantic search over `policy_chunks`                               | `query` (string) `top_k`                    |
| `policy.source`     | Retrieve original PDF snippet via chunk\_id                        | `chunk_id`                                  |

The orchestrator implements MCP: convert LLM function calls into actual back-end actions, then pass results back as JSON.

### 6.2 System + Memory Prompts

* **System**: “You are AirDash Assistant, specialised in London air-quality data and policy.”
* **Memory**: concat last 10 messages; add current filter state (boroughs, pollutant, etc.) and visible graph extents.
* **Tools context**: JSON schema for each tool, auto-generated for the model.

### 6.3 User Flows

| Scenario                                         | LLM Tool Calls                                                                                                        | Front-end Reaction                                  |
| ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| “Show me where NO2 exceeded WHO limits in 2022.” | `filters.set(pollutant='NO2', year=2022)`                                                                             | Dash callbacks re-render map/charts                 |
| “Zoom into Putney High St.”                      | `geo.zoom_map(lat, lon, zoom=15)`                                                                                     | Map centres on Putney                               |
| “What actions are proposed near bus route 73?”   | `policy.search("bus route 73")` → choose chunk → summarise; optional follow-up `sensors.aggregate` for nearby sensors | Assistant answers, can suggest highlighting sensors |

Voice input is converted to text client-side; responses are read aloud with Web Speech API (optional).

---

## 7. Dash Front-End Additions

* **Chat Panel** (right drawer)

  * Text box, send button, mic button.
  * “Allow chat to control dashboard” checkbox: stores `chat_control_enabled` in `dcc.Store`.

* **Admin Panel** (route `/admin` or auth-guarded modal)

  * Upload new PDFs (drag-and-drop) → triggers parser.
  * “Sync web docs” button → triggers crawler job.
  * Job logs table.

* **Map**

  * Receives `geo.zoom_map` events via `dcc.Store` and relayouts accordingly.

---

## 8. Security & Rate-Limiting

* Supabase Row Level Security enabled for sensitive tables.
* Admin role required for uploads / crawler triggers.
* API keys (OpenAI, Supabase service) stored in Render environment.
* Chat rate limit: 20 queries/min per IP.

---

## 9. Deployment

| Target            | Platform                  | Command                  |
| ----------------- | ------------------------- | ------------------------ |
| Web service       | Render (Free)             | `gunicorn app:server`    |
| Background worker | Render Cron               | `python crawl_runner.py` |
| Parsing worker    | Render Background service | `python parse_queue.py`  |

Keep-alive ping job already configured: every 10 min, 08:00-20:00 local.

---

## 10. Implementation Phases

1. **Foundations**

   * Stabilise Supabase schema; add new tables.
   * Ship Dash chat-panel (no control, no policy search yet).

2. **Document Pipeline**

   * Build crawler + parser; ingest 3 sample councils.
   * Populate vector store; expose `policy.search` tool.

3. **MCP Orchestrator**

   * Implement FastAPI tool server.
   * Connect LlamaIndex agent with tools.

4. **Dashboard Control**

   * Implement `filters.set`, `geo.zoom_map`.
   * Add “Allow chat control” toggle.

5. **Voice + Admin Tools**

   * Web Speech API integration.
   * Admin upload page and manual sync.

6. **Testing & UX polish**

   * Unit + integration tests (pytest, Playwright).
   * Accessibility, mobile view, loading spinners.

7. **Launch & Iteration**

   * Public beta.
   * Collect feedback; add more councils and datasets.

---

## 11. Parsing Strategy Details

| Layer           | Technique                                                                             | Output                |
| --------------- | ------------------------------------------------------------------------------------- | --------------------- |
| Text Extraction | `pdfplumber`                                                                          | Raw text              |
| Chunking        | 512 tokens, 20-token overlap                                                          | Structured chunks     |
| Embedding       | `text-embedding-ada-002`                                                              | 1536-D vector         |
| Action Mining   | GPT with function calling schema: `{"action_type": "...", "description": "...", ...}` | `parsed_actions` rows |
| Linkage         | Named-entity + Regex (bus route, road names, sensor IDs)                              | `geo_entities` array  |

Chunks keep `char_start` / `char_end`, so the chatbot can always reconstruct the exact page & paragraph (and give the user a “View in document” link).

---

## 12. User Personas & Use-Cases

| Persona         | Goal                                                          | Key Features                                     |
| --------------- | ------------------------------------------------------------- | ------------------------------------------------ |
| Local resident  | Understand pollution on their street; check council promises. | Map filters, chat Q\&A, policy doc snippets      |
| Council officer | Monitor sensor compliance; track AQAP progress.               | Chart tools, parsed\_actions table, download CSV |
| Journalist      | Investigate hotspots; quote original docs.                    | Semantic search, citation links, map zoom        |
| Researcher      | Export raw data for modelling.                                | Export buttons, Supabase SQL endpoint            |

---

## 13. Future Enhancements

* Mobile PWA offline mode.
* Real-time WebSocket push of hourly sensor updates.
* Forecasting (Prophet / SARIMA) and what-if scenarios.
* User accounts for saving dashboards and alerts.

---

### 14. Mobile-First Experience (Chat-Centric)

| Area                        | Layout & Behaviour                                                                                                                                                                                                                                                           | Technical Notes                                                                                                    |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Default View (portrait)** | 1. **Header** – small title bar with a mic icon. <br>2. **Chat Bar** – always visible at the bottom, 56 px high (text input, send icon, mic button). <br>3. **Full-screen Map** – occupies remaining viewport. <br>   *Tap on map hides chat history until user swipes up.*  | Dash `dcc.Graph` stretches to `100 vh` minus header + chat‐bar.                                                    |
| **Chat Drawer / History**   | Swipe-up or tap on chat bar ➜ drawer reveals last ∼10 messages; occupies up to 70 % height.                                                                                                                                                                                  | Implement with CSS `position: fixed; bottom: 56px;` and `transform: translateY(100%)`. Touch events handled in JS. |
| **Charts Panel**            | Swipe-left from right edge ➜ side-panel shows mini time-series and bar chart. Panel auto-updates with current filters.                                                                                                                                                       | Use `dcc.Tabs` inside `SlideOver` component. Deactivate heavy charts if panel is closed (to save CPU).             |
| **Voice Flow**              | Press-and-hold mic: Web Speech API streams interim results to backend (`/chat/stream`). Release to send final query. Assistant replies with TTS unless phone is muted.                                                                                                       | Fallback to text if `window.SpeechRecognition` unavailable.                                                        |
| **Interactions**            | *User*: “Show PM 2.5 in Teddington last year.” <br>*LLM*: calls `filters.set` and `geo.zoom_map`, returns answer and refreshes map. <br>*User*: “Compare it to Putney.” <br>*LLM*: splits screen: map keeps current view; bar chart panel opens with both sites highlighted. | All state updates pass through the MCP tool layer, identical to desktop.                                           |
| **Offline / Low-bandwidth** | If no network: cached tiles + last 24 h data displayed; chat disabled.                                                                                                                                                                                                       | LocalStorage cache seeded during first load.                                                                       |
| **Onboarding Hint**         | First visit shows 3-step tooltip overlay: “Tap mic to ask questions”, “Swipe up for history”, “Swipe left for charts”.                                                                                                                                                       | Controlled by `localStorage.hasSeenMobileIntro`.                                                                   |

#### Component Hierarchy (Dash)

```
<Div id="mobile-root">
  <Header />
  <dcc.Graph id="map-graph" />
  <ChatBar>
    <input type="text"> <MicButton/>
  </ChatBar>

  <!-- Off-canvas elements -->
  <ChatDrawer id="chat-drawer">
    <ChatHistory />
  </ChatDrawer>

  <ChartsSlideOver id="charts-panel">
    <Tabs>
      <Tab label="Trend"><dcc.Graph id="ts-small"/></Tab>
      <Tab label="Compare"><dcc.Graph id="bar-small"/></Tab>
    </Tabs>
  </ChartsSlideOver>
</Div>
```

#### Additional Implementation Tasks

1. **Responsive CSS** – media queries switch desktop grid to stacked mobile flow; hide sidebars.
2. **Touch Gestures** – small JS file (`assets/mobile-gestures.js`) handles swipe detection and emits custom Dash events via `dcc.Store`.
3. **Performance Budget** – limit map marker count on mobile to 500 by default; provide “Show all” toggle when zoomed.
4. **Accessibility** – ARIA labels for mic & send buttons; TTS respects OS “Reduce motion / Speak selections” settings.

Add these milestones to *Phase 5: Voice + Admin Tools* in the master roadmap.

