import bcrypt
import sqlite3

# Define the admin password
admin_password = 'adminpassword'

# Hash the password
hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())

# Connect to the SQLite database
conn = sqlite3.connect('instance/database.db')  # Change this to your database file
c = conn.cursor()

# Create the admin table if it doesn't exist
c.execute('''
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT
    )
''')

# Insert the hashed password into the table
c.execute('''
    INSERT OR REPLACE INTO admin (id, username, password)
    VALUES (1, 'admin', ?)
''', (hashed_password,))

# Commit the changes and close the connection
conn.commit()
conn.close()
