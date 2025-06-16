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

# Add this after imports, before any callbacks or functions
SYMBOL_MAP = {
    "DT": "square",
    "Clarity": "circle",
    "Automatic": "triangle-up"
}

# Load data from CSV file
def load_data():
    """Load environmental data from GitHub CSV file"""
    csv_url = 'https://raw.githubusercontent.com/tomfi3/environ/main/environmental_data_merged.csv'
    df = pd.read_csv(csv_url)
    # Standardize Richmond borough names
    df['borough'] = df['borough'].replace(to_replace=r'(?i)richmond.*', value='Richmond', regex=True)
    return df

# Borough name mapping for short labels
BOROUGH_LABELS = {
    'Wandsworth': 'Wand',
    'Richmond': 'Rich',
    'Merton': 'Mert'
}

# Load data
df = load_data()

# Get unique values for filters
boroughs = sorted(df['borough'].unique().tolist())
pollutants = sorted(df['pollutant'].unique().tolist())
sensor_types = sorted(df['sensor_type'].unique().tolist())
years = sorted([int(y) for y in df['year'].unique()])
months = sorted([int(m) for m in df['month'].unique()])

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
    dcc.Store(id='selected-individual-sensors', data=[]),  # For individual sensor selection
    dcc.Store(id='selected-averaging', data='Annual'),
    dcc.Store(id='selected-year', data=2024),
    dcc.Store(id='selected-month', data=1),
    dcc.Store(id='selected-color-scale', data='WHO'),
    dcc.Store(id='selected-map-style', data='carto-voyager'),
    dcc.Store(id='map-view-store', data={'center': {'lat': 51.445, 'lon': -0.22}, 'zoom': 11.3}),
    dcc.Store(id='map-expanded', data=False),
    dcc.Store(id='chart-expanded', data=False),
    
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
                    html.Button(
                        "Expand Chart", id="expand-chart-btn", className="expand-button"
                    )
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
                            options=[{'label': s, 'value': s} for s in sorted(df['site_code'].unique())],
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
                            date=df['date'].min(),
                            className="dropdown-style"
                        )
                    ], style={'marginBottom': '12px'}),
                    html.Div([
                        html.Label("Chart End Date", style={'fontWeight': '500', 'marginBottom': '4px', 'display': 'block', 'fontSize': '12px'}),
                        dcc.DatePickerSingle(
                            id='chart-end-date',
                            date=df['date'].max(),
                            className="dropdown-style"
                        )
                    ], style={'marginBottom': '12px'}),
                    html.Button("Update Chart", id="update-chart-button", className="export-button")
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
    if not relayoutData:
        return current_view
    new_center = current_view['center']
    new_zoom = current_view['zoom']
    if 'mapbox.center' in relayoutData:
        new_center = relayoutData['mapbox.center']
    if 'mapbox.zoom' in relayoutData:
        new_zoom = relayoutData['mapbox.zoom']
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
    [Input('selected-boroughs', 'data'),
     Input('selected-pollutant', 'data'),
     Input('selected-sensor-types', 'data'),
     Input('selected-averaging', 'data'),
     Input('selected-year', 'data'),
     Input('selected-month', 'data'),
     Input('selected-color-scale', 'data'),
     Input('selected-map-style', 'data')],
    [State('map-view-store', 'data'),
     State('selected-individual-sensors', 'data')],
    prevent_initial_call=False
)
def update_map(selected_boroughs, selected_pollutant, selected_sensor_types, selected_averaging, selected_year, selected_month, selected_color_scale, selected_map_style, map_view, selected_individual_sensors):
    print(f"[DEBUG] Map callback inputs:")
    print(f"  - selected_boroughs: {selected_boroughs}")
    print(f"  - selected_pollutant: {selected_pollutant}")
    print(f"  - selected_sensor_types: {selected_sensor_types}")
    print(f"  - selected_averaging: {selected_averaging}")
    print(f"  - selected_year: {selected_year}")
    print(f"  - selected_month: {selected_month}")
    print(f"  - selected_color_scale: {selected_color_scale}")
    print(f"  - selected_map_style: {selected_map_style}")
    print(f"[DEBUG] Map callback states:")
    print(f"  - selected_individual_sensors: {selected_individual_sensors}")
    
    # Always show all relevant sensor locations, even if no data for selected pollutant/period
    all_sensors = df[['site_code', 'borough', 'lat', 'lon', 'sensor_type']].drop_duplicates()
    all_sensors = all_sensors[
        all_sensors['borough'].isin(selected_boroughs) & 
        all_sensors['sensor_type'].isin(selected_sensor_types)
    ]
    # Get data for the selected filters
    filtered_df = df.copy()
    filtered_df = filtered_df[filtered_df['borough'].isin(selected_boroughs)]
    filtered_df = filtered_df[filtered_df['pollutant'] == selected_pollutant]
    filtered_df = filtered_df[filtered_df['sensor_type'].isin(selected_sensor_types)]
    filtered_df = filtered_df[filtered_df['averaging_period'] == selected_averaging]
    filtered_df = filtered_df[filtered_df['year'] == selected_year]
    if selected_averaging == 'Month':
        filtered_df = filtered_df[filtered_df['month'] == selected_month]
    # Map site_code to value
    sensor_value_map = dict(zip(filtered_df['site_code'], filtered_df['value']))
    # Filter sensors to only those with data for the selected pollutant/filters
    sensors_with_data = all_sensors[all_sensors['site_code'].isin(sensor_value_map.keys())]

    # Add a single trace for all sensors with data
    marker_colors = []
    for _, row in sensors_with_data.iterrows():
        val = sensor_value_map.get(row['site_code'], None)
        marker_colors.append(get_color_for_value(val, selected_pollutant, selected_color_scale))
    
    fig = go.Figure()
    fig.add_trace(go.Scattermap(
        lat=sensors_with_data['lat'],
        lon=sensors_with_data['lon'],
        mode='markers+text',
        marker=dict(
            size=20,
            color=marker_colors,
            opacity=0.95,
            allowoverlap=True
        ),
        text=sensors_with_data['site_code'],
        textposition='top center',
        name=f"Sensors with data",
        customdata=sensors_with_data.apply(
            lambda row: [
                row['borough'],
                row['sensor_type'],
                sensor_value_map.get(row['site_code'], float('nan'))
            ],
            axis=1
        ).tolist(),
        hovertemplate=(
            "<b>%{text}</b><br>" +
            "Borough: %{customdata[0]}<br>" +
            "Type: %{customdata[1]}<br>" +
            "Value: %{customdata[2]:.1f} μg/m³<extra></extra>"
        )
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
        uirevision="stay",
        map=dict(
            style=selected_map_style,
            center=map_view['center'],
            zoom=map_view['zoom']
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        shapes=legend_shapes,
        annotations=legend_annotations
    )
    
    return fig

@callback(
    Output('detailed-chart', 'figure'),
    [Input('chart-sensors-dropdown', 'value'),
     Input('map-graph', 'selectedData'),
     Input('map-graph', 'clickData'),
     Input('selected-pollutant', 'data'),
     Input('selected-averaging', 'data'),
     Input('chart-start-date', 'date'),
     Input('chart-end-date', 'date'),
     Input('update-chart-button', 'n_clicks')],
    prevent_initial_call=False
)
def update_detailed_chart(dropdown_sensors, lasso_data, click_data, selected_pollutant, selected_averaging, chart_start_date, chart_end_date, n_clicks):
    all_sensors = []
    if dropdown_sensors:
        all_sensors.extend(dropdown_sensors)
    if lasso_data and 'points' in lasso_data:
        lasso_sensors = [point['text'] for point in lasso_data['points'] if 'text' in point]
        all_sensors.extend(lasso_sensors)
    if click_data and 'points' in click_data:
        click_sensors = [point['text'] for point in click_data['points'] if 'text' in point]
        all_sensors.extend(click_sensors)
    all_sensors = list(set(all_sensors))
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
            paper_bgcolor='white',
            xaxis=dict(
                showline=True,
                linewidth=2,
                linecolor='black',
                mirror=True,
                gridcolor='#e0e0e0',
                zeroline=True,
                zerolinecolor='black'
            ),
            yaxis=dict(
                showline=True,
                linewidth=2,
                linecolor='black',
                mirror=True,
                gridcolor='#e0e0e0',
                zeroline=True,
                zerolinecolor='black',
                range=[0, 1]
            ),
        )
        return fig
    chart_data = df[
        (df['site_code'].isin(all_sensors)) &
        (df['pollutant'] == selected_pollutant)
    ].copy()
    if len(chart_data) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No data for selected sensors",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="gray")
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
                zerolinecolor='black'
            ),
            yaxis=dict(
                showline=True,
                linewidth=2,
                linecolor='black',
                mirror=True,
                gridcolor='#e0e0e0',
                zeroline=True,
                zerolinecolor='black',
                range=[0, 1]
            ),
        )
        return fig
    fig = go.Figure()
    max_y = 0
    for sensor in all_sensors:
        sensor_data = chart_data[chart_data['site_code'] == sensor]
        if len(sensor_data) > 0:
            if selected_averaging == 'Month':
                sensor_data['date'] = pd.to_datetime(dict(year=sensor_data['year'], month=sensor_data['month'], day=1))
            else:
                sensor_data['date'] = pd.to_datetime(sensor_data['year'], format='%Y')
            sensor_data = sensor_data.sort_values('date')
            fig.add_trace(go.Scatter(
                x=sensor_data['date'],
                y=sensor_data['value'],
                mode='lines+markers',
                name=sensor,
                line=dict(width=2),
                marker=dict(size=4)
            ))
            max_y = max(max_y, sensor_data['value'].max())
    # Add limit lines
    limit_lines = []
    if selected_pollutant == 'NO2':
        limit_lines = [
            dict(type='line', y0=40, y1=40, xref='paper', x0=0, x1=1, line=dict(color='red', width=2, dash='dot')),
            dict(type='line', y0=10, y1=10, xref='paper', x0=0, x1=1, line=dict(color='blue', width=2, dash='dot'))
        ]
        max_y = max(max_y, 45)
    elif selected_pollutant == 'PM2.5':
        limit_lines = [
            dict(type='line', y0=20, y1=20, xref='paper', x0=0, x1=1, line=dict(color='red', width=2, dash='dot')),
            dict(type='line', y0=5, y1=5, xref='paper', x0=0, x1=1, line=dict(color='blue', width=2, dash='dot'))
        ]
        max_y = max(max_y, 22)
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
            zerolinecolor='black'
        ),
        yaxis=dict(
            showline=True,
            linewidth=2,
            linecolor='black',
            mirror=True,
            gridcolor='#e0e0e0',
            zeroline=True,
            zerolinecolor='black',
            range=[0, max_y * 1.05]
        ),
        shapes=limit_lines
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
def update_pollutant_selection(n_clicks):
    if not n_clicks or not any(n_clicks):
        selected_pollutant = 'NO2'
    else:
        clicked_idx = max((i for i, v in enumerate(n_clicks) if v), key=lambda i: n_clicks[i])
        selected_pollutant = pollutants[clicked_idx]
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
def update_sensor_type_selection(n_clicks, current_selection):
    ctx = dash.callback_context
    
    # Handle initial load - return default state with all sensor types selected
    if not ctx.triggered:
        return sensor_types, [
            f"filter-button multi-select selected"
            for sensor in sensor_types
        ]
    
    current = current_selection or sensor_types
    
    if not n_clicks or not any(n_clicks):
        # If no clicks, return current selection
        return current, [
            f"filter-button multi-select {'selected' if sensor in current else ''}"
            for sensor in sensor_types
        ]
    
    clicked_idx = max((i for i, v in enumerate(n_clicks) if v), key=lambda i: n_clicks[i])
    clicked_sensor = sensor_types[clicked_idx]
    
    if clicked_sensor in current:
        new_selection = [s for s in current if s != clicked_sensor]
    else:
        new_selection = current + [clicked_sensor]
    
    button_classes = [
        f"filter-button multi-select {'selected' if sensor in new_selection else ''}"
        for sensor in sensor_types
    ]
    return new_selection, button_classes

@callback(
    [Output('selected-averaging', 'data'),
     Output({'type': 'averaging-btn', 'index': ALL}, 'className')],
    [Input({'type': 'averaging-btn', 'index': ALL}, 'n_clicks')],
    prevent_initial_call=False
)
def update_averaging_selection(n_clicks):
    periods = ['Annual', 'Month']
    if not n_clicks or not any(n_clicks):
        selected_period = 'Annual'
    else:
        clicked_idx = max((i for i, v in enumerate(n_clicks) if v), key=lambda i: n_clicks[i])
        selected_period = periods[clicked_idx]
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
def update_color_scale_selection(n_clicks):
    scales = ['WHO', 'Borough', 'UK']
    if not n_clicks or not any(n_clicks):
        selected_scale = 'WHO'
    else:
        clicked_idx = max((i for i, v in enumerate(n_clicks) if v), key=lambda i: n_clicks[i])
        selected_scale = scales[clicked_idx]
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
                (0, 10, 'Excellent', '#00ff00'),      # Green - WHO guideline
                (10, 20, 'Good', '#ffff00'),          # Yellow
                (20, 30, 'Moderate', '#ffa500'),      # Orange
                (30, 40, 'Poor', '#ff6600'),          # Dark Orange
                (40, float('inf'), 'Very Poor', '#ff0000')  # Red - UK legal limit
            ]
        },
        'Borough': {
            'name': 'Borough Standards',
            'ranges': [
                (0, 15, 'Excellent', '#00ff00'),      # Green
                (15, 25, 'Good', '#ffff00'),          # Yellow
                (25, 35, 'Moderate', '#ffa500'),      # Orange
                (35, 45, 'Poor', '#ff6600'),          # Dark Orange
                (45, float('inf'), 'Very Poor', '#ff0000')  # Red
            ]
        },
        'UK': {
            'name': 'UK Legal Limits',
            'ranges': [
                (0, 20, 'Excellent', '#00ff00'),      # Green
                (20, 30, 'Good', '#ffff00'),          # Yellow
                (30, 40, 'Moderate', '#ffa500'),      # Orange
                (40, 50, 'Poor', '#ff6600'),          # Dark Orange
                (50, float('inf'), 'Very Poor', '#ff0000')  # Red - UK legal limit
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
    [Output('selected-individual-sensors', 'data'),
     Output('chart-sensors-dropdown', 'value')],
    [Input('map-graph', 'clickData'),
     Input('map-graph', 'selectedData')],
    [State('selected-individual-sensors', 'data')],
    prevent_initial_call=True
)
def update_individual_sensor_selection(click_data, selected_data, current_selection):
    ctx = dash.callback_context
    print(f"[DEBUG] Individual sensor selection callback triggered")
    print(f"  - trigger_id: {ctx.triggered[0]['prop_id'] if ctx.triggered else 'None'}")
    print(f"  - click_data: {click_data}")
    print(f"  - selected_data: {selected_data}")
    print(f"  - current_selection: {current_selection}")
    
    if not ctx.triggered:
        return current_selection or [], current_selection or []
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    current = current_selection or []
    
    if 'clickData' in trigger_id:
        if click_data:
            # Single click on a sensor - clear and select only this sensor
            point = click_data['points'][0]
            sensor_code = point['text']  # site_code is in the text field
            new_selection = [sensor_code]
            print(f"[DEBUG] Single click on sensor: {sensor_code}, new selection: {new_selection}")
            return new_selection, new_selection
        else:
            # Click on empty map - clear selection
            print(f"[DEBUG] Click on empty map, clearing selection")
            return [], []
    
    elif 'selectedData' in trigger_id:
        if selected_data:
            # Lasso/box selection - clear and select only lassoed sensors
            selected_points = selected_data['points']
            selected_sensors = [point['text'] for point in selected_points]
            print(f"[DEBUG] Lasso selection: {selected_sensors}")
            return selected_sensors, selected_sensors
        else:
            # Lasso selection cleared - clear selection
            print(f"[DEBUG] Lasso selection cleared")
            return [], []
    
    return current, current

# Callback to sync dropdown with selected individual sensors
@callback(
    Output('selected-individual-sensors', 'data', allow_duplicate=True),
    Input('chart-sensors-dropdown', 'value'),
    prevent_initial_call=True
)
def update_sensors_from_dropdown(dropdown_value):
    return dropdown_value or []

# Callback for Clear Selection button
@callback(
    [Output('selected-individual-sensors', 'data', allow_duplicate=True),
     Output('chart-sensors-dropdown', 'value', allow_duplicate=True)],
    Input('clear-selection-button', 'n_clicks'),
    prevent_initial_call=True
)
def clear_sensor_selection(n_clicks):
    if n_clicks:
        return [], []
    return dash.no_update, dash.no_update

# Callback for time series chart (small chart)
@callback(
    Output('time-series-graph', 'figure'),
    [Input('chart-sensors-dropdown', 'value'),
     Input('map-graph', 'selectedData'),
     Input('map-graph', 'clickData'),
     Input('selected-pollutant', 'data'),
     Input('selected-averaging', 'data')],
    prevent_initial_call=False
)
def update_time_series_chart(dropdown_sensors, lasso_data, click_data, selected_pollutant, selected_averaging):
    all_sensors = []
    if dropdown_sensors:
        all_sensors.extend(dropdown_sensors)
    
    if lasso_data and 'points' in lasso_data:
        lasso_sensors = [point['text'] for point in lasso_data['points'] if 'text' in point]
        all_sensors.extend(lasso_sensors)
    
    if click_data and 'points' in click_data:
        click_sensors = [point['text'] for point in click_data['points'] if 'text' in point]
        all_sensors.extend(click_sensors)
    
    # Remove duplicates
    all_sensors = list(set(all_sensors))
    
    print(f"[DEBUG] Time series chart - selected sensors: {all_sensors}")
    
    if not all_sensors:
        fig = go.Figure()
        fig.add_annotation(
            text="No sensors selected",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="gray")
        )
        fig.update_layout(
            title="Time Series",
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig
    
    # Filter data for selected sensors
    chart_data = df[
        (df['site_code'].isin(all_sensors)) &
        (df['pollutant'] == selected_pollutant) &
        (df['averaging_period'] == selected_averaging)
    ].copy()
    
    if len(chart_data) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No data for selected sensors",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="gray")
        )
        fig.update_layout(
            title="Time Series",
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig
    
    # Create time series chart
    fig = go.Figure()
    
    for sensor in all_sensors:
        sensor_data = chart_data[chart_data['site_code'] == sensor]
        if len(sensor_data) > 0:
            # Create date column for x-axis
            if selected_averaging == 'Month':
                sensor_data['date'] = pd.to_datetime(dict(year=sensor_data['year'], month=sensor_data['month'], day=1))
            else:  # Annual
                sensor_data['date'] = pd.to_datetime(sensor_data['year'], format='%Y')
            
            sensor_data = sensor_data.sort_values('date')
            
            fig.add_trace(go.Scatter(
                x=sensor_data['date'],
                y=sensor_data['value'],
                mode='lines+markers',
                name=sensor,
                line=dict(width=2),
                marker=dict(size=4)
            ))
    
    fig.update_layout(
        title="Time Series",
        xaxis_title="Date",
        yaxis_title=f"{selected_pollutant} ({selected_averaging})",
        height=170,
        margin=dict(l=40, r=40, t=40, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

# Callback for bar chart (small chart)
@callback(
    Output('bar-graph', 'figure'),
    [Input('chart-sensors-dropdown', 'value'),
     Input('map-graph', 'selectedData'),
     Input('map-graph', 'clickData'),
     Input('selected-pollutant', 'data'),
     Input('selected-averaging', 'data')],
    prevent_initial_call=False
)
def update_bar_chart(dropdown_sensors, lasso_data, click_data, selected_pollutant, selected_averaging):
    all_sensors = []
    if dropdown_sensors:
        all_sensors.extend(dropdown_sensors)
    
    if lasso_data and 'points' in lasso_data:
        lasso_sensors = [point['text'] for point in lasso_data['points'] if 'text' in point]
        all_sensors.extend(lasso_sensors)
    
    if click_data and 'points' in click_data:
        click_sensors = [point['text'] for point in click_data['points'] if 'text' in point]
        all_sensors.extend(click_sensors)
    
    # Remove duplicates
    all_sensors = list(set(all_sensors))
    
    print(f"[DEBUG] Bar chart - selected sensors: {all_sensors}")
    
    if not all_sensors:
        fig = go.Figure()
        fig.add_annotation(
            text="No sensors selected",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="gray")
        )
        fig.update_layout(
            title="Bar Chart",
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig
    
    # Filter data for selected sensors
    chart_data = df[
        (df['site_code'].isin(all_sensors)) &
        (df['pollutant'] == selected_pollutant) &
        (df['averaging_period'] == selected_averaging)
    ].copy()
    
    if len(chart_data) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No data for selected sensors",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="gray")
        )
        fig.update_layout(
            title="Bar Chart",
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig
    
    # Create bar chart - average values by sensor
    sensor_avg = chart_data.groupby('site_code')['value'].mean().reset_index()
    sensor_avg = sensor_avg.sort_values('value', ascending=False)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=sensor_avg['site_code'],
        y=sensor_avg['value'],
        marker_color='lightblue',
        marker_line_color='darkblue',
        marker_line_width=1,
        opacity=0.8
    ))
    
    fig.update_layout(
        title="Average Values by Sensor",
        xaxis_title="Sensor",
        yaxis_title=f"{selected_pollutant} ({selected_averaging})",
        height=170,
        margin=dict(l=40, r=40, t=40, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(tickangle=45)
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))   # 10000 is a safe default
    app.run(server="0.0.0.0", port=port, debug=False)
