import sqlite3

# Connect to your database
conn = sqlite3.connect('faces.db')  # Replace with your database file name
cursor = conn.cursor()

# SQL command to delete rows where name is 'pawan'
delete_rows_query = '''
DELETE FROM recognition_logs
WHERE name = 'pawan';
'''

try:
    # Execute the SQL command
    cursor.execute(delete_rows_query)
    conn.commit()
    print("Rows with name 'pawan' deleted successfully.")
except sqlite3.OperationalError as e:
    print(f"An error occurred: {e}")
finally:
    # Close the connection
    conn.close()
