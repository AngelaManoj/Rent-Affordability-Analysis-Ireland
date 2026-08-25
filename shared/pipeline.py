# HOW TO RUN:
# Option A (simple): cd shared && python pipeline.py
# Option B (with web UI at localhost:4200): Terminal 1: prefect server start | Terminal 2: cd shared && python pipeline.py

import subprocess
import sys
from pathlib import Path
from prefect import flow, task, get_run_logger



BASE_DIR = Path(__file__).parent.parent


def run_script(script_path: str, working_dir: str):
    """Run a Python script from its own working directory."""
    logger = get_run_logger()
    logger.info(f"Running: {script_path}")

    result = subprocess.run(
        [sys.executable, script_path],
        cwd=working_dir,
        capture_output=True,
        text=True
    )

    if result.stdout:
        logger.info(result.stdout)
    if result.stderr:
        logger.warning(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"Script failed: {script_path}\n"
            f"STDERR: {result.stderr}"
        )


#Task 0: Setup Databases 

@task(name="Setup Databases", retries=1, retry_delay_seconds=10)
def setup_databases():
    """
    Checks MongoDB and PostgreSQL are running.
    Creates the rent_affordability database if it doesn't exist.
    """
    run_script(
        script_path=str(BASE_DIR / 'databases' / 'setup_databases.py'),
        working_dir=str(BASE_DIR / 'databases')
    )


#Task 1A: Parse .px to MongoDB

@task(name="Member A - Parse PX to MongoDB", retries=1, retry_delay_seconds=10)
def parse_px_to_mongodb():
    """
    Member A Step 1:
    Reads the raw rent.px PC-Axis file using regex,
    extracts metadata and data values,
    stores everything in MongoDB in 5000-value chunks.
    """
    run_script(
        script_path=str(BASE_DIR / 'member_A_rent' / 'step1_parse_px_to_mongodb.py'),
        working_dir=str(BASE_DIR / 'member_A_rent')
    )


#Task 2A: Extract from MongoDB, clean, save CSV 

@task(name="Member A - Extract and Clean", retries=1, retry_delay_seconds=10)
def extract_and_clean():
    """
    Member A Step 2:
    Retrieves all chunks from MongoDB,
    reassembles the flat data array,
    reconstructs rows by Quarter x Bedrooms x PropertyType x Location,
    drops nulls and outliers (rent < €100 or > €10,000),
    saves to rent_cleaned.csv.
    """
    run_script(
        script_path=str(BASE_DIR / 'member_A_rent' / 'step2_extract_and_clean.py'),
        working_dir=str(BASE_DIR / 'member_A_rent')
    )


#Task 3A: Load rent data to PostgreSQL

@task(name="Member A - Load Rent to PostgreSQL", retries=1, retry_delay_seconds=10)
def load_rent_to_postgresql():
    """
    Member A Step 3:
    Reads rent_cleaned.csv,
    creates rent_data table with indexes on year, county, quarter,
    bulk inserts all records using executemany,
    creates 3 summary SQL views.
    """
    run_script(
        script_path=str(BASE_DIR / 'member_A_rent' / 'step3_load_to_postgresql.py'),
        working_dir=str(BASE_DIR / 'member_A_rent')
    )


#Task 1B: Load earnings CSV to PostgreSQL

@task(name="Member B - Load Earnings to PostgreSQL", retries=1, retry_delay_seconds=10)
def load_earnings_to_postgresql():
    """
    Member B Step 1:
    Reads earnings.csv,
    standardises county names (removes Co. prefix),
    casts Year and VALUE safely,
    derives monthly = annual / 12,
    creates earnings_data table with indexes,
    inserts all records,
    creates 3 summary SQL views including gender pay gap view.
    """
    run_script(
        script_path=str(BASE_DIR / 'member_B_earnings' / 'step1_load_csv_to_postgresql.py'),
        working_dir=str(BASE_DIR / 'member_B_earnings')
    )


#Task 2 Shared: Merge and Analyse

@task(name="Shared - Merge and Analyse", retries=1, retry_delay_seconds=10)
def merge_and_analyse():
    """
    Shared Step 1:
    Joins rent_data and earnings_data in PostgreSQL by county and year,
    computes rent-to-income ratio = (monthly_rent / monthly_earnings) x 100,
    categorises as Affordable (<30%), Burdened (30-50%), Severely Burdened (>50%),
    saves to rent_affordability_analysis table and CSV.
    """
    run_script(
        script_path=str(BASE_DIR / 'shared' / 'merge_and_analyze.py'),
        working_dir=str(BASE_DIR / 'shared')
    )


#Task 3 Shared: Create Visualisations

@task(name="Shared - Create Visualisations", retries=1, retry_delay_seconds=10)
def create_visualisations():
    """
    Shared Step 2:
    Reads from rent_affordability_analysis table,
    generates 8 charts:
      - Member A: rent trends, rent distribution
      - Member B: earnings trends, earnings distribution
      - Shared: affordability trends, heatmap, scatter, categories
    Saves all to visualizations/ folder as PNG files.
    """
    run_script(
        script_path=str(BASE_DIR / 'shared' / 'create_visualizations.py'),
        working_dir=str(BASE_DIR / 'shared')
    )


#Main Flow 

@flow(
    name="Rent Affordability ETL Pipeline",
    description=(
        "Full ETL pipeline for Irish rent affordability analysis. "
        "Processes RTB rent data (.px) and CSO earnings data (.csv), "
        "stores in MongoDB and PostgreSQL, merges datasets, "
        "computes rent-to-income ratios, and generates visualisations."
    ),
    log_prints=True,
)
def rent_affordability_pipeline():
    """
    Master flow that runs all tasks in the correct order.

    Pipeline order:
        setup_databases
              ↓                    ↓
        parse_px_to_mongodb   load_earnings_to_postgresql  (parallel)
              ↓
        extract_and_clean
              ↓
        load_rent_to_postgresql
              ↓                    ↓
              └─── merge_and_analyse ───┘
                          ↓
               create_visualisations
    """
    logger = get_run_logger()
    logger.info("Starting Rent Affordability ETL Pipeline")
    logger.info(f"Project root: {BASE_DIR}")

    # Step 0: Setup — must run first
    logger.info("Step 0: Setting up databases")
    setup_databases()

    # Step 1: Member A and Member B run independently after setup
    # Member A: parse raw .px file into MongoDB
    logger.info("Step 1A: Parsing PX file to MongoDB (Member A)")
    parse_px_to_mongodb()

    # Member B: load earnings CSV to PostgreSQL
    # This runs after setup but doesn't depend on Member A
    logger.info("Step 1B: Loading earnings CSV to PostgreSQL (Member B)")
    load_earnings_to_postgresql()

    # Step 2A: Member A continues - extract from MongoDB and clean
    logger.info("Step 2A: Extracting from MongoDB and cleaning (Member A)")
    extract_and_clean()

    # Step 3A: Member A loads cleaned data to PostgreSQL
    logger.info("Step 3A: Loading cleaned rent data to PostgreSQL (Member A)")
    load_rent_to_postgresql()

    # Step 2 Shared: Both datasets now in PostgreSQL - merge and analyse
    logger.info("Step 2 Shared: Merging datasets and calculating affordability ratios")
    merge_and_analyse()

    # Step 3 Shared: Generate all visualisations
    logger.info("Step 3 Shared: Generating visualisations")
    create_visualisations()

    logger.info("Pipeline complete! All tasks finished successfully.")
    logger.info(f"Visualisations saved to: {BASE_DIR / 'visualizations'}")
    logger.info(f"Analysis CSV saved to: {BASE_DIR / 'data' / 'rent_affordability_analysis.csv'}")


#Run

if __name__ == "__main__":
    # Run once immediately
    rent_affordability_pipeline()
