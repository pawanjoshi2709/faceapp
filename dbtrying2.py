import sqlite3

# Connect to the existing database
conn = sqlite3.connect('faces.db')
c = conn.cursor()

# Step 1: Create a new table with the unique email_id column
print("Creating new table with unique email_id...")
c.execute('''
    CREATE TABLE IF NOT EXISTS faces_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobile_number_1 INTEGER,
        mobile_number_2 INTEGER,
        email_id TEXT UNIQUE,  -- Make the email_id column unique
        address TEXT,
        state TEXT,
        city TEXT,
        country TEXT,
        encoding BLOB,
        image BLOB
    )
''')
print("New table created.")

# Step 2: Copy the data from the old table to the new table
print("Copying data to the new table...")
c.execute('''
    INSERT INTO faces_new (id, name, mobile_number_1, mobile_number_2, email_id, address, state, city, country, encoding, image)
    SELECT id, name, mobile_number_1, mobile_number_2, email_id, address, state, city, country, encoding, image
    FROM faces
''')
print("Data copied successfully.")

# Step 3: Drop the old table
print("Dropping the old table...")
c.execute('DROP TABLE faces')
print("Old table dropped.")

# Step 4: Rename the new table to the original table name
print("Renaming the new table to 'faces'...")
c.execute('ALTER TABLE faces_new RENAME TO faces')
print("Table renamed successfully.")

# Commit and close the connection
conn.commit()
conn.close()
print("Database operation completed.")
