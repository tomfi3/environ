import pandas as pd
import numpy as np
from datetime import datetime
import os

def load_and_prepare_data():
    # Read the data files with appropriate encodings
    backup_df = pd.read_csv('EnvironmentalDashboard/data/databackup.csv', encoding='utf-8')
    uk_air_df = pd.read_csv('EnvironmentalDashboard/data/uk_air_quality_data_complete.csv', encoding='utf-8')
    try:
        aq_sensors_df = pd.read_csv('EnvironmentalDashboard/data/AQSensors.csv', encoding='utf-8')
    except UnicodeDecodeError:
        try:
            aq_sensors_df = pd.read_csv('EnvironmentalDashboard/data/AQSensors.csv', encoding='latin1')
        except Exception as e:
            print(f"Error reading AQSensors.csv with latin1 encoding: {str(e)}")
            aq_sensors_df = pd.read_csv('EnvironmentalDashboard/data/AQSensors.csv', encoding='cp1252')
    
    # Filter backup data to only include Clarity and DT sensors
    backup_df = backup_df[backup_df['sensor_type'].isin(['Clarity', 'DT'])]
    
    # Prepare Automatic sensor data from UK air quality data
    auto_df = uk_air_df.copy()
    auto_df['sensor_type'] = 'Automatic'
    auto_df['site_code'] = auto_df['siteCode']
    auto_df['borough'] = auto_df['borough']
    auto_df['site_name'] = auto_df['siteName']
    auto_df['pollutant'] = auto_df['pollutant']
    auto_df['value'] = auto_df['value']
    auto_df['averaging_period'] = auto_df['averaging_period']
    auto_df['date'] = auto_df['date']
    # Extract year and month from date
    auto_df['year'] = pd.to_datetime(auto_df['date'], errors='coerce').dt.year
    auto_df['month'] = pd.to_datetime(auto_df['date'], errors='coerce').dt.month
    auto_df['month_name'] = pd.to_datetime(auto_df['date'], errors='coerce').dt.strftime('%b')
    # Build a mapping from siteCode to latitude and longitude
    aq_sensors_map = aq_sensors_df.drop_duplicates('siteCode').set_index('siteCode')[['latitude', 'longitude']]
    # Map latitude and longitude for each site_code in auto_df
    auto_df['lat'] = auto_df['site_code'].map(aq_sensors_map['latitude'])
    auto_df['lon'] = auto_df['site_code'].map(aq_sensors_map['longitude'])
    # Remove any Automatic sensors that don't have coordinates
    auto_df = auto_df.dropna(subset=['lat', 'lon'])
    # Ensure all required columns are present
    required_columns = [
        'site_code', 'borough', 'lat', 'lon', 'sensor_type',
        'year', 'month', 'month_name', 'pollutant', 'value',
        'date', 'averaging_period', 'site_name'
    ]
    missing_columns = [col for col in required_columns if col not in auto_df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns in auto_df: {missing_columns}")
    auto_df = auto_df[required_columns]
    # Combine all data
    combined_df = pd.concat([backup_df, auto_df], ignore_index=True)
    # Sort the data
    combined_df = combined_df.sort_values(['site_code', 'pollutant', 'year', 'month'])
    return combined_df

def main():
    try:
        print("Loading and preparing data...")
        combined_df = load_and_prepare_data()
        output_file = 'EnvironmentalDashboard/data/environmental_data_merged.csv'
        combined_df.to_csv(output_file, index=False, encoding='utf-8')
        print("\nData merge completed successfully!")
        print(f"\nTotal records: {len(combined_df)}")
        print("\nRecords by sensor type:")
        print(combined_df['sensor_type'].value_counts())
        print("\nRecords by borough:")
        print(combined_df['borough'].value_counts())
        print("\nRecords by pollutant:")
        print(combined_df['pollutant'].value_counts())
        auto_sensors = combined_df[combined_df['sensor_type'] == 'Automatic']
        print(f"\nAutomatic sensors with coordinates: {len(auto_sensors)}")
        print(f"Automatic sensors without coordinates: {len(auto_sensors[auto_sensors['lat'].isna()])}")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main() 