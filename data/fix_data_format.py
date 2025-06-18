import pandas as pd
import os

def fix_data_format():
    """Fix date format and averaging period issues in environmental data"""
    print("Loading environmental data...")
    
    # Read the data file
    input_file = 'EnvironmentalDashboard/data/environmental_data_merged.csv'
    df = pd.read_csv(input_file)
    
    # Make a backup of the original file
    backup_file = 'EnvironmentalDashboard/data/environmental_data_merged_backup.csv'
    df.to_csv(backup_file, index=False)
    print(f"Created backup at: {backup_file}")
    
    # Fix date format for Automatic sensors
    print("\nFixing date format for Automatic sensors...")
    auto_mask = df['sensor_type'] == 'Automatic'
    df.loc[auto_mask, 'date'] = pd.to_datetime(df.loc[auto_mask, 'date']).dt.strftime('%Y-%m')
    
    # Change 'Year' to 'Annual' in averaging_period for Automatic sensors
    print("Changing 'Year' to 'Annual' for Automatic sensors...")
    df.loc[(auto_mask) & (df['averaging_period'] == 'Year'), 'averaging_period'] = 'Annual'
    
    # Save the fixed data
    output_file = 'EnvironmentalDashboard/data/environmental_data_merged.csv'
    df.to_csv(output_file, index=False)
    
    # Print summary of changes
    print("\nSummary of changes:")
    print(f"Total records processed: {len(df)}")
    print(f"Automatic sensor records: {auto_mask.sum()}")
    print(f"Records with 'Year' averaging period: {(df['averaging_period'] == 'Year').sum()}")
    print(f"Records with 'Annual' averaging period: {(df['averaging_period'] == 'Annual').sum()}")
    print(f"\nFixed data saved to: {output_file}")

if __name__ == "__main__":
    fix_data_format() 