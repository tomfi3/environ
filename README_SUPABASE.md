# Environmental Dashboard - Supabase Integration

This document describes the changes made to migrate the Environmental Dashboard from CSV-based data loading to Supabase database integration.

## Overview

The dashboard has been refactored to use a Supabase database instead of local CSV files. The new architecture provides:

- **Real-time data**: Live data from the database instead of static CSV files
- **Scalable storage**: Database-backed storage for large datasets
- **Better performance**: Efficient queries and indexing
- **Centralized data management**: Single source of truth for all environmental data

## Database Schema

The Supabase database uses the following structure:

### Tables
- **`sensors`**: Sensor metadata (locations, types, deployment info)
- **`hourly_data`**: Raw hourly sensor readings
- **`daily_averages`**: Computed daily averages
- **`monthly_averages`**: Monthly aggregated data
- **`annual_averages`**: Annual aggregated data

### Views
- **`active_sensors`**: Only active sensor deployments
- **`map_monthly_data`**: Monthly data with sensor metadata for maps

### Key Changes in Data Structure

| Old CSV Field | New Database Field | Notes |
|---------------|-------------------|-------|
| `site_code` | `id_site` | Primary identifier for all internal logic |
| `site_name` | `site_name` | Human-readable sensor name |
| `borough` | `borough` | Borough or local authority |
| `lat/lon` | `lat/lon` | Geographic coordinates |
| `sensor_type` | `sensor_type` | Sensor type (DT, Clarity, etc.) |
| `pollutant` | `pollutant` | Pollutant name (NO2, PM2.5, PM10) |
| `value` | `value` | Measurement value |
| `year/month/date` | `year/month/date` | Time information |
| `averaging_period` | `averaging_period` | Data aggregation period |

## Setup Instructions

### 1. Environment Variables

Set the following environment variables:

```bash
export SUPABASE_URL="your_supabase_project_url"
export SUPABASE_ANON_KEY="your_supabase_anon_key"
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

The new requirements include:
- `supabase==2.3.4`: Supabase Python client

### 3. Test Connection

Run the test script to verify your setup:

```bash
python test_supabase.py
```

This will test:
- Environment variable configuration
- Supabase connection
- Data loading from all tables
- Filter functionality

### 4. Run the Dashboard

```bash
python app_modern.py
```

## Key Changes in the Application

### Data Loading

**Before (CSV)**:
```python
def load_data():
    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'environmental_data_merged.csv')
    df = pd.read_csv(csv_path)
    return df
```

**After (Supabase)**:
```python
def load_data():
    loader = get_supabase_loader()
    df = loader.get_annual_data()  # Load from database
    return df
```

### Filter Values

**Before**: Extracted from loaded CSV data
**After**: Queried from database using `get_unique_values()`

### Map Data

**Before**: Filtered global DataFrame
**After**: Dynamic queries based on selected filters

### Chart Data

**Before**: Subset of global DataFrame
**After**: Targeted queries for specific sensors and time periods

## New Files

- `supabase_io.py`: Supabase data loader and connection management
- `test_supabase.py`: Connection and data loading test script
- `README_SUPABASE.md`: This documentation file

## Modified Files

- `app_modern.py`: Updated to use Supabase instead of CSV
- `requirements.txt`: Added Supabase dependency

## Error Handling

The application includes comprehensive error handling:

- **Connection failures**: Graceful fallback with error messages
- **Empty data**: Appropriate UI feedback
- **Missing sensors**: Fallback to default values
- **Database errors**: Logged with user-friendly messages

## Performance Considerations

- **Caching**: Global loader instance to avoid repeated connections
- **Efficient queries**: Targeted queries instead of loading all data
- **Lazy loading**: Data loaded only when needed
- **Connection pooling**: Reuse of database connections

## Troubleshooting

### Common Issues

1. **Environment variables not set**
   - Error: "SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be set"
   - Solution: Set the required environment variables

2. **Connection timeout**
   - Error: "Failed to initialize Supabase loader"
   - Solution: Check network connection and Supabase project status

3. **No data returned**
   - Error: "No data for selected sensors"
   - Solution: Verify database contains data for the selected filters

4. **Permission errors**
   - Error: "Access denied" or similar
   - Solution: Check Supabase RLS (Row Level Security) policies

### Debug Mode

Enable debug logging by setting the log level in `supabase_io.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Migration Notes

- The application maintains backward compatibility with the existing UI
- All existing functionality is preserved
- Sensor selection now uses `id_site` internally but displays `site_code` and `site_name` to users
- Data filtering and charting logic remains the same from a user perspective

## Future Enhancements

- Real-time data updates using Supabase subscriptions
- Advanced caching strategies
- Database query optimization
- Additional data sources and integrations 