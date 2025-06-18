# -*- coding: utf-8 -*-
import os
import pandas as pd
from supabase import create_client, Client
from typing import List, Dict, Optional, Tuple
import logging
from datetime import date

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Continue without dotenv if not installed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global cache for active sensors
_cached_active_sensors_df = None

class SupabaseLoader:
    """Data loader for Supabase environmental database"""
    
    def __init__(self):
        """Initialize Supabase client"""
        # Get Supabase credentials from environment variables
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be set")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized")
    
    def get_sensor_metadata(self) -> pd.DataFrame:
        """Get all sensor metadata from the sensors table"""
        try:
            response = self.supabase.table('sensors').select('*').execute()
            df = pd.DataFrame(response.data)
            logger.info(f"Loaded {len(df)} sensor records")
            return df
        except Exception as e:
            logger.error(f"Error loading sensor metadata: {e}")
            return pd.DataFrame()
    
    def get_active_sensors(self) -> pd.DataFrame:
        """Get only active sensors from the active_sensors view (cached)"""
        global _cached_active_sensors_df
        if _cached_active_sensors_df is None:
            logger.info("Loading active sensors from Supabase (initial cache)...")
            try:
                response = self.supabase.table('active_sensors').select('*').execute()
                _cached_active_sensors_df = pd.DataFrame(response.data)
                logger.info(f"Loaded {len(_cached_active_sensors_df)} active sensor records")
            except Exception as e:
                logger.error(f"Error loading active sensors: {e}")
                return pd.DataFrame()
        return _cached_active_sensors_df
    
    def get_monthly_data(self, 
                        id_sites: Optional[List[str]] = None,
                        pollutants: Optional[List[str]] = None,
                        years: Optional[List[int]] = None,
                        months: Optional[List[int]] = None) -> pd.DataFrame:
        """Get monthly averaged data with sensor metadata"""
        try:
            # Start with the map_monthly_data view which includes sensor metadata
            query = self.supabase.table('map_monthly_data').select('*')
            
            # Apply filters
            if id_sites:
                query = query.in_('id_site', id_sites)
            if pollutants:
                query = query.in_('pollutant', pollutants)
            if years:
                query = query.in_('year', years)
            if months:
                query = query.in_('month', months)
            
            response = query.execute()
            df = pd.DataFrame(response.data)
            
            # Standardize column names to match the old CSV structure
            if not df.empty:
                # Keep id_site as the primary identifier - don't rename to site_code
                df = df.rename(columns={
                    'site_name': 'site_name',
                    'borough': 'borough',
                    'lat': 'lat',
                    'lon': 'lon',
                    'sensor_type': 'sensor_type',
                    'pollutant': 'pollutant',
                    'value': 'value',
                    'year': 'year',
                    'month': 'month',
                    'date': 'date'
                })
                # Add averaging_period column
                df['averaging_period'] = 'Month'
            
            logger.info(f"Loaded {len(df)} monthly data records")
            return df
        except Exception as e:
            logger.error(f"Error loading monthly data: {e}")
            return pd.DataFrame()
    
    def get_annual_data(self,
                       id_sites: Optional[List[str]] = None,
                       pollutants: Optional[List[str]] = None,
                       years: Optional[List[int]] = None) -> pd.DataFrame:
        """Get annual averaged data with sensor metadata"""
        try:
            logger.info(f"[DEBUG] get_annual_data called with:")
            logger.info(f"  - id_sites: {id_sites}")
            logger.info(f"  - pollutants: {pollutants}")
            logger.info(f"  - years: {years}")
            
            # First get annual data
            query = self.supabase.table('annual_averages').select('*')
            
            # Apply filters
            if id_sites:
                query = query.in_('id_site', id_sites)
            if pollutants:
                query = query.in_('pollutant', pollutants)
            if years:
                query = query.in_('year', years)
            
            response = query.execute()
            annual_df = pd.DataFrame(response.data)
            
            logger.info(f"[DEBUG] Annual data query returned {len(annual_df)} rows")
            if not annual_df.empty:
                logger.info(f"[DEBUG] Sample annual data:")
                logger.info(f"  - id_sites: {annual_df['id_site'].unique()[:5]}")
                logger.info(f"  - pollutants: {annual_df['pollutant'].unique()}")
                logger.info(f"  - years: {annual_df['year'].unique()}")
            
            if annual_df.empty:
                logger.info("No annual data found")
                return pd.DataFrame()
            
            # Get sensor metadata from active_sensors view instead of sensors table
            sensor_ids = annual_df['id_site'].unique().tolist()
            logger.info(f"[DEBUG] Getting metadata for {len(sensor_ids)} sensors: {sensor_ids[:5]}")
            sensors_query = self.supabase.table('active_sensors').select('*').in_('id_site', sensor_ids)
            sensors_response = sensors_query.execute()
            sensors_df = pd.DataFrame(sensors_response.data)
            
            logger.info(f"[DEBUG] Sensor metadata query returned {len(sensors_df)} rows")
            
            if sensors_df.empty:
                logger.warning("No sensor metadata found for annual data")
                # Return annual data without metadata
                # Keep id_site as the primary identifier - don't rename to site_code
                annual_df['site_name'] = annual_df['id_site']
                annual_df['borough'] = 'Unknown'
                annual_df['lat'] = 0.0
                annual_df['lon'] = 0.0
                annual_df['sensor_type'] = 'Unknown'
            else:
                # Merge annual data with sensor metadata
                annual_df = annual_df.merge(sensors_df, on='id_site', how='left')
                # Keep id_site as the primary identifier - don't rename to site_code
            
            # Standardize column names to match the old CSV structure
            annual_df['averaging_period'] = 'Annual'
            # Add month column for consistency (set to 1 for annual data)
            annual_df['month'] = 1
            
            logger.info(f"Loaded {len(annual_df)} annual data records")
            return annual_df
        except Exception as e:
            logger.error(f"Error loading annual data: {e}")
            return pd.DataFrame()
    
    def get_combined_data(self,
                         averaging_period: str = 'Annual',
                         id_sites: Optional[List[str]] = None,
                         pollutants: Optional[List[str]] = None,
                         years: Optional[List[int]] = None,
                         months: Optional[List[int]] = None) -> pd.DataFrame:
        """Get data for the specified averaging period"""
        if averaging_period == 'Annual':
            return self.get_annual_data(id_sites, pollutants, years)
        elif averaging_period == 'Month':
            return self.get_monthly_data(id_sites, pollutants, years, months)
        else:
            logger.error(f"Unsupported averaging period: {averaging_period}")
            return pd.DataFrame()
    
    def get_unique_values(self) -> Dict[str, List]:
        """Get unique values for filters from the database"""
        try:
            # Get unique boroughs, pollutants, and sensor types from active sensors
            active_sensors = self.get_active_sensors()
            
            if active_sensors.empty:
                return {
                    'boroughs': [],
                    'pollutants': [],
                    'sensor_types': [],
                    'years': [],
                    'months': []
                }
            
            # Get unique values
            boroughs = sorted(active_sensors['borough'].unique().tolist())
            pollutants = sorted(active_sensors['pollutants_measured'].explode().unique().tolist())
            sensor_types = sorted(active_sensors['sensor_type'].unique().tolist())
            
            # Get year range from monthly data
            monthly_data = self.get_monthly_data()
            years = sorted([int(y) for y in monthly_data['year'].unique()]) if not monthly_data.empty else []
            months = sorted([int(m) for m in monthly_data['month'].unique()]) if not monthly_data.empty else []
            
            return {
                'boroughs': boroughs,
                'pollutants': pollutants,
                'sensor_types': sensor_types,
                'years': years,
                'months': months
            }
        except Exception as e:
            logger.error(f"Error getting unique values: {e}")
            return {
                'boroughs': [],
                'pollutants': [],
                'sensor_types': [],
                'years': [],
                'months': []
            }
    
    def get_sensors_by_borough(self, boroughs: List[str]) -> pd.DataFrame:
        """Get sensors filtered by borough"""
        try:
            active_sensors = self.get_active_sensors()
            if active_sensors.empty:
                return pd.DataFrame()
            
            filtered_sensors = active_sensors[active_sensors['borough'].isin(boroughs)]
            return filtered_sensors
        except Exception as e:
            logger.error(f"Error getting sensors by borough: {e}")
            return pd.DataFrame()
    
    def get_sensors_by_type(self, sensor_types: List[str]) -> pd.DataFrame:
        """Get sensors filtered by sensor type"""
        try:
            active_sensors = self.get_active_sensors()
            if active_sensors.empty:
                return pd.DataFrame()
            
            filtered_sensors = active_sensors[active_sensors['sensor_type'].isin(sensor_types)]
            return filtered_sensors
        except Exception as e:
            logger.error(f"Error getting sensors by type: {e}")
            return pd.DataFrame()

def get_sensor_year_range():
    """Return list of years from earliest sensor start_date to current year."""
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be set")
        supabase = create_client(supabase_url, supabase_key)
        response = supabase.table('sensors').select('start_date').order('start_date', asc=True).limit(1).execute()
        if response.data and response.data[0].get('start_date'):
            first_year = int(response.data[0]['start_date'][:4])
        else:
            first_year = 2000  # fallback if no start_date
    except Exception as e:
        print(f"[ERROR] get_sensor_year_range(): {e}")
        first_year = 2000
    current_year = date.today().year
    return list(range(first_year, current_year + 1))

# Global instance
supabase_loader = None

def initialize_supabase():
    """Initialize the global Supabase loader instance"""
    global supabase_loader
    try:
        supabase_loader = SupabaseLoader()
        logger.info("Supabase loader initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Supabase loader: {e}")
        return False

def get_supabase_loader() -> SupabaseLoader:
    """Get the global Supabase loader instance"""
    global supabase_loader
    if supabase_loader is None:
        if not initialize_supabase():
            raise RuntimeError("Failed to initialize Supabase loader")
    return supabase_loader

def clear_active_sensors_cache():
    """Clear the active sensors cache (for debugging/testing)"""
    global _cached_active_sensors_df
    _cached_active_sensors_df = None
    logger.info("Active sensors cache cleared") 