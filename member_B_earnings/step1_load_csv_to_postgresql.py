# Step 1: Load earnings CSV into PostgreSQL
import pandas as pd

from config import get_postgres_connection


def load_earnings_csv(filepath='../data/earnings.csv'):
    print(f"Loading: {filepath}")
    df = pd.read_csv(filepath, encoding='utf-8-sig')
    print(f"Rows: {len(df)}, Columns: {list(df.columns)}")
    return df


def clean_earnings_data(df):
    df = df.copy()

    # Standardise county names so they match the rent dataset
    df['County'] = df['County'].str.replace('Co. ', '', regex=False)
    df['County'] = df['County'].replace('Dublin City and Suburbs', 'Dublin')

    # Cast Year safely - drop any rows with invalid years
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce').astype('Int64')

    # Cast VALUE (weekly earnings) safely
    df['VALUE'] = pd.to_numeric(df['VALUE'], errors='coerce')

    rows_before = len(df)
    df = df.dropna(subset=['VALUE', 'Year'])
    print(f"Dropped {rows_before - len(df):,} rows with missing/invalid Year or VALUE")

    # Derive monthly and annual from weekly. Use annual = weekly * 52 as the
    # base, then monthly = annual / 12 so that monthly * 12 == annual exactly.
    df['AnnualEarnings']  = df['VALUE'] * 52
    df['MonthlyEarnings'] = df['AnnualEarnings'] / 12

    df = df.rename(columns={'Statistic Label': 'StatisticType', 'VALUE': 'WeeklyEarnings'})
    print(f"Cleaned rows: {len(df)}")
    return df


def create_earnings_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS earnings_data (
            id               SERIAL PRIMARY KEY,
            statistic_type   VARCHAR(100),
            year             INTEGER,
            county           VARCHAR(50),
            sex              VARCHAR(20),
            unit             VARCHAR(20),
            weekly_earnings  DECIMAL(10,2),
            monthly_earnings DECIMAL(10,2),
            annual_earnings  DECIMAL(10,2),
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_earnings_year   ON earnings_data(year);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_earnings_county ON earnings_data(county);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_earnings_sex    ON earnings_data(sex);")
    conn.commit()
    cursor.close()
    print("Table and indexes created")


def load_to_postgresql(df, conn):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM earnings_data;")

    records = [
        (row['StatisticType'], int(row['Year']), row['County'], row['Sex'],
         row['UNIT'], float(row['WeeklyEarnings']),
         float(row['MonthlyEarnings']), float(row['AnnualEarnings']))
        for _, row in df.iterrows()
    ]

    cursor.executemany("""
        INSERT INTO earnings_data
            (statistic_type, year, county, sex, unit,
             weekly_earnings, monthly_earnings, annual_earnings)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, records)

    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM earnings_data;")
    print(f"Inserted {cursor.fetchone()[0]} records")
    cursor.close()


def create_summary_views(conn):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE OR REPLACE VIEW avg_earnings_by_county_year AS
        SELECT county, year,
               ROUND(AVG(weekly_earnings),  2) AS avg_weekly_earnings,
               ROUND(AVG(monthly_earnings), 2) AS avg_monthly_earnings,
               ROUND(AVG(annual_earnings),  2) AS avg_annual_earnings
        FROM earnings_data
        WHERE sex = 'Both sexes'
        GROUP BY county, year
        ORDER BY county, year;
    """)

    cursor.execute("""
        CREATE OR REPLACE VIEW latest_earnings_by_county AS
        SELECT county, year, sex,
               ROUND(AVG(monthly_earnings), 2) AS avg_monthly_earnings,
               ROUND(AVG(annual_earnings),  2) AS avg_annual_earnings
        FROM earnings_data
        WHERE year = (SELECT MAX(year) FROM earnings_data)
          AND sex = 'Both sexes'
        GROUP BY county, year, sex
        ORDER BY avg_monthly_earnings DESC;
    """)

    cursor.execute("""
        CREATE OR REPLACE VIEW gender_pay_gap AS
        SELECT county, year,
               ROUND(AVG(CASE WHEN sex='Male'   THEN monthly_earnings END), 2) AS male_earnings,
               ROUND(AVG(CASE WHEN sex='Female' THEN monthly_earnings END), 2) AS female_earnings,
               ROUND(AVG(CASE WHEN sex='Male'   THEN monthly_earnings END) -
                     AVG(CASE WHEN sex='Female' THEN monthly_earnings END), 2) AS pay_gap,
               ROUND((AVG(CASE WHEN sex='Male'  THEN monthly_earnings END) -
                      AVG(CASE WHEN sex='Female' THEN monthly_earnings END)) /
                      AVG(CASE WHEN sex='Male'  THEN monthly_earnings END) * 100, 2) AS gap_percentage
        FROM earnings_data
        WHERE sex IN ('Male', 'Female')
        GROUP BY county, year
        ORDER BY county, year;
    """)

    conn.commit()
    cursor.close()
    print("Views created")


if __name__ == "__main__":
    df = load_earnings_csv()
    df_clean = clean_earnings_data(df)

    conn = get_postgres_connection()
    print("Connected to PostgreSQL")
    create_earnings_table(conn)
    load_to_postgresql(df_clean, conn)
    create_summary_views(conn)
    conn.close()

    print("Step 1 done. CSV loaded into PostgreSQL with summary views created.")
