# London Environmental Monitoring Dashboard

A modern, map‑centric **Dash** application for exploring air‑quality data across the London boroughs of **Wandsworth, Richmond upon Thames, and Merton**.

It combines a Supabase‑hosted database, Plotly visualisations and borough boundary overlays to give inspectors and the public an at‑a‑glance view of sensor performance, pollution hotspots and compliance against WHO/UK targets.

---

## 1  Key Features

| Module                | Highlights                                                                                                                                      |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **Interactive Map**   | Live markers coloured by pollutant value; click, box‑drag or lasso to select sensors; optional borough polygons (KMZ → GeoJSON).                |
| **Multi‑chart Panel** | • Annual / monthly trends  • Borough comparison bar‑chart  • Small time‑series preview.<br>All charts respect the active filters and selection. |
| **Dynamic Filters**   | Pollutant, borough, sensor‑type, averaging period, year+month sliders, colour‑scale (WHO / Borough / UK legal).                                 |
| **Supabase Loader**   | Caches the **active\_sensors** view and exposes helpers: `get_annual_data`, `get_monthly_data`, `get_combined_data`, `get_unique_values`.       |
| **Export & Tools**    | CSV export, custom chart titles, borough NO₂ target toggle (30 µg m‑3), legend‑mode cycler, clear‑selection buttons.                            |
| **Responsive UI**     | Expand/collapse map or detailed chart, mobile‑friendly CSS, print stylesheet, subtle animations.                                                |

---

## 2  Folder Structure

```text
├─ assets/                 # CSS + KMZ boundary files
│  ├─ dashboard.css
│  ├─ Wandsworth Area.kmz  # required for borough shading
│  └─ …
├─ main.py                 # Dash application
├─ supabase_io.py          # Database helper / cache layer
├─ requirements.txt        # Python package list
└─ README.md               # (this file)
```

> **Tip:** Any other static assets (logos, screenshots) dropped inside `assets/` will be served automatically by Dash.

---

## 3  Quick Start

### 3.1 Prerequisites

* Python 3.9 +
* libspatialindex / GEOS / GDAL libraries (needed by **geopandas** / **fiona**)
* A Supabase project populated with the tables/views referenced in `supabase_io.py` (`sensors`, `active_sensors`, `annual_averages`, `map_monthly_data`).

### 3.2 Installation & Run

```bash
# clone (or download) the repo
$ git clone https://github.com/<your‑org>/london‑env‑dashboard.git
$ cd london‑env‑dashboard

# create & activate a virtual‑env (optional but recommended)
$ python -m venv .venv
$ source .venv/bin/activate  # Windows: .venv\Scripts\activate

# install Python dependencies
$ pip install -r requirements.txt

# add environment secrets
$ cp .env.example .env          # create if not committed
$ nano .env                     # fill in the values below

SUPABASE_URL=https://xyzcompany.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...

# run the server (default http://127.0.0.1:5000)
$ python main.py
```

A browser window should open automatically (or visit the URL shown in the console).

### 3.3 Docker (optional)

```bash
$ docker build -t envdash .
$ docker run -p 5000:5000 --env-file .env envdash
```

---

## 4  Environment Variables

| Variable            | Description                                                                |
| ------------------- | -------------------------------------------------------------------------- |
| `SUPABASE_URL`      | Base URL of your Supabase project (e.g. `https://xyz.supabase.co`).        |
| `SUPABASE_ANON_KEY` | **Anon** or **service** key with read access to the relevant tables/views. |
| `PORT` (optional)   | Port for Dash to bind to (default `5000`).                                 |
| `HOST` (optional)   | Host interface (default `0.0.0.0` for Docker/Replit).                      |

Store them in **.env** for local use or the hosting provider’s secret manager.

---

## 5  Data Expectations

### 5.1 Sensors / Metadata

```text
id_site (PK) · site_code · site_name · borough · lat · lon · sensor_type · pollutants_measured[]
```

### 5.2 Annual Averages (`annual_averages`)

| id\_site | pollutant | year | value |
| -------- | --------- | ---- | ----- |

### 5.3 Monthly Data (`map_monthly_data`)

\| id\_site | pollutant | year | month | value | date |

Both views already join the sensor metadata, so the app fetches everything in one call.

---

## 6  Usage Guide

1. **Pick filters** in the sidebar – buttons turn red when active.
2. The **map** updates instantly; click or drag‑lasso sensors to send them to the charts below.
3. Toggle **Borough Boundaries** to shade polygons; colours are light grey, outline black.
4. **Expand Map / Chart** buttons maximise each panel for presentations.
5. In *Chart Tools* you can:

   * Manually choose sensors via dropdown (multi‑select).
   * Narrow the date window.
   * Apply a custom title or reset.
   * Show the **Borough Target** line (NO₂ only) at 30 µg m‑3.
6. Use **Export Data / Export Table** to download CSV slices of the current view.

---

## 7  Styling & Customisation

* All colours, spacing and component classes live in `assets/dashboard.css` – tweak tokens at the top (`:root { --sidebar-width …}`) to apply a new theme.
* Map marker shapes derive from `SYMBOL_MAP` in **main.py**. Add new sensor types there.
* Colour‑scales are defined in `COLOR_SCALES` – edit thresholds or palettes per pollutant and standard.

---

## 8  Development Notes

* Callbacks are grouped by purpose (map, small charts, detailed chart, UI state).
* **Supabase caching:** `supabase_io.clear_active_sensors_cache()` can be called from a Python console when testing fresh data.
* Logging is via `logging` – set `LOG_LEVEL=DEBUG` to see verbose database requests.
* The app auto‑reloads on file changes when run locally; disable with `export DASH_DEBUG=False`.

### Running Unit Tests

(No formal tests yet) – PRs adding **pytest** coverage are welcome 🙂

---

## 9  Troubleshooting

| Symptom                                                             | Likely cause                                   | Fix                                                                           |
| ------------------------------------------------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------- |
| *"Failed to initialize Supabase loader"*                            | Missing or incorrect env vars                  | Check `.env`, regenerate **anon key** if revoked.                             |
| Map shows but **no markers**                                        | Empty `active_sensors` view                    | Verify DB view; `id_site`, `lat`, `lon` must not be NULL.                     |
| KMZ boundaries don’t appear                                         | Files absent or corrupt in `/assets`           | Keep original Google‑Earth KMZ names; ensure they contain a single `doc.kml`. |
| `NotImplementedError: Polygon does not provide __array_interface__` | Mishandling Shapely polys in Pandas (dev work) | Convert to `GeoSeries([...])` before to\_file().                              |

---

## 10  Roadmap

* Live websocket / Supabase channel for near‑real‑time updates
* Additional boroughs & nationwide mode
* User authentication & role‑based filters
* Alert system for exceedances (email / Teams webhook)
* Docker compose with PostGIS for local development

---

## 11  License

Released under the **MIT** License – see `LICENSE` file for full text.

---

### Acknowledgements

* Plotly Dash – interactive Python web apps
* Supabase – open‑source Firebase alternative
* London Borough Councils – public air‑quality data feeds
* Inspiration from the **Love Clean Air** initiative.
