import sqlite3

def fetch_recognition_logs(date, country=None, state=None):
    # Connect to the SQLite database
    conn = sqlite3.connect('faces.db')
    cur = conn.cursor()

    # Base query
    query = '''
    SELECT rl.id, rl.face_id, f.name, rl.date, rl.start_time, rl.total_time, rl.last_recorded_time
    FROM recognition_logs rl
    JOIN faces f ON rl.face_id = f.id
    WHERE rl.date = ?
    '''
    params = [date]

    # Add filters based on provided arguments
    if country:
        query += ' AND f.country = ?'
        params.append(country)
    if state:
        query += ' AND f.state = ?'
        params.append(state)

    print("Query:", query)
    print("Parameters:", params)
    
    # Execute the query
    try:
        cur.execute(query, params)
        logs = cur.fetchall()  # Fetch all rows from the result
        print("Logs fetched:", logs)
    except sqlite3.Error as e:
        print("SQLite error:", e)
        logs = []
    finally:
        # Close the connection
        conn.close()

    return logs

# Example usage
if __name__ == "__main__":
    # Use a date in 'YYYY-MM-DD' format, and include country and state filters
    date = '2024-09-05'
    country = 'India'
    state = 'uk'
    logs = fetch_recognition_logs(date)
