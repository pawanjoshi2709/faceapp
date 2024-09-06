import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('instance/database.db')
c = conn.cursor()

# Fetch all table names
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = c.fetchall()

# Print all table names
print("Tables in the database:")
for table in tables:
    print(table[0])

# Print schema for each table
for table in tables:
    print(f"\nSchema for table {table[0]}:")
    c.execute(f"PRAGMA table_info({table[0]});")
    schema = c.fetchall()
    for column in schema:
        print(column)

# Close the connection
conn.close()
