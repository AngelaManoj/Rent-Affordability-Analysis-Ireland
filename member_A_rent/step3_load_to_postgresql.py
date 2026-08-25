# Step 3: Load cleaned data from CSV into PostgreSQL and create summary views
import pandas as pd

from config import get_postgres_connection


def load_from_csv(filepath='../data/rent_cleaned.csv'):
    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} rows from {filepath}")
    return df


def create_rent_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rent_data (
            id            SERIAL PRIMARY KEY,
            quarter       VARCHAR(10),
            year          INTEGER,
            quarter_num   INTEGER,
            bedrooms      VARCHAR(50),
            property_type VARCHAR(100),
            location      VARCHAR(200),
            county        VARCHAR(50),
            location_type VARCHAR(50),
            monthly_rent  DECIMAL(10,2),
            annual_rent   DECIMAL(10,2),
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rent_year    ON rent_data(year);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rent_county  ON rent_data(county);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rent_quarter ON rent_data(quarter);")
    conn.commit()
    cursor.close()
    print("Table and indexes created")


def load_to_postgresql(df, conn):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rent_data;")

    records = [
        (row['Quarter'], int(row['Year']), int(row['QuarterNum']),
         row['Bedrooms'], row['PropertyType'], row['Location'],
         row['County'], row['LocationType'],
         float(row['MonthlyRent']), float(row['AnnualRent']))
        for _, row in df.iterrows()
    ]

    cursor.executemany("""
        INSERT INTO rent_data
            (quarter, year, quarter_num, bedrooms, property_type,
             location, county, location_type, monthly_rent, annual_rent)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, records)

    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM rent_data;")
    print(f"Inserted {cursor.fetchone()[0]} records")
    cursor.close()


def create_summary_views(conn):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE OR REPLACE VIEW avg_rent_by_county_year AS
        SELECT county, year,
               ROUND(AVG(monthly_rent), 2) AS avg_monthly_rent,
               ROUND(AVG(annual_rent),  2) AS avg_annual_rent,
               COUNT(*) AS num_records
        FROM rent_data
        WHERE bedrooms = 'All bedrooms'
          AND property_type = 'All property types'
        GROUP BY county, year
        ORDER BY county, year;
    """)

    cursor.execute("""
        CREATE OR REPLACE VIEW latest_rent_by_county AS
        SELECT county, quarter, year,
               ROUND(AVG(monthly_rent), 2) AS avg_monthly_rent
        FROM rent_data
        WHERE bedrooms = 'All bedrooms'
          AND property_type = 'All property types'
          AND year = (SELECT MAX(year) FROM rent_data)
        GROUP BY county, quarter, year
        ORDER BY avg_monthly_rent DESC;
    """)

    cursor.execute("""
        CREATE OR REPLACE VIEW rent_by_property_type AS
        SELECT property_type, year,
               ROUND(AVG(monthly_rent), 2) AS avg_monthly_rent,
               COUNT(*) AS num_records
        FROM rent_data
        WHERE bedrooms = 'All bedrooms'
          AND property_type != 'All property types'
        GROUP BY property_type, year
        ORDER BY property_type, year;
    """)

    conn.commit()
    cursor.close()
    print("Views created")


if __name__ == "__main__":
    df_clean = load_from_csv()

    conn = get_postgres_connection()
    print("Connected to PostgreSQL")
    create_rent_table(conn)
    load_to_postgresql(df_clean, conn)
    create_summary_views(conn)
    conn.close()

    print("Step 3 done. Data loaded to PostgreSQL.")
