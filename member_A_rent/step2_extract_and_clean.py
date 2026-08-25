# Step 2: Extract from MongoDB, clean and transform data, save to CSV
import pandas as pd
import numpy as np

from config import get_mongo_client, MONGO_DATABASE


def extract_from_mongodb(collection_name='raw_rent_data'):
    print("Connecting to MongoDB...")

    try:
        client = get_mongo_client()
        db = client[MONGO_DATABASE]

        metadata_doc = db['rent_metadata'].find_one()
        if not metadata_doc:
            print("No metadata found")
            return None

        # Read all chunks in order so the flat array is reassembled correctly
        chunks = list(db[collection_name].find().sort('start_global_index', 1))
        if not chunks:
            print("No data chunks found")
            return None

        data_values = []
        for chunk in chunks:
            data_values.extend(chunk['raw_data_values'])

        print(f"Retrieved {len(data_values):,} values from {len(chunks)} chunks")
        client.close()

        return {'metadata': metadata_doc, 'raw_data_values': data_values}

    except Exception as e:
        print(f"MongoDB error: {e}")
        return None


def transform_px_data_to_dataframe(mongo_document):
    #Reconstruct rows from the flat PX data array.
    print("Transforming data...")

    metadata    = mongo_document['metadata']
    data_values = mongo_document['raw_data_values']

    quarters       = metadata['quarters']
    bedrooms       = metadata['bedrooms']
    property_types = metadata['property_types']
    locations      = metadata['locations']

    # PX axis order follows HEADING: Quarter > Bedrooms > PropertyType > Location
    missing_markers = {'..', '.', ''}
    records = []
    idx = 0

    for quarter in quarters:
        for bedroom in bedrooms:
            for prop_type in property_types:
                for location in locations:
                    if idx >= len(data_values):
                        # Ran out of values - stop completely; the data is malformed
                        print(f"WARNING: data array exhausted at index {idx}, stopping")
                        return pd.DataFrame(records)
                    raw = data_values[idx].strip('"')
                    try:
                        rent_value = float(raw) if raw not in missing_markers else np.nan
                    except ValueError:
                        rent_value = np.nan
                    records.append({
                        'Quarter':      quarter,
                        'Bedrooms':     bedroom,
                        'PropertyType': prop_type,
                        'Location':     location,
                        'MonthlyRent':  rent_value,
                    })
                    idx += 1

    df = pd.DataFrame(records)
    print(f"Built DataFrame: {len(df):,} rows, {df['MonthlyRent'].notna().sum():,} non-null rents")
    return df


def clean_rent_data(df):
    print("Cleaning data...")

    rows_before = len(df)

    df['Year']       = df['Quarter'].str[:4].astype(int)
    df['QuarterNum'] = df['Quarter'].str[-1].astype(int)
    df['County']     = df['Location'].apply(extract_county_name)

    df = df.dropna(subset=['MonthlyRent'])
    rows_after_null = len(df)
    print(f"Dropped {rows_before - rows_after_null:,} rows with missing rent values")

    # Filter outliers - rents under €100 or over €10000 are likely data errors
    df = df[(df['MonthlyRent'] >= 100) & (df['MonthlyRent'] <= 10000)].copy()
    rows_after_filter = len(df)
    print(f"Dropped {rows_after_null - rows_after_filter:,} outlier rows (rent < €100 or > €10000)")

    df['AnnualRent']    = df['MonthlyRent'] * 12
    df['LocationType']  = df['Location'].apply(categorise_location)

    print(f"Final clean rows: {len(df):,}")
    return df


def extract_county_name(location):
    counties = [
        'Carlow', 'Cavan', 'Clare', 'Cork', 'Donegal', 'Dublin',
        'Galway', 'Kerry', 'Kildare', 'Kilkenny', 'Laois', 'Leitrim',
        'Limerick', 'Longford', 'Louth', 'Mayo', 'Meath', 'Monaghan',
        'Offaly', 'Roscommon', 'Sligo', 'Tipperary', 'Waterford',
        'Westmeath', 'Wexford', 'Wicklow',
    ]
    for county in counties:
        if county.lower() in location.lower():
            return county
    return location


def categorise_location(location):
    if 'City' in location:
        return 'City'
    elif 'Town' in location:
        return 'Town'
    elif 'Dublin' in location and any(c.isdigit() for c in location):
        return 'Dublin Postal'
    return 'Area'


if __name__ == "__main__":
    mongo_doc = extract_from_mongodb()
    if not mongo_doc:
        raise SystemExit("Failed to extract from MongoDB")

    df_rent  = transform_px_data_to_dataframe(mongo_doc)
    df_clean = clean_rent_data(df_rent)

    df_clean.to_csv('../data/rent_cleaned.csv', index=False)
    print("Saved to rent_cleaned.csv")

    print(f"Years: {df_clean['Year'].min()} - {df_clean['Year'].max()}")
    print(f"Counties: {df_clean['County'].nunique()}")
    print(f"Avg monthly rent: €{df_clean['MonthlyRent'].mean():.2f}")
    print("Step 2 done. Data cleaned and saved to CSV.")
