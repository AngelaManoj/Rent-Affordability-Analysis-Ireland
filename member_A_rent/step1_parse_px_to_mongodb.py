# Step 1: Parse the .px file and store raw data in MongoDB
import re
from datetime import datetime

from config import get_mongo_client, MONGO_DATABASE


def parse_px_file(filepath):
    print(f"Reading: {filepath}")

    # The file has a UTF-8 BOM despite declaring charset UTF-16
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    metadata = {
        'title':          extract_value(content, 'TITLE'),
        'description':    extract_value(content, 'DESCRIPTION'),
        'units':          extract_value(content, 'UNITS'),
        'last_updated':   extract_value(content, 'LAST-UPDATED'),
        'matrix':         extract_value(content, 'MATRIX'),
        'quarters':       extract_list_values(content, 'Quarter'),
        'bedrooms':       extract_list_values(content, 'Number of Bedrooms'),
        'property_types': extract_list_values(content, 'Property Type'),
        'locations':      extract_list_values(content, 'Location'),
    }

    print(f"Quarters: {len(metadata['quarters'])}, Bedrooms: {len(metadata['bedrooms'])}, "
          f"Property types: {len(metadata['property_types'])}, Locations: {len(metadata['locations'])}")

    expected = (len(metadata['quarters']) * len(metadata['bedrooms']) *
                len(metadata['property_types']) * len(metadata['locations']))
    print(f"Expected data points: {expected:,}")

    data_section = re.search(r'DATA=\s*(.*?);', content, re.DOTALL)
    if data_section:
        data_values = [v.strip('"') for v in data_section.group(1).split()]
        print(f"Data values found: {len(data_values):,}")
    else:
        data_values = []

    if len(data_values) != expected:
        print(f"WARNING: data values ({len(data_values)}) != expected ({expected})")

    return {
        'metadata': metadata,
        'data_values': data_values,
        'total_records': len(data_values),
    }


def extract_value(content, key):
    match = re.search(f'{key}="(.*?)"', content)
    return match.group(1) if match else None


def extract_list_values(content, key):
    pattern = f'VALUES\\("{key}"\\)=(.*?);'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return re.findall(r'"(.*?)"', match.group(1))
    return []


def store_in_mongodb(data, collection_name='raw_rent_data'):
    print("Connecting to MongoDB...")

    try:
        client = get_mongo_client()
        db = client[MONGO_DATABASE]
        collection = db[collection_name]

        # Clear any previous run
        collection.delete_many({})

        metadata_col = db['rent_metadata']
        metadata_col.delete_many({})
        metadata_col.insert_one({
            'imported_at':    datetime.now(),
            'source':         'RTB Rent Report (RIQ02)',
            'format':         'PC-Axis (.px)',
            'quarters':       data['metadata']['quarters'],
            'bedrooms':       data['metadata']['bedrooms'],
            'property_types': data['metadata']['property_types'],
            'locations':      data['metadata']['locations'],
            'total_records':  data['total_records'],
        })

        # Store data in chunks of 5000 values each (avoids 16MB BSON document limit)
        chunk_size = 5000
        total = len(data['data_values'])
        num_chunks = 0

        for start in range(0, total, chunk_size):
            chunk = data['data_values'][start:start + chunk_size]
            collection.insert_one({
                'source':             'RTB Rent Report (RIQ02)',
                'imported_at':        datetime.now(),
                'chunk_index':        start // chunk_size,
                'start_global_index': start,
                'chunk_size':         len(chunk),
                'raw_data_values':    chunk,
            })
            num_chunks += 1

        print(f"Stored {total:,} values across {num_chunks} chunks in MongoDB")
        client.close()
        return True

    except Exception as e:
        print(f"MongoDB error: {e}")
        return False


if __name__ == "__main__":
    parsed = parse_px_file('../data/rent.px')

    if store_in_mongodb(parsed):
        print("Step 1 done. Data stored in MongoDB.")
    else:
        print("Step 1 failed. Check MongoDB connection.")
