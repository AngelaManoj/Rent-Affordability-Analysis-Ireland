SETUP INSTRUCTIONS

1. COPY THESE TWO FILES INTO EVERY SUBFOLDER

Copy config.py and .env into each of these folders:
  - databases/
  - member_A_rent/
  - member_B_earnings/
  - shared/

Every folder needs its own copy of both files.

Currently config.py is available only in databases folder only.
Need to copy and add along with.env file to the 4 folders mentioned above.

2. CREATE YOUR .env FILE

Create a file called exactly ".env" (no .txt) in each folder with your own PostgreSQL password:

    PG_HOST=localhost
    PG_PORT=5432
    PG_USER=postgres
    PG_PASSWORD=your_password_here
    PG_DATABASE=rent_affordability
    MONGO_URI=mongodb://localhost:27017/
    MONGO_DATABASE=rent_affordability

Each team member uses their own password on their own laptop.


3. HOW TO RUN THE SCRIPTS

    cd shared
    python pipeline.py
   



