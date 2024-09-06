import sqlite3
from flask import flash ,send_file, redirect, url_for
from io import BytesIO
from PIL import Image
import pandas as pd
import plotly.express as px
import plotly.io as pio
from datetime import datetime
from model import save_face,load_encodings,is_unknown_face_in_database,log_recognition, is_encoding_in_database
import face_recognition
import re


import logging
logging.basicConfig(level=logging.DEBUG)


import time
import io
import base64
import cv2
import numpy as np
import bcrypt




def fetch_faces(sort_order='all'):
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    if sort_order == 'latest':
        c.execute('SELECT id, name FROM faces ORDER BY id DESC')
    else:
        c.execute('SELECT id, name FROM faces ORDER BY id ASC')
    faces = c.fetchall()
    conn.close()
    return faces





def get_db_connection_login():
    conn = sqlite3.connect('instance/database.db')  
    conn.row_factory = sqlite3.Row
    return conn





def fetch_data(state):
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    c.execute('SELECT city, COUNT(*) FROM faces WHERE state = ? GROUP BY city', (state,))
    data = c.fetchall()
    conn.close()
    return data





def fetch_recognition_logs(face_id):
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    c.execute('SELECT date, name,start_time,last_recorded_time FROM recognition_logs WHERE face_id = ?', (face_id,))
    logs = c.fetchall()
    conn.close()
    return logs








def validate_phone_number(phone_number):
    # Return True if phone_number is None or matches the regex pattern
    return phone_number is None or re.fullmatch(r'\d{10}', phone_number) is not None





def validate_email(email):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.fullmatch(email_regex, email) is not None





def fetch_image(face_id):
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    c.execute('SELECT image FROM faces WHERE id = ?', (face_id,))
    data = c.fetchone()
    conn.close()
    if data:
        image_data = data[0]
        image = Image.open(BytesIO(image_data))
        return image
    else:
        return None
    





def plot_day_chart(logs, selected_date):
    # Convert logs to a DataFrame
    df = pd.DataFrame(logs, columns=['id', 'face_id', 'name', 'date', 'start_time', 'total_time', 'last_recorded_time'])
    
    # Ensure 'date' column is in datetime format
    df['date'] = pd.to_datetime(df['date'])
    
    # Convert selected_date to datetime with time set to midnight
    selected_date = pd.to_datetime(selected_date).normalize()
    
    # Debug: Print the DataFram
    
    # Filter logs for the selected date
    df_selected = df[df['date'].dt.normalize() == selected_date]
    
   
    
    # If there are no records for the selected date, return an empty chart or a message
    if df_selected.empty:
        return "<p>No records found for the selected date.</p>"

    # Create a DataFrame with the count of logs
    day_counts = df_selected.groupby('date').size().reset_index(name='count')
    
   
    
    # Create a bar chart
    fig = px.bar(day_counts, 
                 x='date', 
                 y='count', 
                 title=f'Attendance Count on {selected_date.strftime("%Y-%m-%d")}',
                 labels={'date': 'Date', 'count': 'Log Count'},
                 text='count')

    # Update the layout for better hover information
    fig.update_traces(texttemplate='%{text}', textposition='outside', hovertemplate='Total log count by region and day : %{text}<extra></extra>')
    fig.update_layout(yaxis_title='Count', xaxis_title='Date')

    # Return the chart as HTML
    return pio.to_html(fig, full_html=False)





def get_head_password():
    password = 'Z1x2c3v4'
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    return hashed_password




def fetch_recognition_logs_day(date, country=None, state=None, city=None):
    # Ensure date is a string in 'YYYY-MM-DD' format
    

    
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
    
    # Add filters based on the provided arguments
    if country:
        query += ' AND f.country = ?'
        params.append(country)
    if state:
        query += ' AND f.state = ?'
        params.append(state)
    if city:
        query += ' AND f.city = ?'
        params.append(city)

  

    try:
        cur.execute(query, params)
        logs = cur.fetchall()
    except sqlite3.Error as e:
        logs = []

    conn.close()
    return logs





def insert_userlogin(gmail, c):
    # Generate password
    password = f"userpassword{gmail}"

    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Insert into userlogin table
    try:
        c.execute('''
            INSERT INTO userlogin (gmail, password)
            VALUES (?, ?)
        ''', (gmail, hashed_password))

    except sqlite3.IntegrityError:
        logging.error("Error: Gmail already exists in the userlogin table.")




    
known_face_encodings, known_face_names, known_face_metadata = load_encodings()
recognized_unknown_faces = set()





def process_frame_data(image_bytes):
    known_face_encodings, known_face_names, known_face_metadata = load_encodings()
    try:
        if not image_bytes:
            raise ValueError("No image data provided")


        # Attempt to open and verify the image
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.verify()  # Verify that image is valid
            image = Image.open(io.BytesIO(image_bytes))  # Reopen image after verification
        except (IOError, ValueError) as e:
            raise ValueError("Image data is not a valid image") from e

    

        # Convert to RGB format
        image = image.convert('RGB')
        frame = np.array(image)
       

        # Resize for face recognition
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = small_frame[:, :, ::-1]  # Convert BGR to RGB

        # Face recognition
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

  

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            

            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            name = "Unknown"

            if True in matches:
                first_match_index = matches.index(True)
                name = known_face_names[first_match_index]
                face_id, _, _ = known_face_metadata[first_match_index]
                # Assuming log_recognition is defined elsewhere
                log_recognition(face_id, name, is_known=True)
            else:
                face_encoding_tuple = tuple(face_encoding)
                if face_encoding_tuple not in recognized_unknown_faces:
                    # Assuming save_face is defined elsewhere
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    save_face('Unknown', 'Unknown', face_encoding, frame_bgr)
                    time.sleep(3)
                    log_recognition(None, 'Unknown', is_known=False)
                    recognized_unknown_faces.add(face_encoding_tuple)
                    
            # Draw bounding box and label
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, f"{name}", (left, bottom + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

        # Convert the frame to BGR format
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Encode the processed frame
        success, buffer = cv2.imencode('.jpg', frame_bgr)
        if not success:
            raise ValueError("Failed to encode image")
        
        # Convert to Base64
        processed_frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return processed_frame_base64

    except Exception as e:
        logging.error(f"Error processing frame: {e}")
        return ''




def check_user_credentials(email, password):
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    
    # Retrieve the hashed password for the given email
    c.execute('SELECT password FROM userlogin WHERE gmail = ?', (email,))
    result = c.fetchone()
    
    if result:
        hashed_password = result[0]
        # Verify the password
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
            return True
    
    return False





def query_face_by_email(email_id):
    try:
        # Query to retrieve the face_id and other details from the faces table using email_id
        conn = sqlite3.connect('faces.db')
        cursor = conn.cursor()
        
        # Fetch the face record for the provided email_id
        cursor.execute("SELECT id FROM faces WHERE email_id = ?", (email_id,))
        face = cursor.fetchone()
       
        conn.close()
       
        if face:
            return  face[0]
        else:
            return None
    except Exception as e:
        logging.error(f"Error fetching face record by email: {e}")
        return None





def plot_charts(logs, selected_month=None, selected_year=None, start_year=None, end_year=None):
    df = pd.DataFrame(logs, columns=['date', 'name', 'last_recorded_time', 'start_time'])
    df['date'] = pd.to_datetime(df['date'])
    

    # Extract hour from 'start_time'
    df['day'] = df['date'].dt.day
    df['month'] = df['date'].dt.strftime('%b')
    df['year'] = df['date'].dt.year

    # Day chart
    if selected_month:
        selected_date = datetime.strptime(selected_month, '%Y-%m')
    else:
        latest_month = df['date'].max().strftime('%Y-%m')
        selected_date = datetime.strptime(latest_month, '%Y-%m')

    days_in_month = pd.Period(year=selected_date.year, month=selected_date.month, freq='M').days_in_month
    day_counts = df[(df['date'].dt.month == selected_date.month) & (df['date'].dt.year == selected_date.year)]
    day_counts = day_counts.groupby('day').size().reindex(range(1, days_in_month + 1), fill_value=0).reset_index(name='count')
    day_count_fig = px.bar(day_counts, x='day', y='count', title=f'Present Counts by Day in {selected_date.strftime("%B %Y")}', labels={'day': 'Day', 'count': 'Present'})
    day_count_fig.update_layout(xaxis=dict(tickmode='linear'))  # Ensure each day is displayed
    day_chart_html = pio.to_html(day_count_fig, full_html=False)

    # Month chart
    if selected_year:
        year = int(selected_year)
    else:
        year = df['date'].max().year

    # Ensure all 12 months are included
    months = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-01', freq='MS').strftime('%b').tolist()
    month_counts = df[df['date'].dt.year == year]
    month_counts = month_counts.groupby('month').size().reindex(months, fill_value=0).reset_index(name='count')
    month_counts.rename(columns={'index': 'month'}, inplace=True)
    month_count_fig = px.bar(month_counts, x='month', y='count', title=f'Present Counts by Month in {year}', labels={'month': 'Month', 'count': 'Days Present'})
    month_count_fig.update_layout(xaxis=dict(tickmode='array', tickvals=months))  # Ensure all months are displayed
    month_chart_html = pio.to_html(month_count_fig, full_html=False)

    # Year chart
    if start_year and end_year:
        year_range = range(int(start_year), int(end_year) + 1)
    else:
        current_year = df['date'].max().year
        year_range = [current_year]

    year_counts = df[df['date'].dt.year.isin(year_range)]
    year_counts = year_counts.groupby('year').size().reindex(year_range, fill_value=0).reset_index(name='count')
    year_count_fig = px.bar(year_counts, x='year', y='count', title='Present Counts by Year', labels={'year': 'Year', 'count': 'Days Present'})
    year_chart_html = pio.to_html(year_count_fig, full_html=False)

    return {
        'day_chart_html': day_chart_html,
        'month_chart_html': month_chart_html,
        'year_chart_html': year_chart_html
    }




def update_password_user(user_email, old_password, new_password, confirm_new_password):
    # Connect to the database directly
    conn = sqlite3.connect('faces.db')
    conn.row_factory = sqlite3.Row
    
    try:
        # Get the current hashed password from the database
        user = conn.execute('SELECT password FROM userlogin WHERE gmail = ?', (user_email,)).fetchone()
        
        if not user:
            flash('User not found.', 'danger')
            return False

        hashed_password = user['password']  # Assuming this is already in bytes format
        
        # Check old password
        if not bcrypt.checkpw(old_password.encode('utf-8'), hashed_password):
            flash('Old password is incorrect.', 'danger')
            return False

        # Check if new passwords match
        if new_password != confirm_new_password:
            flash('New passwords do not match.', 'danger')
            return False

        # Hash the new password
        hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # Update the password in the database
        conn.execute('UPDATE userlogin SET password = ? WHERE gmail = ?', (hashed_new_password, user_email))
        conn.commit()

        flash('Password changed successfully.', 'success')
        return True

    except Exception as e:
        flash(f'An error occurred: {e}', 'danger')
        return False

    finally:
        conn.close()
    

    