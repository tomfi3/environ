# -*- coding: utf-8 -*-
import dash
from dash import dcc, html, Input, Output, State, callback
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import os
from dash import ctx
from dash.dependencies import ALL
import json

# Import Supabase loader
from supabase_io import get_supabase_loader, initialize_supabase

# Add this after imports, before any callbacks or functions
SYMBOL_MAP = {
    "DT": "square",
    "Clarity": "circle",
    "Automatic": "triangle-up"
}

# Load data from Supabase
def load_data():
    """Load environmental data from Supabase database"""
    try:
        # Initialize Supabase connection
        if not initialize_supabase():
            raise RuntimeError("Failed to initialize Supabase connection")
        
        loader = get_supabase_loader()
        
        # Get all data for the current view (we'll filter in callbacks)
        # For now, load annual data as default
        df = loader.get_annual_data()
        
        if df.empty:
            print("Warning: No data loaded from Supabase")
            return pd.DataFrame()
        
        # Standardize Richmond borough names (keeping existing logic)
        df['borough'] = df['borough'].replace(to_replace=r'(?i)richmond.*', value='Richmond', regex=True)
        
        print(f"Loaded {len(df)} records from Supabase")
        return df
        
    except Exception as e:
        print(f"Error loading data from Supabase: {e}")
        # Return empty DataFrame as fallback
        return pd.DataFrame()

# Borough name mapping for short labels
BOROUGH_LABELS = {
    'Wandsworth': 'Wand',
    'Richmond': 'Rich',
    'Merton': 'Mert'
}

# Load data
df = load_data()

# Get unique values for filters from Supabase
def get_filter_values():
    """Get unique filter values from Supabase"""
    try:
        loader = get_supabase_loader()
        unique_values = loader.get_unique_values()
        
        # Fallback to empty lists if Supabase fails or if years are empty
        if not unique_values['years']:
            print("Warning: No years found in Supabase")
            return [], [], [], [], []
        
        return (
            unique_values['boroughs'],
            unique_values['pollutants'],
            unique_values['sensor_types'],
            unique_values['years'],
            unique_values['months']
        )
    except Exception as e:
        print(f"Error getting filter values from Supabase: {e}")
        return [], [], [], [], []

# Get filter values
boroughs, pollutants, sensor_types, _, months = get_filter_values()

# Force full year range regardless of Supabase response
years = list(range(2000, datetime.now().year + 1))

# Fallbacks for other fields if needed
if not boroughs:
    boroughs = ['Wandsworth', 'Richmond', 'Merton']
if not pollutants:
    pollutants = ['NO2', 'PM2.5', 'PM10']
else:
    if 'PM2.5' not in pollutants:
        pollutants.append('PM2.5')
if not sensor_types:
    sensor_types = ['DT', 'Clarity', 'Automatic']
if not months:
    months = list(range(1, 13))

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "London Environmental Dashboard"
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body { margin: 0; padding: 0; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# App layout
app.layout = html.Div([
    # Sidebar
    html.Div([
        html.H2("Environmental Dashboard", className="header-title"),
        html.P("London Air Quality Monitor", className="header-subtitle"),
        html.Div([
            html.H3("Filters", className="section-title"),
            
            # Borough Filter (Multi-select)
            html.Div([
                html.Label("Borough", style={'fontWeight': '500', 'marginBottom': '8px', 'display': 'block', 'fontSize': '12px'}),
                html.Div([
                    html.Button(
                        BOROUGH_LABELS.get(borough, borough),
                        id={'type': 'borough-btn', 'index': borough},
                        className='filter-button multi-select selected'
                    ) for borough in boroughs
                ], className="filter-button-row")
            ], className="filter-section"),
            
            # Pollutant Filter (Single-select)
            html.Div([
                html.Label("Pollutant", style={'fontWeight': '500', 'marginBottom': '8px', 'display': 'block', 'fontSize': '12px'}),
                html.Div([
                    html.Button(
                        "PM2.5" if pollutant == "PM25" else pollutant,
                        id={'type': 'pollutant-btn', 'index': pollutant},
                        className=f'filter-button single-select{" selected" if pollutant == "NO2" else ""}'
                    ) for pollutant in pollutants
                ], className="filter-button-row")
            ], className="filter-section"),
            
            # Sensor Type Filter (Multi-select)
            html.Div([
                html.Label("Sensor Type", style={'fontWeight': '500', 'marginBottom': '8px', 'display': 'block', 'fontSize': '12px'}),
                html.Div([
                    html.Button(
                        sensor_type,
                        id={'type': 'sensor-btn', 'index': sensor_type},
                        className='filter-button multi-select selected'
                    ) for sensor_type in sensor_types
                ], className="filter-button-row")
            ], className="filter-section"),
            
            # Averaging Period Filter (Single-select)
            html.Div([
                html.Label("Averaging Period", style={'fontWeight': '500', 'marginBottom': '8px', 'display': 'block', 'fontSize': '12px'}),
                html.Div([
                    html.Button(
                        period,
                        id={'type': 'averaging-btn', 'index': period},
                        className=f'filter-button single-select{" selected" if period == "Annual" else ""}'
                    ) for period in ['Annual', 'Month']
                ], className="filter-button-row")
            ], className="filter-section"),
            
            # Year Slider (always visible)
            html.Div([
                html.Label("Year", className="filter-label"),
                dcc.Slider(
                    id='year-slider',
                    min=min(years),
                    max=max(years),
                    step=1,
                    value=2024,
                    marks={
                        year: {
                            'label': str(year) if year in [min(years), min(years) + (max(years) - min(years)) // 3, 
                                                         min(years) + 2 * (max(years) - min(years)) // 3, max(years)] else ''
                        } for year in years
                    },
                    tooltip={"placement": "bottom", "always_visible": True},
                    included=False,
                    className='year-slider'
                )
            ], className="filter-section"),
            
            # Month Slider (only visible when averaging period is 'Month')
            html.Div([
                html.Label("Month", className="filter-label"),
                dcc.Slider(
                    id='month-slider',
                    min=1,
                    max=12,
                    step=1,
                    value=1,
                    marks={
                        month: {
                            'label': datetime(2024, month, 1).strftime('%b')
                        } for month in [1, 4, 7, 10]
                    },
                    tooltip={"placement": "bottom", "always_visible": True},
                    included=False,
                    className='month-slider'
                )
            ], id='month-slider-container', className="filter-section", style={'display': 'none'}),
            
            # Color Scale Filter (Single-select)
            html.Div([
                html.Label("Color Scale", style={'fontWeight': '500', 'marginBottom': '8px', 'display': 'block', 'fontSize': '12px'}),
                html.Div([
                    html.Button(
                        scale_type,
                        id={'type': 'color-scale-btn', 'index': scale_type},
                        className='filter-button single-select selected' if scale_type == 'WHO' else 'filter-button single-select'
                    ) for scale_type in ['WHO', 'Borough', 'UK']
                ], className="filter-button-row")
            ], className="filter-section"),
            
            # Map Style Dropdown
            html.Div([
                html.Label("Map Style", style={'fontWeight': '500', 'marginBottom': '8px', 'display': 'block', 'fontSize': '12px'}),
                dcc.Dropdown(
                    id='map-style-dropdown',
                    options=[
                        {'label': 'OpenStreetMap', 'value': 'open-street-map'},
                        {'label': 'Carto Voyager', 'value': 'carto-voyager'},
                        {'label': 'Carto Positron', 'value': 'carto-positron'},
                        {'label': 'Stamen Terrain', 'value': 'stamen-terrain'},
                    ],
                    value='carto-voyager',
                    clearable=False,
                    style={'marginBottom': '10px', 'fontSize': '13px'}
                )
            ], className="filter-section"),
            
            # Export Button
            html.Button("Export Data", id="export-button", className="export-button")
        ])
    ], className="sidebar"),
    
    # Store components for selected values
    dcc.Store(id='selected-boroughs', data=boroughs),
    dcc.Store(id='selected-pollutant', data='NO2'),
    dcc.Store(id='selected-sensor-types', data=sensor_types),  # For map view filter
    dcc.Store(id='selected-averaging', data='Annual'),
    dcc.Store(id='selected-year', data=2024),
    dcc.Store(id='selected-month', data=1),
    dcc.Store(id='selected-color-scale', data='WHO'),
    dcc.Store(id='selected-map-style', data='carto-voyager'),
    dcc.Store(id='map-view-store', data={'center': {'lat': 51.445, 'lon': -0.22}, 'zoom': 11.3}),
    dcc.Store(id='map-expanded', data=False),
    dcc.Store(id='chart-expanded', data=False),
    dcc.Store(id='legend-mode-store', data=0),
    dcc.Store(id='custom-title-store', data=None),
    
    # Main Content
    html.Div([
        # Header Banner
        html.Div([
            html.H1("London Environmental Monitoring Dashboard", className="header-title"),
            html.P("Real-time air quality data across London boroughs", className="header-subtitle")
        ], className="header"),
        # TOP AREA: Map + 2 Small Charts
        html.Div([
            # Map Card
            html.Div(
                id='map-card',
                className='card map-compact',
                children=[
                    html.Div([
                        html.H3("Air Quality Map", className="card-title"),
                        html.Button(
                            "Expand Map", id="expand-map-btn", className="expand-button"
                        )
                    ], className="card-header"),
                    html.Div(
                        id='map-container',
                        style={'height': '100%', 'width': '100%'},
                        children=[
                            dcc.Graph(
                                id='map-graph',
                                style={'height': '100%', 'width': '100%'}
                            )
                        ]
                    )
                ]
            ),
            # 2 Small Charts
            html.Div([
                html.Div([
                    html.H3("Time Series", className="card-title"),
                    dcc.Graph(id='time-series-graph', style={'height': '170px', 'width': '100%'})
                ], className="card"),
                html.Div([
                    html.H3("Pollutant Comparison", className="card-title"),
                    dcc.Graph(id='bar-graph', style={'height': '170px', 'width': '100%'})
                ], className="card")
            ], className="charts-stack", id='small-charts-stack')
        ], id='top-area-grid', className="top-grid-compact"),
        # DETAILED SECTION: Detailed Chart + Tools
        html.Div([
            # Detailed Chart
            html.Div([
                html.Div([
                    html.H3("Detailed Analysis", className="card-title"),
                    html.Div([
                        html.Button('Toggle Legend', id='toggle-legend-btn', className='expand-button'),
                        html.Button("Expand Chart", id="expand-chart-btn", className="expand-button")
                    ], style={'display': 'flex', 'gap': '8px', 'marginLeft': 'auto'})
                ], className="card-header"),
                html.Div(
                    id='detailed-chart-container',
                    style={'height': '100%', 'width': '100%'},
                    children=[
                        dcc.Graph(
                            id='detailed-chart',
                            style={'height': '100%', 'width': '100%'},
                            config={'responsive': True}
                        )
                    ]
                )
            ], className="card detailed-compact", id='detailed-chart-card'),
            # Tools
            html.Div([
                html.Div([
                    html.H3("Chart Tools", className="card-title"),
                    html.Div([
                        html.Label("Select Sensors to Show in Charts", style={'fontWeight': '500', 'marginBottom': '4px', 'display': 'block', 'fontSize': '12px'}),
                        dcc.Dropdown(
                            id='chart-sensors-dropdown',
                            options=[],  # Will be populated by callback
                            multi=True,
                            placeholder="Select sensors...",
                            className="dropdown-style"
                        ),
                        html.Button("Clear Selection", id="clear-selection-button", className="export-button"),
                        html.Button("Clear Map Selection", id="clear-map-selection-button", className="export-button")
                    ], style={'marginBottom': '12px'}),
                    html.Div([
                        html.Label("Chart Start Date", style={'fontWeight': '500', 'marginBottom': '4px', 'display': 'block', 'fontSize': '12px'}),
                        dcc.DatePickerSingle(
                            id='chart-start-date',
                            date=None,  # Will be set by callback
                            className="dropdown-style"
                        )
                    ], style={'marginBottom': '12px'}),
                    html.Div([
                        html.Label("Chart End Date", style={'fontWeight': '500', 'marginBottom': '4px', 'display': 'block', 'fontSize': '12px'}),
                        dcc.DatePickerSingle(
                            id='chart-end-date',
                            date=None,  # Will be set by callback
                            className="dropdown-style"
                        )
                    ], style={'marginBottom': '12px'}),
                    html.Button("Update Chart", id="update-chart-button", className="export-button"),
                    # --- Custom Chart Title Tool ---
                    html.Div([
                        html.Label("Custom Chart Title", style={'fontWeight': '500', 'marginBottom': '4px', 'display': 'block', 'fontSize': '12px'}),
                        dcc.Input(id='custom-title-input', type='text', placeholder='Enter custom title...', className='dropdown-style', style={'width': '70%', 'marginRight': '8px'}),
                        html.Button('Apply Title', id='apply-title-btn', className='export-button', n_clicks=0, style={'marginRight': '8px'}),
                        html.Button('Reset Title', id='reset-title-btn', className='export-button', n_clicks=0)
                    ], style={'marginTop': '16px', 'marginBottom': '8px'}),
                ], className="card"),
                html.Div([
                    html.H3("Table Tools", className="card-title"),
                    html.Div([
                        html.Label("Show Data Table", style={'fontWeight': '500', 'marginBottom': '4px', 'display': 'block', 'fontSize': '12px'}),
                        dcc.Checklist(
                            id='show-table-toggle',
                            options=[{'label': 'Display Data Table', 'value': 'show'}],
                            value=[],
                            style={'marginBottom': '12px'}
                        ),
                        html.Button("Export Table", id="export-table-button", className="export-button")
                    ])
                ], className="card")
            ], id='tools-container', className="tools-stack")
        ], id='detailed-section', className="detailed-section-compact")
    ], className="main-content")
], className="main-container")

# Callbacks
@callback(
    Output('map-view-store', 'data'),
    Input('map-graph', 'relayoutData'),
    State('map-view-store', 'data'),
    prevent_initial_call=True
)
def update_map_view(relayoutData, current_view):
    print(f"[DEBUG] update_map_view called with relayoutData: {relayoutData}")
    if not relayoutData:
        return current_view
    new_center = current_view['center']
    new_zoom = current_view['zoom']
    if 'map.center' in relayoutData:
        new_center = relayoutData['map.center']
    if 'map.zoom' in relayoutData:
        new_zoom = relayoutData['map.zoom']
    print(f"[DEBUG] Updated zoom from {current_view['zoom']} to {new_zoom}")
    return {'center': new_center, 'zoom': new_zoom}

@callback(
    Output('selected-map-style', 'data'),
    Input('map-style-dropdown', 'value'),
    prevent_initial_call=False
)
def update_selected_map_style(style):
    return style

@callback(
    Output('map-graph', 'figure'),
    [Input('map-graph', 'relayoutData'),
     Input('selected-boroughs', 'data'),
     Input('selected-pollutant', 'data'),
     Input('selected-sensor-types', 'data'),
     Input('selected-averaging', 'data'),
     Input('selected-year', 'data'),
     Input('selected-month', 'data'),
     Input('selected-color-scale', 'data'),
     Input('selected-map-style', 'data')],
    [State('map-view-store', 'data')],
    prevent_initial_call=False
)
def update_map(relayout, selected_boroughs, selected_pollutant, selected_sensor_types, selected_averaging, selected_year, selected_month, selected_color_scale, selected_map_style, map_view_store):
    print("\n================ MAP CALLBACK DEBUG ================")
    print(f"[DEBUG] Map callback inputs:")
    print(f"  - selected_boroughs: {selected_boroughs} (type: {type(selected_boroughs)})")
    print(f"  - selected_pollutant: {selected_pollutant} (type: {type(selected_pollutant)})")
    print(f"  - selected_sensor_types: {selected_sensor_types} (type: {type(selected_sensor_types)})")
    print(f"  - selected_averaging: {selected_averaging} (type: {type(selected_averaging)})")
    print(f"  - selected_year: {selected_year} (type: {type(selected_year)})")
    print(f"  - selected_month: {selected_month} (type: {type(selected_month)})")
    print(f"  - selected_color_scale: {selected_color_scale} (type: {type(selected_color_scale)})")
    print(f"  - selected_map_style: {selected_map_style} (type: {type(selected_map_style)})")
    print(f"[DEBUG] Map callback states:")
    print(f"  - map_view_store: {map_view_store}")
    print(f"  - relayout: {relayout}")
    
    # Use map_view_store for zoom/center unless relayoutData provides new values
    zoom = map_view_store.get('zoom', 11.3) if map_view_store else 11.3
    center = map_view_store.get('center', {'lat': 51.445, 'lon': -0.22}) if map_view_store else {'lat': 51.445, 'lon': -0.22}
    if relayout:
        if 'map.zoom' in relayout:
            zoom = relayout['map.zoom']
        if 'map.center' in relayout:
            center = relayout['map.center']
    print(f"[DEBUG] Current zoom: {zoom}, center: {center}")
    
    try:
        loader = get_supabase_loader()
        active_sensors = loader.get_active_sensors()
        print(f"[DEBUG] Loaded {len(active_sensors)} active sensors from Supabase")
        if not active_sensors.empty:
            print(f"[DEBUG] Active sensors sample:\n{active_sensors.head(3)}")
        else:
            print("[DEBUG] No active sensors found")
            return go.Figure()
        
        all_sensors = active_sensors[
            active_sensors['borough'].isin(selected_boroughs) & 
            active_sensors['sensor_type'].isin(selected_sensor_types)
        ]
        print(f"[DEBUG] Filtered sensors by borough/type: {len(all_sensors)}")
        if not all_sensors.empty:
            print(f"[DEBUG] Filtered sensors sample:\n{all_sensors.head(3)}")
        else:
            print("[DEBUG] No sensors match the current filters")
            return go.Figure()
        
        db_pollutant = "PM25" if selected_pollutant == "PM2.5" else selected_pollutant
        print(f"[DEBUG] Mapped pollutant '{selected_pollutant}' to DB value '{db_pollutant}'")
        if selected_year is not None:
            selected_year = int(selected_year)
            print(f"[DEBUG] Converted selected_year to int: {selected_year}")
        
        print(f"[DEBUG] Calling get_combined_data with:")
        print(f"  - averaging_period: {selected_averaging}")
        print(f"  - id_sites: {all_sensors['id_site'].tolist()[:5]} ... total {len(all_sensors)}")
        print(f"  - pollutants: {[db_pollutant]}")
        print(f"  - years: {[selected_year] if selected_year is not None else None}")
        print(f"  - months: {[selected_month] if selected_averaging == 'Month' else None}")
        
        filtered_df = loader.get_combined_data(
            averaging_period=selected_averaging,
            id_sites=all_sensors['id_site'].tolist(),
            pollutants=[db_pollutant],
            years=[selected_year] if selected_year is not None else None,
            months=[selected_month] if selected_averaging == 'Month' else None
        )
        print(f"[DEBUG] Returned {len(filtered_df)} rows from get_combined_data")
        if not filtered_df.empty:
            print(f"[DEBUG] filtered_df columns: {filtered_df.columns.tolist()}")
            print(f"[DEBUG] filtered_df sample:\n{filtered_df.head(3)}")
            print(f"[DEBUG] filtered_df id_site unique: {filtered_df['id_site'].unique()[:5]}")
            print(f"[DEBUG] filtered_df years: {filtered_df['year'].unique() if 'year' in filtered_df.columns else 'N/A'}")
            print(f"[DEBUG] filtered_df pollutants: {filtered_df['pollutant'].unique() if 'pollutant' in filtered_df.columns else 'N/A'}")
        else:
            print(f"[DEBUG] No data returned - checking what's available in the database...")
            try:
                sample_data = loader.get_annual_data()
                if not sample_data.empty:
                    print(f"[DEBUG] Sample annual data available:")
                    print(f"  - Pollutants: {sample_data['pollutant'].unique()}")
                    print(f"  - Years: {sorted(sample_data['year'].unique())}")
                    print(f"  - Sample rows: {len(sample_data)}")
                    print(sample_data[['id_site', 'pollutant', 'year', 'value']].head())
                else:
                    print(f"[DEBUG] No annual data available at all")
            except Exception as e:
                print(f"[DEBUG] Error checking sample data: {e}")
        
        # Always show all filtered sensors
        sensor_value_map = dict(zip(filtered_df['id_site'], filtered_df['value'])) if not filtered_df.empty else {}
        # Only keep sensors that have data for the current filter selection
        sensors_with_data = all_sensors[all_sensors['id_site'].isin(sensor_value_map.keys())].copy() if sensor_value_map else pd.DataFrame(columns=all_sensors.columns)
        print(f"[DEBUG] sensors_with_data: {len(sensors_with_data)} (with data for current filters)")
        if not sensors_with_data.empty:
            print(f"[DEBUG] sensors_with_data sample:\n{sensors_with_data.head(3)}")

        marker_size = marker_size_for_zoom(zoom)
        print(f"[DEBUG] Map zoom: {zoom}, marker_size: {marker_size}")
        print(f"[DEBUG] Sensors with data: {len(sensors_with_data)} (with data for current filters)")
        print("================ END MAP CALLBACK DEBUG ================\n")

        fig = go.Figure()
        if not sensors_with_data.empty:
            # Assign marker colors: color by value
            marker_colors = [get_color_for_value(sensor_value_map[row['id_site']], selected_pollutant, selected_color_scale) for _, row in sensors_with_data.iterrows()]
            fig.add_trace(go.Scattermap(
                lat=sensors_with_data['lat'],
                lon=sensors_with_data['lon'],
                mode='markers+text',
                marker=dict(
                    size=marker_size,
                    color=marker_colors,
                    opacity=0.95,
                    allowoverlap=True
                ),
                text=sensors_with_data['site_code'],  # Use site_code for display
                textposition='top center',
                name=f"Sensors (all)",
                customdata=sensors_with_data.apply(
                    lambda row: [
                        row['site_code'],  # site_code for hover display
                        row['borough'],
                        row['sensor_type'],
                        sensor_value_map.get(row['id_site'], float('nan'))  # Still keyed by id_site
                    ],
                    axis=1
                ).tolist(),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>" +  # site_code
                    "Borough: %{customdata[1]}<br>" +
                    "Type: %{customdata[2]}<br>" +
                    "Value: %{customdata[3]:.1f} μg/m³<extra></extra>"
                )
            ))
        else:
            # Add a single invisible dummy marker at the map center
            fig.add_trace(go.Scattermap(
                lat=[center['lat']],
                lon=[center['lon']],
                mode='markers',
                marker=dict(size=1, color='rgba(0,0,0,0)', opacity=0),
                text=[''],
                hoverinfo='skip',
                showlegend=False
            ))

        # Add color scale legend only
        color_scale_info = get_color_scale_info(selected_pollutant, selected_color_scale)
        legend_shapes = []
        legend_annotations = []
        legend_y = 0.12
        legend_x = 0.01
        legend_height = 0.025

        for i, (min_val, max_val, label, color) in enumerate(color_scale_info):
            legend_shapes.append(dict(
                type="rect",
                xref="paper", yref="paper",
                x0=legend_x, x1=legend_x + 0.04,
                y0=legend_y + i * legend_height, y1=legend_y + (i + 1) * legend_height,
                fillcolor=color, line=dict(width=0)
            ))
            legend_annotations.append(dict(
                x=legend_x + 0.045, y=legend_y + i * legend_height + legend_height / 2,
                xref="paper", yref="paper",
                text=f"{label} ({min_val:g}-{max_val if max_val != float('inf') else '∞'})",
                showarrow=False, xanchor="left", yanchor="middle",
                font=dict(size=12)
            ))

        # Update layout with only the color scale legend
        fig.update_layout(
            uirevision=f"mapview_{zoom}_{center['lat']}_{center['lon']}",  # Stable uirevision
            map=dict(
                style=selected_map_style,
                center=center,
                zoom=zoom,
                domain=dict(x=[0, 1], y=[0, 1])
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
            shapes=legend_shapes,
            annotations=legend_annotations
        )
        
        return fig
        
    except Exception as e:
        print(f"[ERROR] Error in map callback: {e}")
        # Return empty figure on error
        return go.Figure()

@callback(
    Output('detailed-chart', 'figure'),
    [Input('chart-sensors-dropdown', 'value'),
     Input('selected-pollutant', 'data'),
     Input('selected-averaging', 'data'),
     Input('chart-start-date', 'date'),
     Input('chart-end-date', 'date'),
     Input('update-chart-button', 'n_clicks'),
     Input('chart-expanded', 'data'),
     Input('legend-mode-store', 'data'),
     Input('custom-title-store', 'data')],
    prevent_initial_call=False
)
def update_detailed_chart(dropdown_sensors, selected_pollutant, selected_averaging, chart_start_date, chart_end_date, n_clicks, chart_expanded, legend_mode, custom_title):
    ref_lines = []  # Always define this at the top
    all_sensors = dropdown_sensors or []
    all_sensors = list(set(all_sensors))  # Ensure no duplicates
    print(f"[DEBUG] update_detailed_chart: all_sensors={all_sensors}")
    print(f"[DEBUG] selected_averaging={selected_averaging}")
    print(f"[DEBUG] chart_expanded={chart_expanded}")
    if not all_sensors:
        fig = go.Figure()
        fig.add_annotation(
            text="No sensors selected. Click on sensors in the map or use the dropdown to select sensors.",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="gray")
        )
        fig.update_layout(
            title=dict(text="Detailed Chart", font=dict(color='black', size=14), x=0.5, xanchor='center'),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig
    
    # Filter by averaging_period (Annual or Month), pollutant, and selected sensors
    try:
        loader = get_supabase_loader()
        chart_data = loader.get_combined_data(
            averaging_period=selected_averaging,
            id_sites=all_sensors,
            pollutants=[selected_pollutant]
        )
        # Build id_site to site_code and site_name mapping
        active_sensors = loader.get_active_sensors()
        id_to_code = dict(zip(active_sensors["id_site"], active_sensors["site_code"]))
        id_to_name = dict(zip(active_sensors["id_site"], active_sensors["site_name"]))
        
        if chart_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No data found for selected sensors and filters.",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            fig.update_layout(
                title=dict(text="Detailed Chart", font=dict(color='black', size=14), x=0.5, xanchor='center'),
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig
        
        # Create time series chart
        fig = go.Figure()
        
        for sensor in all_sensors:
            sensor_data = chart_data[chart_data['id_site'] == sensor]
            if len(sensor_data) > 0:
                # Create date column for x-axis
                if selected_averaging == 'Month':
                    sensor_data['date'] = pd.to_datetime(dict(year=sensor_data['year'], month=sensor_data['month'], day=1))
                else:  # Annual
                    sensor_data['date'] = pd.to_datetime(sensor_data['year'], format='%Y')
                sensor_data = sensor_data.sort_values('date')
                # Legend label logic per legend_mode
                site_code = id_to_code.get(sensor, sensor)
                site_name = id_to_name.get(sensor, '')
                if legend_mode in [0, 1]:
                    trace_name = site_code
                elif legend_mode in [2, 3]:
                    trace_name = f"{site_code}: {site_name}" if site_name else site_code
                else:  # legend_mode == 4
                    trace_name = ''
                fig.add_trace(go.Scatter(
                    x=sensor_data['date'],
                    y=sensor_data['value'],
                    mode='lines+markers',
                    name=trace_name,
                    line=dict(width=2),
                    marker=dict(size=4),
                    showlegend=(legend_mode != 4)
                ))
        
        # Add reference lines for WHO and UK limits if pollutant is NO2, PM2.5, or PM10
        ref_lines = []
        ref_annotations = []
        min_ymax = 1.05 * max(sensor_data['value'].max() for sensor_data in [chart_data[chart_data['id_site'] == sensor] for sensor in all_sensors])
        if selected_pollutant == "NO2":
            min_ymax = max(min_ymax, 50)
        elif selected_pollutant in ["PM2.5", "PM10"]:
            min_ymax = max(min_ymax, 30)
        
        if selected_pollutant in ["NO2", "PM2.5", "PM10"]:
            who_limits = {"NO2": 10, "PM2.5": 5, "PM10": 15}
            uk_limits = {"NO2": 40, "PM2.5": 20, "PM10": 40}
            if selected_pollutant in who_limits:
                ref_lines.append(dict(type='line', y0=who_limits[selected_pollutant], y1=who_limits[selected_pollutant], xref='paper', x0=0, x1=1, line=dict(color='green', width=2, dash='dot')))
                ref_annotations.append(dict(
                    x=0.01, y=who_limits[selected_pollutant]+2 if selected_pollutant=="NO2" else who_limits[selected_pollutant]+1,
                    xref='paper', yref='y',
                    text='WHO Guideline',
                    showarrow=False, xanchor='left', yanchor='bottom',
                    font=dict(size=11, color='green'),
                    align='left',
                    bgcolor='rgba(255,255,255,0.7)',
                    borderpad=2,
                    bordercolor='green',
                    borderwidth=0
                ))
            if selected_pollutant in uk_limits:
                ref_lines.append(dict(type='line', y0=uk_limits[selected_pollutant], y1=uk_limits[selected_pollutant], xref='paper', x0=0, x1=1, line=dict(color='red', width=2, dash='dot')))
                ref_annotations.append(dict(
                    x=0.01, y=uk_limits[selected_pollutant]+2 if selected_pollutant=="NO2" else uk_limits[selected_pollutant]+1,
                    xref='paper', yref='y',
                    text='UK Limit',
                    showarrow=False, xanchor='left', yanchor='bottom',
                    font=dict(size=11, color='red'),
                    align='left',
                    bgcolor='rgba(255,255,255,0.7)',
                    borderpad=2,
                    bordercolor='red',
                    borderwidth=0
                ))
        
        # Create chart title based on averaging period and pollutant
        if custom_title:
            chart_title = custom_title
        elif selected_averaging == 'Annual':
            chart_title = f"Chart of Annual Average {selected_pollutant}"
        else:
            chart_title = f"Chart of Monthly Average {selected_pollutant}"
        
        # Legend layout logic per legend_mode
        showlegend = legend_mode != 4
        bottom_margin = 40  # default
        if legend_mode == 0:
            legend_config = dict(
                orientation='v',
                yanchor='top',
                y=1,
                xanchor='right',
                x=1,
                font=dict(family='monospace', size=12),
                bgcolor='rgba(255,255,255,0.9)'
            )
        elif legend_mode == 1:
            legend_config = dict(
                orientation='v',
                yanchor='top',
                y=1,
                xanchor='left',
                x=1.02,
                font=dict(family='monospace', size=12),
                bgcolor='rgba(255,255,255,0.9)'
            )
        elif legend_mode == 2:
            legend_config = dict(
                orientation='v',
                yanchor='top',
                y=1,
                xanchor='left',
                x=1.02,
                font=dict(family='monospace', size=12),
                bgcolor='rgba(255,255,255,0.9)'
            )
        elif legend_mode == 3:
            legend_config = dict(
                orientation='h',
                yanchor='top',
                y=-0.25,
                xanchor='center',
                x=0.5,
                font=dict(family='monospace', size=12),
                bgcolor='rgba(255,255,255,0.9)'
            )
            bottom_margin = 120
        else:
            legend_config = dict(font=dict(family='monospace', size=12))
        fig.update_layout(
            title=dict(text=chart_title, font=dict(color='black', size=14), x=0.5, xanchor='center'),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=40, r=40, t=40, b=bottom_margin),
            xaxis=dict(
                showline=True,
                linewidth=2,
                linecolor='black',
                mirror=True,
                gridcolor='#e0e0e0',
                zeroline=True,
                zerolinecolor='black',
                title="Year"
            ),
            yaxis=dict(
                showline=True,
                linewidth=2,
                linecolor='black',
                mirror=True,
                gridcolor='#e0e0e0',
                zeroline=True,
                zerolinecolor='black',
                range=[0, min_ymax],
                title=f"{selected_pollutant} Concentration (μg/m³)"
            ),
            legend=legend_config,
            showlegend=showlegend,
            shapes=ref_lines,
            annotations=ref_annotations
        )
        
        return fig
        
    except Exception as e:
        print(f"[ERROR] Error loading chart data from Supabase: {e}")
        fig = go.Figure()
        fig.add_annotation(
            text="Error loading data from database",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="red")
        )
        fig.update_layout(
            title=dict(text="Detailed Chart", font=dict(color='black', size=14), x=0.5, xanchor='center'),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(
                showline=True,
                linewidth=2,
                linecolor='black',
                mirror=True,
                gridcolor='#e0e0e0',
                zeroline=True,
                zerolinecolor='black',
                title="Year"
            ),
            yaxis=dict(
                showline=True,
                linewidth=2,
                linecolor='black',
                mirror=True,
                gridcolor='#e0e0e0',
                zeroline=True,
                zerolinecolor='black',
                range=[0, 1],
                title=f"{selected_pollutant} Concentration (μg/m³)"
            ),
        )
        return fig

# Callbacks for filter button interactions
@callback(
    [Output('selected-boroughs', 'data'),
     Output({'type': 'borough-btn', 'index': ALL}, 'className')],
    [Input({'type': 'borough-btn', 'index': ALL}, 'n_clicks')],
    [State('selected-boroughs', 'data')],
    prevent_initial_call=True
)
def update_borough_selection(n_clicks, current_selection):
    if not n_clicks or not any(n_clicks):
        return current_selection, [
            f"filter-button multi-select {'selected' if borough in current_selection else ''}"
            for borough in boroughs
        ]
    clicked_idx = max((i for i, v in enumerate(n_clicks) if v), key=lambda i: n_clicks[i])
    clicked_borough = boroughs[clicked_idx]
    if clicked_borough in current_selection:
        new_selection = [b for b in current_selection if b != clicked_borough]
    else:
        new_selection = current_selection + [clicked_borough]
    button_classes = [
        f"filter-button multi-select {'selected' if borough in new_selection else ''}"
        for borough in boroughs
    ]
    return new_selection, button_classes

@callback(
    [Output('selected-pollutant', 'data'),
     Output({'type': 'pollutant-btn', 'index': ALL}, 'className')],
    [Input({'type': 'pollutant-btn', 'index': ALL}, 'n_clicks')],
    prevent_initial_call=False
)
def update_pollutant_selection(_):
    trig = dash.callback_context.triggered_id
    if trig is None:
        selected_pollutant = 'NO2'
    else:
        selected_pollutant = trig["index"]
    button_classes = [
        f"filter-button single-select {'selected' if pollutant == selected_pollutant else ''}"
        for pollutant in pollutants
    ]
    return selected_pollutant, button_classes

# Callback for sensor type filter (map view filter)
@callback(
    [Output('selected-sensor-types', 'data'),
     Output({'type': 'sensor-btn', 'index': ALL}, 'className')],
    [Input({'type': 'sensor-btn', 'index': ALL}, 'n_clicks')],
    [State('selected-sensor-types', 'data')],
    prevent_initial_call=False
)
def update_sensor_type_selection(_, current_selection):
    trig = dash.callback_context.triggered_id
    if trig is None:
        current_selection = sensor_types
        return (
            current_selection,
            [f"filter-button multi-select selected" for _ in sensor_types]
        )
    clicked_sensor = trig["index"]
    current_selection = current_selection or sensor_types
    if clicked_sensor in current_selection:
        new_selection = [s for s in current_selection if s != clicked_sensor]
    else:
        new_selection = current_selection + [clicked_sensor]
    button_classes = [
        f"filter-button multi-select {'selected' if s in new_selection else ''}"
        for s in sensor_types
    ]
    return new_selection, button_classes

@callback(
    [Output('selected-averaging', 'data'),
     Output({'type': 'averaging-btn', 'index': ALL}, 'className')],
    [Input({'type': 'averaging-btn', 'index': ALL}, 'n_clicks')],
    prevent_initial_call=False
)
def update_averaging_selection(_):
    periods = ['Annual', 'Month']
    trig = dash.callback_context.triggered_id
    if trig is None:
        selected_period = 'Annual'
    else:
        selected_period = trig["index"]
    button_classes = [
        f"filter-button single-select {'selected' if period == selected_period else ''}"
        for period in periods
    ]
    return selected_period, button_classes

@callback(
    [Output('selected-color-scale', 'data'),
     Output({'type': 'color-scale-btn', 'index': ALL}, 'className')],
    [Input({'type': 'color-scale-btn', 'index': ALL}, 'n_clicks')]
)
def update_color_scale_selection(_):
    scales = ['WHO', 'Borough', 'UK']
    trig = dash.callback_context.triggered_id
    if trig is None:
        selected_scale = 'WHO'
    else:
        selected_scale = trig["index"]
    button_classes = [
        f"filter-button single-select {'selected' if scale == selected_scale else ''}"
        for scale in scales
    ]
    return selected_scale, button_classes

# Month slider visibility callback
@callback(
    Output('month-slider-container', 'style'),
    [Input('selected-averaging', 'data')]
)
def toggle_month_slider(averaging_period):
    if averaging_period == 'Month':
        return {'display': 'block'}
    else:
        return {'display': 'none'}

# Update year and month stores
@callback(
    Output('selected-year', 'data'),
    [Input('year-slider', 'value')]
)
def update_selected_year(year):
    return year

@callback(
    Output('selected-month', 'data'),
    [Input('month-slider', 'value')]
)
def update_selected_month(month):
    return month

# Color scale definitions for different pollutants and standards
COLOR_SCALES = {
    'NO2': {
        'WHO': {
            'name': 'WHO Guidelines',
            'ranges': [
                (0, 10, 'WHO compliant', '#ccffff'),      # grey - WHO guideline
                (10, 20, 'Good', '#33ccff'),          # blue
                (20, 30, 'Moderate', '#00ffcc'),      # turq
                (30, 40, 'UK Limit compliant', '#00ff00'),          # green
                (40, 60, 'Poor', '#ffa500'),          # orange
                (60, 100, 'Very Poor', '#ff0000'),          # red
                (100, float('inf'), 'Extremly Poor', '#660033')  # purplet
            ]
        },
        'Borough': {
            'name': 'Borough Standards',
            'ranges': [
                (0, 10, 'Excellent', '#ccffff'),      # grey
                (10, 30, 'Good', '#33ccff'),          # blue
                (30, 40, 'Moderate', '#00ff00'),      # green
                (40, 60, 'Poor', '#ffa500'),          # orange
                (60, float('inf'), 'Very Poor', '#ff0000')  # Red
            ]
        },
        'UK': {
            'name': 'UK Legal Limits',
            'ranges': [
                (0, 40, 'Moderate', '#00ff00'),      # green
                (40, 60, 'Poor', '#ffa500'),          # Orange
                (60, float('inf'), 'Very Poor', '#ff0000')  # Red - UK legal limit
            ]
        }
    },
    'PM2.5': {
        'WHO': {
            'name': 'WHO Guidelines',
            'ranges': [
                (0, 5, 'Excellent', '#00ff00'),       # Green - WHO guideline
                (5, 10, 'Good', '#ffff00'),           # Yellow
                (10, 15, 'Moderate', '#ffa500'),      # Orange
                (15, 20, 'Poor', '#ff6600'),          # Dark Orange
                (20, float('inf'), 'Very Poor', '#ff0000')  # Red - UK legal limit
            ]
        },
        'Borough': {
            'name': 'Borough Standards',
            'ranges': [
                (0, 8, 'Excellent', '#00ff00'),       # Green
                (8, 12, 'Good', '#ffff00'),           # Yellow
                (12, 16, 'Moderate', '#ffa500'),      # Orange
                (16, 20, 'Poor', '#ff6600'),          # Dark Orange
                (20, float('inf'), 'Very Poor', '#ff0000')  # Red
            ]
        },
        'UK': {
            'name': 'UK Legal Limits',
            'ranges': [
                (0, 10, 'Excellent', '#00ff00'),      # Green
                (10, 15, 'Good', '#ffff00'),          # Yellow
                (15, 20, 'Moderate', '#ffa500'),      # Orange
                (20, 25, 'Poor', '#ff6600'),          # Dark Orange
                (25, float('inf'), 'Very Poor', '#ff0000')  # Red - UK legal limit
            ]
        }
    },
    'PM10': {
        'WHO': {
            'name': 'WHO Guidelines',
            'ranges': [
                (0, 15, 'Excellent', '#00ff00'),      # Green - WHO guideline
                (15, 25, 'Good', '#ffff00'),          # Yellow
                (25, 35, 'Moderate', '#ffa500'),      # Orange
                (35, 45, 'Poor', '#ff6600'),          # Dark Orange
                (45, float('inf'), 'Very Poor', '#ff0000')  # Red - UK legal limit
            ]
        },
        'Borough': {
            'name': 'Borough Standards',
            'ranges': [
                (0, 20, 'Excellent', '#00ff00'),      # Green
                (20, 30, 'Good', '#ffff00'),          # Yellow
                (30, 40, 'Moderate', '#ffa500'),      # Orange
                (40, 50, 'Poor', '#ff6600'),          # Dark Orange
                (50, float('inf'), 'Very Poor', '#ff0000')  # Red
            ]
        },
        'UK': {
            'name': 'UK Legal Limits',
            'ranges': [
                (0, 25, 'Excellent', '#00ff00'),      # Green
                (25, 35, 'Good', '#ffff00'),          # Yellow
                (35, 45, 'Moderate', '#ffa500'),      # Orange
                (45, 50, 'Poor', '#ff6600'),          # Dark Orange
                (50, float('inf'), 'Very Poor', '#ff0000')  # Red - UK legal limit
            ]
        }
    }
}

def get_color_for_value(value, pollutant, scale_type):
    """Get color for a value based on pollutant and scale type"""
    if pollutant not in COLOR_SCALES or scale_type not in COLOR_SCALES[pollutant]:
        return '#cccccc'  # Default gray
    
    ranges = COLOR_SCALES[pollutant][scale_type]['ranges']
    for min_val, max_val, label, color in ranges:
        if min_val <= value < max_val:
            return color
    
    return '#cccccc'  # Default gray if no range matches

def get_color_scale_info(pollutant, scale_type):
    """Get color scale information for legend display"""
    return COLOR_SCALES[pollutant][scale_type]['ranges']

# Callback for individual sensor selection (map interactions)
@callback(
    Output('chart-sensors-dropdown', 'value'),
    [Input('map-graph', 'clickData'),
     Input('map-graph', 'selectedData')],
    prevent_initial_call=True
)
def update_individual_sensor_selection(click_data, selected_data):
    """Update dropdown selection based on map interactions"""
    ctx = dash.callback_context
    print(f"[DEBUG] update_individual_sensor_selection called:")
    print(f"  - click_data: {click_data}")
    print(f"  - selected_data: {selected_data}")
    
    trigger_id = ctx.triggered[0]['prop_id'] if ctx.triggered else ''
    
    # Get mapping from site_code to id_site for conversion
    try:
        loader = get_supabase_loader()
        active_sensors = loader.get_active_sensors()
        sitecode_to_id_map = {row['site_code']: row['id_site'] for _, row in active_sensors.iterrows()}
    except Exception as e:
        print(f"[ERROR] Error getting site_code mapping: {e}")
        return []
    
    if 'clickData' in trigger_id:
        if click_data:
            # Single click on a sensor - clear and select only this sensor
            point = click_data['points'][0]
            site_code = point['text']  # site_code is in the text field
            sensor_id = sitecode_to_id_map.get(site_code, site_code)  # Convert to id_site
            new_selection = [sensor_id]
            print(f"[DEBUG] Single click on sensor: {site_code} -> {sensor_id}, new selection: {new_selection}")
            return new_selection
        else:
            # Click on empty map - clear selection
            print(f"[DEBUG] Click on empty map, clearing selection")
            return []
    
    elif 'selectedData' in trigger_id:
        if selected_data:
            # Lasso/box selection - clear and select only lassoed sensors
            selected_points = selected_data['points']
            selected_site_codes = [point['text'] for point in selected_points]
            selected_sensors = [sitecode_to_id_map.get(code, code) for code in selected_site_codes]
            print(f"[DEBUG] Lasso selection: {selected_site_codes} -> {selected_sensors}")
            return selected_sensors
        else:
            # Lasso on empty area - clear selection
            print(f"[DEBUG] Lasso on empty area, clearing selection")
            return []
    
    # No valid trigger - return no update
    return dash.no_update

# Callback for time series chart (small chart)
@callback(
    Output('time-series-graph', 'figure'),
    [Input('chart-sensors-dropdown', 'value'),
     Input('selected-pollutant', 'data'),
     Input('selected-averaging', 'data')],
    prevent_initial_call=False
)
def update_time_series_chart(dropdown_sensors, selected_pollutant, selected_averaging):
    ref_lines = []  # Always define this at the top
    all_sensors = dropdown_sensors or []
    all_sensors = list(set(all_sensors))  # Ensure no duplicates
    print(f"[DEBUG] Time series chart - selected sensors: {all_sensors}")
    if not all_sensors:
        fig = go.Figure()
        fig.add_annotation(
            text="No sensors selected. Click on sensors in the map or use the dropdown to select sensors.",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="gray")
        )
        fig.update_layout(
            title=dict(text="Time Series Chart", font=dict(color='black', size=14), x=0.5, xanchor='center'),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig
    # Filter data for selected sensors
    try:
        loader = get_supabase_loader()
        chart_data = loader.get_combined_data(
            averaging_period=selected_averaging,
            id_sites=all_sensors,
            pollutants=[selected_pollutant]
        )
        # Build id_site to site_code and site_name mapping
        active_sensors = loader.get_active_sensors()
        id_to_code = dict(zip(active_sensors["id_site"], active_sensors["site_code"]))
        id_to_name = dict(zip(active_sensors["id_site"], active_sensors["site_name"]))
        
        if chart_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No data found for selected sensors and filters.",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            fig.update_layout(
                title=dict(text="Time Series Chart", font=dict(color='black', size=14), x=0.5, xanchor='center'),
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig
        
        # Create time series chart
        fig = go.Figure()
        
        for sensor in all_sensors:
            sensor_data = chart_data[chart_data['id_site'] == sensor]
            if len(sensor_data) > 0:
                # Create date column for x-axis
                if selected_averaging == 'Month':
                    sensor_data['date'] = pd.to_datetime(dict(year=sensor_data['year'], month=sensor_data['month'], day=1))
                else:  # Annual
                    sensor_data['date'] = pd.to_datetime(sensor_data['year'], format='%Y')
                sensor_data = sensor_data.sort_values('date')
                # Legend label logic: just site_code for time series chart
                site_code = id_to_code.get(sensor, sensor)
                trace_name = site_code
                fig.add_trace(go.Scatter(
                    x=sensor_data['date'],
                    y=sensor_data['value'],
                    mode='lines+markers',
                    name=trace_name,
                    line=dict(width=2),
                    marker=dict(size=4)
                ))
        
        # Add reference lines for WHO and UK limits if pollutant is NO2, PM2.5, or PM10
        ref_lines = []
        if selected_pollutant in ["NO2", "PM2.5", "PM10"]:
            who_limits = {"NO2": 10, "PM2.5": 5, "PM10": 15}
            uk_limits = {"NO2": 40, "PM2.5": 20, "PM10": 40}
            if selected_pollutant in who_limits:
                ref_lines.append(dict(type='line', y0=who_limits[selected_pollutant], y1=who_limits[selected_pollutant], xref='paper', x0=0, x1=1, line=dict(color='green', width=2, dash='dot')))
            if selected_pollutant in uk_limits:
                ref_lines.append(dict(type='line', y0=uk_limits[selected_pollutant], y1=uk_limits[selected_pollutant], xref='paper', x0=0, x1=1, line=dict(color='red', width=2, dash='dot')))
        
        fig.update_layout(
            height=170,
            margin=dict(l=40, r=40, t=40, b=40),
            plot_bgcolor='white',
            paper_bgcolor='white',
            showlegend=True,
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="right", 
                x=1,
                font=dict(family="monospace", size=10),  # Narrow font for legend
                bgcolor='rgba(255,255,255,0.9)'
            ),
            yaxis=dict(
                showticklabels=False, 
                range=[0, None], 
                fixedrange=False, 
                autorange=True
            ),
            shapes=ref_lines,
            xaxis=dict(title="Year")
        )
        # Always show y=0
        fig.update_yaxes(range=[0, None])
        return fig
        
    except Exception as e:
        print(f"[ERROR] Error loading time series data from Supabase: {e}")
        fig = go.Figure()
        fig.add_annotation(
            text="Error loading data from database",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="red")
        )
        fig.update_layout(
            height=170,
            margin=dict(l=40, r=40, t=40, b=40),
            plot_bgcolor='white',
            paper_bgcolor='white',
            showlegend=True,
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="right", 
                x=1,
                font=dict(family="monospace", size=10),
                bgcolor='rgba(255,255,255,0.9)'
            ),
            yaxis=dict(
                showticklabels=False, 
                range=[0, None], 
                fixedrange=False, 
                autorange=True
            ),
            shapes=ref_lines,
            xaxis=dict(title="Year")
        )
        fig.update_yaxes(range=[0, None])
        return fig

# Callback for bar chart (small chart)
@callback(
    Output('bar-graph', 'figure'),
    [Input('chart-sensors-dropdown', 'value'),
     Input('selected-pollutant', 'data'),
     Input('selected-averaging', 'data'),
     Input('selected-year', 'data'),
     Input('selected-month', 'data')],
    prevent_initial_call=False
)
def update_bar_chart(dropdown_sensors, selected_pollutant, selected_averaging, selected_year, selected_month):
    all_sensors = dropdown_sensors or []
    all_sensors = list(set(all_sensors))  # Ensure no duplicates
    print(f"[DEBUG] Bar chart - selected sensors: {all_sensors}")
    if not all_sensors:
        fig = go.Figure()
        fig.add_annotation(
            text="No sensors selected. Click on sensors in the map or use the dropdown to select sensors.",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="gray")
        )
        fig.update_layout(
            title=dict(text="Bar Chart", font=dict(color='black', size=14), x=0.5, xanchor='center'),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig
    
    # Filter data for selected sensors, pollutant, averaging period, and time period
    try:
        loader = get_supabase_loader()
        chart_data = loader.get_combined_data(
            averaging_period=selected_averaging,
            id_sites=all_sensors,
            pollutants=[selected_pollutant],
            years=[selected_year],
            months=[selected_month] if selected_averaging == 'Month' else None
        )
        
        if chart_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No data found for selected sensors and filters.",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            fig.update_layout(
                title=dict(text="Bar Chart", font=dict(color='black', size=14), x=0.5, xanchor='center'),
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig
        
        # Create bar chart - average values by sensor
        sensor_avg = chart_data.groupby('id_site')['value'].mean().reset_index()
        sensor_avg = sensor_avg.sort_values('value', ascending=False)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=sensor_avg['id_site'],
            y=sensor_avg['value'],
            marker_color='lightblue',
            name=f"{selected_pollutant} Average"
        ))
        
        # Add reference lines for WHO and UK limits if pollutant is NO2, PM2.5, or PM10
        ref_lines = []
        if selected_pollutant in ["NO2", "PM2.5", "PM10"]:
            who_limits = {"NO2": 10, "PM2.5": 5, "PM10": 15}
            uk_limits = {"NO2": 40, "PM2.5": 20, "PM10": 40}
            if selected_pollutant in who_limits:
                ref_lines.append(dict(type='line', y0=who_limits[selected_pollutant], y1=who_limits[selected_pollutant], xref='paper', x0=0, x1=1, line=dict(color='green', width=2, dash='dot')))
            if selected_pollutant in uk_limits:
                ref_lines.append(dict(type='line', y0=uk_limits[selected_pollutant], y1=uk_limits[selected_pollutant], xref='paper', x0=0, x1=1, line=dict(color='red', width=2, dash='dot')))
        
        fig.update_layout(
            height=170,
            margin=dict(l=40, r=40, t=40, b=40),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(tickangle=45),
            yaxis=dict(showticklabels=False, range=[0, None]),
            shapes=ref_lines
        )
        return fig
        
    except Exception as e:
        print(f"[ERROR] Error loading bar chart data from Supabase: {e}")
        fig = go.Figure()
        fig.add_annotation(
            text="Error loading data from database",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="red")
        )
        fig.update_layout(
            height=170,
            margin=dict(l=40, r=40, t=40, b=40),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(tickangle=45),
            yaxis=dict(showticklabels=False, range=[0, None]),
            shapes=[]
        )
        return fig

# Callback for Clear Map Selection button
@callback(
    Output('map-graph', 'selectedData', allow_duplicate=True),
    Input('clear-map-selection-button', 'n_clicks'),
    prevent_initial_call=True
)
def clear_map_selection(n_clicks):
    if n_clicks:
        return None
    return dash.no_update

@callback(
    [Output('top-area-grid', 'className'),
     Output('map-graph', 'className'),
     Output('map-card', 'className'),
     Output('small-charts-stack', 'className'),
     Output('expand-map-btn', 'children'),
     Output('detailed-section', 'className'),
     Output('tools-container', 'className'),
     Output('expand-chart-btn', 'children'),
     Output('detailed-chart-card', 'className')],
    [Input('map-expanded', 'data'),
     Input('chart-expanded', 'data')],
    prevent_initial_call=False
)
def update_layout(map_expanded, chart_expanded):
    # Top area logic
    if map_expanded:
        top_grid_class = "top-grid-map-expanded"
        map_class = "map-expanded"
        small_charts_class = "hidden"
        map_btn = "Collapse Map"
    else:
        top_grid_class = "top-grid-compact"
        map_class = "map-compact"
        small_charts_class = "charts-stack"
        map_btn = "Expand Map"
    # Detailed section logic
    if chart_expanded:
        detailed_section_class = "detailed-section-expanded"
        tools_class = "tools-row"
        chart_btn = "Collapse Chart"
        chart_card_class = "card detailed-expanded"
    else:
        detailed_section_class = "detailed-section-compact"
        tools_class = "tools-stack"
        chart_btn = "Expand Chart"
        chart_card_class = "card detailed-compact"
    return (
        top_grid_class,
        map_class,   # for map-graph
        f"card {map_class}",  # for map-card
        small_charts_class,
        map_btn,
        detailed_section_class,
        tools_class,
        chart_btn,
        chart_card_class
    )

@callback(
    Output('map-expanded', 'data'),
    [Input('expand-map-btn', 'n_clicks')],
    [State('map-expanded', 'data')],
    prevent_initial_call=True
)
def set_map_expanded(n, expanded):
    if n is None:
        return False
    return not expanded

@callback(
    Output('chart-expanded', 'data'),
    [Input('expand-chart-btn', 'n_clicks')],
    [State('chart-expanded', 'data')],
    prevent_initial_call=True
)
def set_chart_expanded(n, expanded):
    if n is None:
        return False
    return not expanded

@callback(
    Output('legend-mode-store', 'data'),
    Input('toggle-legend-btn', 'n_clicks'),
    State('legend-mode-store', 'data'),
    prevent_initial_call=False
)
def cycle_legend_mode(n_clicks, current_mode):
    if n_clicks is None:
        return 0
    return (current_mode + 1) % 5

def marker_size_for_zoom(zoom, base_zoom=12, base_size=20):
    """Dramatically scale marker size with zoom level."""
    return max(7, int(base_size *1.2**(zoom - base_zoom)))

@callback(
    Output('chart-sensors-dropdown', 'options'),
    [Input('selected-boroughs', 'data'),
     Input('selected-sensor-types', 'data')],
    prevent_initial_call=False
)
def update_sensor_dropdown_options(selected_boroughs, selected_sensor_types):
    """Update sensor dropdown options based on selected boroughs and sensor types"""
    try:
        loader = get_supabase_loader()
        active_sensors = loader.get_active_sensors()
        
        if active_sensors.empty:
            return []
        
        # Filter sensors by selected boroughs and sensor types
        filtered_sensors = active_sensors[
            active_sensors['borough'].isin(selected_boroughs) & 
            active_sensors['sensor_type'].isin(selected_sensor_types)
        ]
        
        # Create options with id_site as value and site_code as label
        options = []
        for _, sensor in filtered_sensors.iterrows():
            # Use site_code for label, id_site for value
            site_code = sensor.get('site_code', sensor['id_site'])
            site_name = sensor.get('site_name', '')
            options.append({
                'label': f"{site_code}: {site_name}" if site_name else site_code,
                'value': sensor['id_site']
            })
        
        # Sort by id_site
        options.sort(key=lambda x: x['value'])
        
        return options
        
    except Exception as e:
        print(f"[ERROR] Error updating sensor dropdown options: {e}")
        return []

@callback(
    [Output('chart-start-date', 'date'),
     Output('chart-end-date', 'date')],
    [Input('selected-pollutant', 'data'),
     Input('selected-averaging', 'data')],
    prevent_initial_call=False
)
def update_date_picker_defaults(selected_pollutant, selected_averaging):
    """Update date picker defaults based on available data"""
    try:
        loader = get_supabase_loader()
        
        # Get all data for the selected pollutant and averaging period
        all_data = loader.get_combined_data(
            averaging_period=selected_averaging,
            pollutants=[selected_pollutant]
        )
        
        if all_data.empty:
            # Fallback to current year
            current_year = datetime.now().year
            if selected_averaging == 'Annual':
                start_date = f"{current_year}-01-01"
                end_date = f"{current_year}-12-31"
            else:
                start_date = f"{current_year}-01-01"
                end_date = f"{current_year}-12-31"
        else:
            # Convert date column to datetime if it's not already
            if 'date' in all_data.columns:
                all_data['date'] = pd.to_datetime(all_data['date'])
                start_date = all_data['date'].min().strftime('%Y-%m-%d')
                end_date = all_data['date'].max().strftime('%Y-%m-%d')
            else:
                # Fallback to year-based dates
                min_year = all_data['year'].min()
                max_year = all_data['year'].max()
                if selected_averaging == 'Annual':
                    start_date = f"{min_year}-01-01"
                    end_date = f"{max_year}-12-31"
                else:
                    start_date = f"{min_year}-01-01"
                    end_date = f"{max_year}-12-31"
        
        return start_date, end_date
        
    except Exception as e:
        print(f"[ERROR] Error setting date picker defaults: {e}")
        # Fallback to current year
        current_year = datetime.now().year
        return f"{current_year}-01-01", f"{current_year}-12-31"

# Callback for Clear Selection button
@callback(
    Output('chart-sensors-dropdown', 'value', allow_duplicate=True),
    Input('clear-selection-button', 'n_clicks'),
    prevent_initial_call=True
)
def clear_sensor_selection(n_clicks):
    if n_clicks:
        return []
    return dash.no_update

# Add callback to handle custom title logic
from dash import no_update
@callback(
    Output('custom-title-store', 'data'),
    [Input('apply-title-btn', 'n_clicks'), Input('reset-title-btn', 'n_clicks')],
    State('custom-title-input', 'value'),
    State('custom-title-store', 'data'),
    prevent_initial_call=True
)
def handle_custom_title(apply_clicks, reset_clicks, input_value, current_store):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'apply-title-btn' and input_value:
        return input_value
    elif button_id == 'reset-title-btn':
        return None
    return no_update


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)

# Expose the server for gunicorn
server = app.server

