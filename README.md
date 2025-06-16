# Environmental Monitoring Dashboard

A modern, interactive dashboard for monitoring environmental pollution data across London boroughs.

## Features

### 🗺️ Interactive Map
- Real-time pollution data visualization
- Color-coded sensor locations
- Click to select sensors for detailed analysis
- Borough boundary highlighting

### 📊 Multiple Chart Types
- **Main Trend Chart**: Compare multiple sensors over time
- **Annual Averages**: Borough-wise yearly comparisons
- **Monthly Averages**: Seasonal trend analysis

### 🎛️ Advanced Filtering
- **Pollutants**: NO₂, PM2.5, PM10
- **Boroughs**: Wandsworth, Richmond, Merton
- **Sensor Types**: DT, Automatic, Clarity
- **Time Periods**: Monthly or Yearly data
- **Date Range**: 2022-2024

### 📋 Data Management
- Interactive data table
- CSV export functionality
- Real-time data filtering
- Search functionality

## Dashboard Layout

### Left Sidebar
- **Filter Controls**: All filtering options in one place
- **Sensor Selection**: Multi-select dropdown for chart comparison
- **Time Controls**: Year and month sliders

### Main Content Area
- **Top Bar**: Welcome message and search box
- **Map Section**: 
  - Large interactive map (2/3 width)
  - Side charts for quick insights (1/3 width)
- **Chart Section**:
  - Main trend analysis chart
  - Chart and table tools
- **Data Table**: Detailed data view with export options

### Responsive Design
- Expandable chart sections
- Mobile-friendly layout
- Consistent spacing and shadows
- Modern card-based design

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Data Setup**:
   - Place your environmental data in `data/environmental_data.csv`
   - Or use the sample data generator (fallback)

3. **Run the Dashboard**:
   ```bash
   python dashboard_app.py
   ```

4. **Access the Dashboard**:
   - Open your browser to `http://localhost:5000`

## Data Format

The dashboard expects CSV data with the following columns:

```csv
site_code,borough,lat,lon,sensor_type,year,month,month_name,pollutant,value,date,averaging_period
W1,Wandsworth,51.4571,-0.1911,DT,2022,1,Jan,NO2,42.3,2022-01,Month
```

### Required Columns:
- `site_code`: Unique sensor identifier
- `borough`: Borough name
- `lat`, `lon`: GPS coordinates
- `sensor_type`: Type of sensor (DT, Automatic, Clarity)
- `year`, `month`: Time period
- `month_name`: Month abbreviation
- `pollutant`: Pollutant type (NO2, PM2.5, PM10)
- `value`: Measured value
- `date`: Date in YYYY-MM format
- `averaging_period`: Month or Year

## Usage Guide

### 1. Filtering Data
- Use the sidebar buttons to select pollutants, boroughs, and sensor types
- Choose between monthly and yearly data views
- Adjust the year and month sliders as needed

### 2. Map Interaction
- Click on sensor points to select them for detailed analysis
- Use the dropdown to select multiple sensors for comparison
- Selected sensors appear as red stars on the map

### 3. Chart Analysis
- The main chart shows trends for selected sensors
- Side charts provide quick borough and monthly comparisons
- Use the expand buttons to get a full-width view

### 4. Data Export
- Click "Export CSV" to download filtered data
- The export includes only the currently selected sensors and filters

### 5. Search Functionality
- Use the search box in the top bar to find specific sensors
- Search by sensor code or borough name

## Customization

### Styling
- Modify `assets/dashboard.css` for custom styling
- Update `DASHBOARD_STYLES` in `dashboard_app.py` for layout changes

### Data Sources
- Replace `data/environmental_data.csv` with your own data
- Ensure the CSV format matches the required structure

### Adding New Features
- The modular callback structure makes it easy to add new charts
- Use the existing card layout for new dashboard elements

## Technical Details

### Architecture
- **Framework**: Dash (Plotly)
- **Data Processing**: Pandas
- **Visualization**: Plotly Express and Graph Objects
- **Styling**: Custom CSS with responsive design

### Performance
- Efficient data filtering and aggregation
- Lazy loading of chart components
- Optimized for large datasets

### Browser Compatibility
- Modern browsers (Chrome, Firefox, Safari, Edge)
- Responsive design for mobile devices
- Print-friendly styles included

## Troubleshooting

### Common Issues

1. **Data not loading**:
   - Check CSV file format and location
   - Verify column names match exactly
   - Ensure data types are correct

2. **Charts not updating**:
   - Check browser console for JavaScript errors
   - Verify callback dependencies are correct
   - Clear browser cache if needed

3. **Styling issues**:
   - Check CSS file is in the correct location
   - Verify CSS syntax is valid
   - Clear browser cache

### Support
- Check the console for error messages
- Verify all dependencies are installed
- Ensure data format matches requirements

## Future Enhancements

- [ ] Real-time data updates
- [ ] Additional pollutant types
- [ ] Advanced statistical analysis
- [ ] User authentication
- [ ] Data validation tools
- [ ] Automated reporting
- [ ] Mobile app version

## License

This project is open source and available under the MIT License. 