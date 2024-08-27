from flask import Flask, request,jsonify,Response,render_template, redirect,session, url_for ,send_file, flash,logging
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email

import pandas as pd
import plotly.express as px
import plotly.io as pio
import bcrypt
import sqlite3
import secrets
import base64
import cv2
import io
import face_recognition
from io import BytesIO
import numpy as np
import os
import json
from PIL import Image
from datetime import datetime
import pickle
from model import save_face,load_encodings,is_unknown_face_in_database,log_recognition, is_encoding_in_database
# Initialize the Flask application
from pyngrok import ngrok


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.secret_key = 'secret_key'
db = SQLAlchemy(app)
ngrok.set_auth_token('2j6yZx3KvVeSEOhGHG0bEjNdWB8_2ri6c36iDuZZxMJxxCD47')

known_face_encodings, known_face_names, known_face_metadata = load_encodings()
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

    def __init__(self, email, password, name):
        self.name = name
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

with app.app_context():
    db.create_all()


# Function to fetch faces from the database
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

def fetch_data(state):
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    c.execute('SELECT city, COUNT(*) FROM faces WHERE state = ? GROUP BY city', (state,))
    data = c.fetchall()
    conn.close()
    return data

import plotly.express as px
from flask import Markup

import plotly.express as px
import plotly.io as pio
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

import pandas as pd
import plotly.express as px
import plotly.io as pio











def fetch_recognition_logs(face_id):
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    c.execute('SELECT date, name,start_time,last_recorded_time FROM recognition_logs WHERE face_id = ?', (face_id,))
    logs = c.fetchall()
    conn.close()
    return logs

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

import pandas as pd
import plotly.express as px
import plotly.io as pio
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.io as pio
from datetime import datetime
from flask import request, render_template, flash, redirect, url_for

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

@app.route('/analyze/<int:face_id>', methods=['GET'])
def analyze_face(face_id):
    logs = fetch_recognition_logs(face_id)
    if logs:
        selected_month = request.args.get('day_month')
        selected_year = request.args.get('month_year')
        start_year = request.args.get('start_year')
        end_year = request.args.get('end_year')

        current_month = datetime.now().strftime('%Y-%m')
        current_year = datetime.now().year

        charts = plot_charts(
            logs,
            selected_month=selected_month,
            selected_year=selected_year,
            start_year=start_year,
            end_year=end_year
        )

        # Determine if the student is present today
        latest_log = logs[-1]  # Assuming logs are sorted
        latest_date = pd.to_datetime(latest_log[0])
        today = datetime.now().date()
        student_name = latest_log[1]  # Name of the student

        if latest_date.date() == today:
            if latest_log[3]:  # last_recorded_time
                presence_status = f"{student_name} is present today. Last recorded time: {latest_log[3]}"
            else:
                presence_status = f"{student_name} is present today. Last recorded time: {latest_log[2]}"
        else:
            if latest_log[3]:  # last_recorded_time
                presence_status = f"{student_name} is not present today. Last recorded time: {latest_log[3]}"
            else:
                presence_status = f"{student_name} is not present today. Last recorded time: {latest_log[2]}"

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                **charts,
                'presence_status': presence_status
            })

        return render_template('face_modal.html',
                               face_id=face_id,
                               day_chart_html=charts['day_chart_html'],
                               month_chart_html=charts['month_chart_html'],
                               year_chart_html=charts['year_chart_html'],
                               current_month=current_month,
                               current_year=current_year,
                               selected_month=selected_month,
                               selected_year=selected_year,
                               start_year=start_year,
                               end_year=end_year,
                               presence_status=presence_status)
    else:
        flash('No recognition logs found for the selected face.', 'warning')
        return redirect(url_for('analyze'))











# Define a route for the root URL ("/")
@app.route('/')
def index():
    return render_template('index.html')

from sqlalchemy.exc import IntegrityError
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Check if the email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address already exists. Please use a different email or log in.')
            return redirect(url_for('register'))

        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)

        try:
            db.session.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.')
            return redirect(url_for('register'))

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['email'] = user.email
            return redirect('/recognize')
        else:
            return render_template('login.html', error='Invalid user')

    return render_template('login.html')



@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect('/')


@app.route('/faces', methods=['GET'])
def display_faces():
    try:
        sort_order = request.args.get('sort_order', 'all')  # default to 'all' if not provided
        conn = sqlite3.connect('faces.db')
        c = conn.cursor()
        if sort_order == 'latest':
            c.execute('SELECT id, name, mobile_number_1, city FROM faces ORDER BY id DESC')
        else:
            c.execute('SELECT id, name, mobile_number_1, city FROM faces ORDER BY id ASC')
        faces = c.fetchall()
        conn.close()
        return render_template('faces.html', faces=faces, sort_order=sort_order)
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return render_template('faces.html', faces=[], sort_order='all')





@app.route('/delete/<int:face_id>', methods=['POST'])
def delete_face(face_id):
    try:
        conn = sqlite3.connect('faces.db')
        c = conn.cursor()
        c.execute('DELETE FROM faces WHERE id = ?', (face_id,))
        conn.commit()
        conn.close()
        flash('Face deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    return redirect(url_for('display_faces'))

@app.route('/modify/<int:face_id>')
def modify_face(face_id):
    try:
        conn = sqlite3.connect('faces.db')
        c = conn.cursor()
        c.execute('SELECT * FROM faces WHERE id = ?', (face_id,))
        face = c.fetchone()
        conn.close()
        if face:
            return render_template('modify.html', face=face)
        else:
            flash('Face not found.', 'error')
            return redirect(url_for('display_faces'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('display_faces'))

@app.route('/update/<int:face_id>', methods=['POST'])
def update_face(face_id):
    try:
        # Get form data
        name = request.form['name']
        mobile_number_1 = request.form['phone1']
        mobile_number_2 = request.form['phone2']
        email_id = request.form['email']
        address = request.form['address']
        state = request.form['state']
        city = request.form['city']
        country = request.form['country']
        
        # Connect to SQLite database
        conn = sqlite3.connect('faces.db')
        c = conn.cursor()
        
        # Update the faces table
        c.execute('''UPDATE faces 
                     SET name = ?, mobile_number_1 = ?, mobile_number_2 = ?, email_id = ?, 
                         address = ?, state = ?, city = ?, country = ? 
                     WHERE id = ?''', 
                  (name, mobile_number_1, mobile_number_2, email_id, address, state, city, country, face_id))
        
        # Update the recognition_logs table to reflect the name change
        c.execute('''UPDATE recognition_logs 
                     SET name = ? 
                     WHERE face_id = ?''', 
                  (name, face_id))
        
        # Commit changes and close the connection
        conn.commit()
        conn.close()
        
        flash('Face updated successfully.', 'success')
        return redirect(url_for('display_faces'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('modify_face', face_id=face_id))


@app.route('/image/<int:face_id>')
def serve_image(face_id):
    try:
        conn = sqlite3.connect('faces.db')
        c = conn.cursor()
        c.execute('SELECT image FROM faces WHERE id = ?', (face_id,))
        image_data = c.fetchone()
        conn.close()
        
        if image_data and image_data[0]:
            return send_file(
                io.BytesIO(image_data[0]),
                mimetype='image/jpeg',
                as_attachment=False,
                download_name=f'face_{face_id}.jpg'
            )
        else:
            flash('Image not found.', 'error')
            return redirect(url_for('display_faces'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('display_faces'))




@app.route('/update_chart', methods=['POST'])
def update_chart():
    selected_state = request.json.get('state')
    data = fetch_data(selected_state)
    df = pd.DataFrame(data, columns=['City', 'Count'])
    fig = px.pie(df, values='Count', names='City')
    fig.update_traces(textinfo='value', textfont_size=14)
    fig.update_layout(title_text='')
    graph_html = pio.to_html(fig, full_html=False)
    return jsonify({'graph_html': graph_html})

@app.route('/analyze', methods=['GET'])
def analyze():
    sort_order = request.args.get('sort_order', 'all')
    faces = fetch_faces(sort_order)
    return render_template('analyze.html', faces=faces, sort_order=sort_order)


import binascii
@app.route('/recognize')
def recognize():
    if 'email' not in session:
        return redirect('/login')
    return render_template('recogonize.html')

import logging
logging.basicConfig(level=logging.DEBUG)

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


@app.route('/process_frame', methods=['POST'])
def process_frame_endpoint():
  
    try:
        data = request.json
        frame_data = data.get('frame')

        if not frame_data:
           
            return jsonify({'message': 'No frame data provided'}), 400

     

        if not frame_data.startswith('data:image/jpeg;base64,'):
      
            return jsonify({'message': 'Frame data is not properly Base64 encoded'}), 400

        # Remove the prefix 'data:image/jpeg;base64,'
        frame_data = frame_data[len('data:image/jpeg;base64,'):]

        if not frame_data:
         
            return jsonify({'message': 'Frame data is empty after base64 split'}), 400

        # Decode Base64 to bytes
        try:
            image_bytes = base64.b64decode(frame_data)
        except (base64.binascii.Error, ValueError) as e:
   
            return jsonify({'message': 'Failed to decode Base64 frame data'}), 400

    
        if len(image_bytes) < 1000:
            logging.error('Decoded image data is too short')
            return jsonify({'message': 'Decoded image data is too short'}), 400

        processed_frame_base64 = process_frame_data(image_bytes)
        
        if not processed_frame_base64:
       
            return jsonify({'message': 'Error processing frame'}), 500

        return jsonify({'processed_frame': f"data:image/jpeg;base64,{processed_frame_base64}"})
    
    except Exception as e:
        logging.error(f"Unexpected error in /process_frame route: {e}")
        return jsonify({'message': 'Unexpected error occurred during frame processing'}), 500




# Run the application
if __name__ == '__main__':
    public_url = ngrok.connect(5000)
    print("Public URL:", public_url)
    app.run()