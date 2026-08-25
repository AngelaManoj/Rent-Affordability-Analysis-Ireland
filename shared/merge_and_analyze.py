# Step 4: Merge rent and earnings data, analyze affordability, and save results
import pandas as pd

from config import get_postgres_connection


def get_rent_data(conn):
    query = """
        SELECT county, year,
               ROUND(AVG(monthly_rent), 2) AS avg_monthly_rent
        FROM rent_data
        WHERE bedrooms = 'All bedrooms'
          AND property_type = 'All property types'
        GROUP BY county, year
        ORDER BY county, year
    """
    df = pd.read_sql_query(query, conn)
    print(f"Rent records: {len(df)} ({df['year'].min()}-{df['year'].max()})")
    return df


def get_earnings_data(conn):
    query = """
        SELECT county, year,
               ROUND(AVG(monthly_earnings), 2) AS avg_monthly_earnings
        FROM earnings_data
        WHERE sex = 'Both sexes'
          AND county <> 'Ireland'
        GROUP BY county, year
        ORDER BY county, year
    """
    df = pd.read_sql_query(query, conn)
    print(f"Earnings records: {len(df)} ({df['year'].min()}-{df['year'].max()})")
    return df


def merge_datasets(df_rent, df_earnings):
    # Compare year ranges
    rent_years = set(df_rent['year'].unique())
    earn_years = set(df_earnings['year'].unique())
    overlap    = sorted(rent_years & earn_years)

    only_rent = sorted(rent_years - earn_years)
    only_earn = sorted(earn_years - rent_years)
    if only_rent:
        print(f"Years in rent only (dropped): {only_rent}")
    if only_earn:
        print(f"Years in earnings only (dropped): {only_earn}")
    print(f"Overlapping years: {overlap[0]}-{overlap[-1]}")

    # Compare county sets
    rent_counties = set(df_rent['county'].unique())
    earn_counties = set(df_earnings['county'].unique())

    only_rent_c = sorted(rent_counties - earn_counties)
    only_earn_c = sorted(earn_counties - rent_counties)
    if only_rent_c:
        print(f"Counties in rent only (dropped): {only_rent_c}")
    if only_earn_c:
        print(f"Counties in earnings only (dropped): {only_earn_c}")

    # Inner join drops year/county combinations where one dataset has no counterpart
    df = pd.merge(df_rent, df_earnings, on=['county', 'year'], how='inner')
    df = df.dropna(subset=['avg_monthly_rent', 'avg_monthly_earnings'])
    print(f"Merged: {len(df)} records, {df['county'].nunique()} counties")
    return df


def calculate_affordability(df):
    df = df.copy()
    df['rent_to_income_ratio'] = (df['avg_monthly_rent'] / df['avg_monthly_earnings']) * 100

    # Standard housing affordability thresholds:
    #   Under 30% = Affordable
    #   30 - 50%  = Burdened
    #   Over 50%  = Severely Burdened
    # include_lowest=True so a value of exactly 0 doesn't become NaN
    df['affordability_category'] = pd.cut(
        df['rent_to_income_ratio'],
        bins=[0, 30, 50, 1000],
        labels=['Affordable', 'Burdened', 'Severely Burdened'],
        include_lowest=True,
    )

    print("\nRent-to-income ratio summary:")
    print(df['rent_to_income_ratio'].describe().round(2))
    print("\nAffordability distribution:")
    print(df['affordability_category'].value_counts())
    return df


def save_to_postgresql(df, conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rent_affordability_analysis (
            id                     SERIAL PRIMARY KEY,
            county                 VARCHAR(50),
            year                   INTEGER,
            avg_monthly_rent       DECIMAL(10,2),
            avg_monthly_earnings   DECIMAL(10,2),
            rent_to_income_ratio   DECIMAL(10,2),
            affordability_category VARCHAR(50),
            created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(county, year)
        );
    """)
    cursor.execute("DELETE FROM rent_affordability_analysis;")

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO rent_affordability_analysis
                (county, year, avg_monthly_rent, avg_monthly_earnings,
                 rent_to_income_ratio, affordability_category)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            row['county'], int(row['year']),
            float(row['avg_monthly_rent']), float(row['avg_monthly_earnings']),
            float(row['rent_to_income_ratio']),
            str(row['affordability_category']) if pd.notna(row['affordability_category']) else None,
        ))

    conn.commit()
    cursor.close()
    print(f"Saved {len(df)} records to rent_affordability_analysis")


def print_summary(df):
    latest = df['year'].max()
    df_latest = df[df['year'] == latest]

    print(f"\nLatest year: {latest}")
    print(f"\nTop 5 most affordable counties:")
    print(df_latest.nsmallest(5, 'rent_to_income_ratio')[
        ['county', 'rent_to_income_ratio', 'avg_monthly_rent', 'avg_monthly_earnings']
    ].to_string(index=False))

    print(f"\nTop 5 least affordable counties:")
    print(df_latest.nlargest(5, 'rent_to_income_ratio')[
        ['county', 'rent_to_income_ratio', 'avg_monthly_rent', 'avg_monthly_earnings']
    ].to_string(index=False))

    print(f"\nNational avg ratio ({latest}): {df_latest['rent_to_income_ratio'].mean():.2f}%")

    df_dublin = df[df['county'] == 'Dublin'].sort_values('year')
    if len(df_dublin) > 1:
        s, e = df_dublin.iloc[0], df_dublin.iloc[-1]
        print(f"\nDublin: {int(s['year'])}: {s['rent_to_income_ratio']:.2f}% "
              f"-> {int(e['year'])}: {e['rent_to_income_ratio']:.2f}%")


if __name__ == "__main__":
    conn = get_postgres_connection()
    print("Connected to PostgreSQL")

    df_rent     = get_rent_data(conn)
    df_earnings = get_earnings_data(conn)
    df_merged   = merge_datasets(df_rent, df_earnings)
    df_analysis = calculate_affordability(df_merged)

    save_to_postgresql(df_analysis, conn)
    df_analysis.to_csv('../data/rent_affordability_analysis.csv', index=False)

    print_summary(df_analysis)
    conn.close()
    print("\nAnalysis complete.")
