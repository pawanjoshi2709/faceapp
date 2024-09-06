from flask import Flask, request,jsonify,Response,render_template, redirect,session, url_for ,send_file, flash,logging
from flask_sqlalchemy import SQLAlchemy
from func import fetch_data, fetch_faces, fetch_image, fetch_recognition_logs,get_head_password, insert_userlogin, plot_charts ,process_frame_data,validate_email,validate_phone_number,check_user_credentials
from func import   query_face_by_email,update_password_user,fetch_recognition_logs_day,plot_day_chart,get_db_connection_login
import pandas as pd
import plotly.express as px
import plotly.io as pio
import bcrypt
import sqlite3
import base64
import io
from datetime import datetime

import logging
logging.basicConfig(level=logging.DEBUG)

from sqlalchemy.exc import IntegrityError
# Initialize the Flask application
from pyngrok import ngrok


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.secret_key = 'secret_key'

db = SQLAlchemy(app)

ngrok.set_auth_token('2j6yZx3KvVeSEOhGHG0bEjNdWB8_2ri6c36iDuZZxMJxxCD47')





class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        # Hash the password
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def set_password(self, new_password):
        # Hash the new password and save it
        self.password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))





@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if not validate_email(email):
            flash('Invalid email address. Please enter a valid email.')
            return redirect(url_for('register'))

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


with app.app_context():
    db.create_all()






@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        admin_password = request.form['admin_password']

        conn = get_db_connection_login()
        admin = conn.execute('SELECT password FROM admin WHERE id = 1').fetchone()
        conn.close()

        if admin and bcrypt.checkpw(admin_password.encode('utf-8'), admin['password']):
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                session['email'] = user.email
                return redirect('/recognize')
            else:
                flash('Invalid user email or password', 'error')
        else:
            flash('Invalid admin password', 'error')

    return render_template('login.html')






@app.route('/change_user_password', methods=['GET', 'POST'])
def change_user_password():
    if request.method == 'POST':
        email = request.form['email']
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('change_user_password.html')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(old_password):
            user.set_password(new_password)
            db.session.commit()
            flash('Password updated successfully', 'success')
            return redirect('/login')
        else:
            flash('Invalid email or old password', 'error')

    return render_template('change_user_password.html')





@app.route('/forgot_user_password', methods=['GET', 'POST'])
def forgot_user_password():
    if request.method == 'POST':
        email = request.form['email']
        head_password = request.form['head_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('forgot_user_password.html')

        # Get the hashed head password
        head_password1 = get_head_password()

        # Check if the entered admin password matches the hashed head password
        if bcrypt.checkpw(head_password.encode('utf-8'), head_password1.encode('utf-8')):
            user = User.query.filter_by(email=email).first()
            if user:
                user.set_password(new_password)
                db.session.commit()
                flash('Password reset successfully', 'success')
                return redirect('/login')
            else:
                flash('User with that email does not exist', 'error')
        else:
            flash('Invalid head password', 'error')

    return render_template('forgot_user_password.html')







@app.route('/change_admin_password', methods=['GET', 'POST'])
def change_admin_password():
    if request.method == 'POST':
        head_password = request.form['head_password']
        new_admin_password = request.form['new_admin_password']
        confirm_new_admin_password = request.form['confirm_new_admin_password']

        # Get the hashed head password
        stored_head_password = get_head_password()

        # Verify the provided head password
        if bcrypt.checkpw(head_password.encode('utf-8'), stored_head_password.encode('utf-8')):
            if new_admin_password != confirm_new_admin_password:
                flash('New passwords do not match', 'error')
            else:
                hashed_password = bcrypt.hashpw(new_admin_password.encode('utf-8'), bcrypt.gensalt())
                conn = get_db_connection_login()
                conn.execute('UPDATE admin SET password = ? WHERE id = 1', (hashed_password,))
                conn.commit()
                conn.close()
                flash('Admin password updated successfully', 'success')
                return redirect('/login')
        else:
            flash('Invalid head password', 'error')

    return render_template('change_admin_password.html')






@app.route('/analyze/<int:face_id>', methods=['GET'])
def analyze_face(face_id):
    if 'email' not in session:
        return redirect('/login')
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
    return render_template('home.html')





@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if check_user_credentials(email, password):
            session['user'] = email  # Store user email in session
            flash('Login successful!', 'success')
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    
    return render_template('user_login.html')





@app.route('/user/dashboard')
def user_dashboard():
    if 'user' not in session:
        return redirect(url_for('user_login'))
    user_email = session['user']
    face_id = query_face_by_email(user_email)
    if not face_id:
        flash('No face record found for this user.', 'warning')
        return redirect(url_for('user_login'))
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
        

        if latest_date.date() == today:
            if latest_log[3]:  # last_recorded_time
                presence_status = f"you are present today. Last recorded time: {latest_log[3]}"
            else:
                presence_status = f"you are  present today. Last recorded time: {latest_log[2]}"
        else:
            if latest_log[3]:  # last_recorded_time
                presence_status = f"you are  not present today. Last recorded time: {latest_log[3]}"
            else:
                presence_status = f"You are not present today. Last recorded time: {latest_log[2]}"

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                **charts,
                'presence_status': presence_status
            })

        return render_template('user_dashboard.html',
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
        flash('No recognition logs found/No History.', 'warning')
        return redirect(url_for('user_login'))






@app.route('/user/change_password', methods=['GET', 'POST'])
def user_change_password():
    if 'user' not in session:
        return redirect(url_for('user_login'))
    
    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_new_password = request.form['confirm_new_password']
        
        user_email = session['user']

        if update_password_user(user_email, old_password, new_password, confirm_new_password):
            return redirect(url_for('user_dashboard'))
        else:
            return redirect(url_for('user_change_password'))
    
    return render_template('user_change_password.html')







@app.route('/user/modify', methods=['GET', 'POST'])
def user_modify_face():
    if 'user' not in session:
        return redirect(url_for('user_login'))

    # Get user email from session
    user_email = session['user']
    
    # Get face_id associated with the user
    face_id = query_face_by_email(user_email)  # Assuming query_face_by_email is a function that fetches face_id by email

    if not face_id:
        flash('No face record found for this user.', 'warning')
        return redirect(url_for('user_login'))

    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name']
            mobile_number_1 = request.form['phone1']
            mobile_number_2 = request.form['phone2']
            address = request.form['address']
            state = request.form['state']
            city = request.form['city']
            country = request.form['country']

            # Validate phone numbers
            valid_phone_1 = validate_phone_number(mobile_number_1)
            valid_phone_2 = validate_phone_number(mobile_number_2)

            if mobile_number_1 and not valid_phone_1:
                flash('Phone Number 1 must be exactly 10 digits if provided or remove all characters.', 'error')
                return redirect(url_for('modify_face'))

            if mobile_number_2 and not valid_phone_2:
                flash('Phone Number 2 must be exactly 10 digits if provided or remove all characters.', 'error')
                return redirect(url_for('modify_face'))

            # Connect to SQLite database
            conn = sqlite3.connect('faces.db')
            c = conn.cursor()

            # Update the faces table
            c.execute('''UPDATE faces 
                         SET name = ?, 
                             mobile_number_1 = COALESCE(NULLIF(?, mobile_number_1), mobile_number_1), 
                             mobile_number_2 = COALESCE(NULLIF(?, mobile_number_2), mobile_number_2), 
                             address = ?, 
                             state = ?, 
                             city = ?, 
                             country = ? 
                         WHERE id = ?''', 
                      (name, mobile_number_1, mobile_number_2, address, state, city, country, face_id))

            # Update the recognition_logs table to reflect the name change
            c.execute('''UPDATE recognition_logs 
                         SET name = ? 
                         WHERE face_id = ?''', 
                      (name, face_id))

            # Commit changes and close the connection
            conn.commit()
            conn.close()

            flash('Face updated successfully.', 'success')
            return redirect(url_for('user_modify_face'))

        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('user_modify_face'))

    # Fetch existing face data to populate the form
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    c.execute('SELECT name, mobile_number_1, mobile_number_2,email_id, address, state, city, country FROM faces WHERE id = ?', (face_id,))
    face_data = c.fetchone()
    conn.close()

    # Render the form with existing face data
    return render_template('user_modify.html', face_data=face_data)





@app.route('/user/image')
def user_serve_image():
    if 'user' not in session:
        return redirect(url_for('user_login'))

    user_email = session['user']
    face_id = query_face_by_email(user_email)  # Fetch face_id by email

    if not face_id:
        flash('No face record found for this user.', 'warning')
        return redirect(url_for('user_login'))

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
            return redirect(url_for('user_modify_face'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('user_modify_face'))




@app.route('/user/logout')
def user_logout():
    # Clear the session
    session.pop('user', None)
    
    # Redirect to the login page
    return redirect(url_for('user_login'))





@app.route('/user/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        admin_password = request.form['admin_password']

        
        conn = get_db_connection_login()
        admin = conn.execute('SELECT password FROM admin WHERE id = 1').fetchone()
        conn.close()

        if admin and bcrypt.checkpw(admin_password.encode('utf-8'), admin['password']):
        # Verify the provided admin password
       
            conn = sqlite3.connect('faces.db')
            conn.row_factory = sqlite3.Row
            user = conn.execute('SELECT * FROM userlogin WHERE gmail = ?', (email,)).fetchone()

            if user:
                # Generate a new password
                new_password = f"userpassword{email}"

                # Hash the new password
                hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

                # Update the user's password in the database
                conn.execute('UPDATE userlogin SET password = ? WHERE gmail = ?', (hashed_password, email))
                conn.commit()
                conn.close()

                flash('Password has been reset successfully. Please check your email for the new password.', 'success')
                return redirect(url_for('user_login'))
            else:
                flash('Email not found in the system.', 'error')
                conn.close()
        else:
            flash('Invalid admin password.', 'error')

    return render_template('user_forgot_password.html')






@app.route('/day_dashboard', methods=['GET'])
def day_data_view():
    if 'email' not in session:
        return redirect('/login')
    selected_date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    selected_country = request.args.get('country')
    selected_state = request.args.get('state')
    selected_city = request.args.get('city')
  

    selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    
    # Fetch recognition logs based on selected filters
    logs = fetch_recognition_logs_day(selected_date_str, selected_country, selected_state, selected_city)


    # Generate chart
    day_chart_html = plot_day_chart(logs, selected_date)

    # Fetch unique countries from the faces table
    conn = sqlite3.connect('faces.db')
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT country FROM faces')
    countries = cur.fetchall()
    country_options = [country[0] for country in countries]
    

    # Fetch unique states if a country is selected
    if selected_country:
        cur.execute('SELECT DISTINCT state FROM faces WHERE country = ?', (selected_country,))
        states = cur.fetchall()
        state_options = [state[0] for state in states]
    else:
        state_options = []
  

    # Fetch unique cities if a state is selected
    if selected_state:
        cur.execute('SELECT DISTINCT city FROM faces WHERE state = ? AND country = ?', (selected_state, selected_country))
        cities = cur.fetchall()
        city_options = [city[0] for city in cities]
    else:
        city_options = []
    

    conn.close()

    # Render HTML template
    return render_template('day_data.html',
                           day_chart_html=day_chart_html,
                           selected_date=selected_date_str,
                           selected_country=selected_country,
                           selected_state=selected_state,
                           selected_city=selected_city,
                           country_options=country_options,
                           state_options=state_options,
                           city_options=city_options)





@app.route('/get_states', methods=['GET'])
def get_states():
    selected_country = request.args.get('country')
    conn = sqlite3.connect('faces.db')
    cur = conn.cursor()
    if selected_country:
        cur.execute('SELECT DISTINCT state FROM faces WHERE country = ?', (selected_country,))
        states = cur.fetchall()
        state_options = [state[0] for state in states]
    else:
        state_options = []
    conn.close()
    return jsonify(states=state_options)






@app.route('/get_cities', methods=['GET'])
def get_cities():
    selected_country = request.args.get('country')
    selected_state = request.args.get('state')
    conn = sqlite3.connect('faces.db')
    cur = conn.cursor()
    if selected_state and selected_country:
        cur.execute('SELECT DISTINCT city FROM faces WHERE state = ? AND country = ?', (selected_state, selected_country))
        cities = cur.fetchall()
        city_options = [city[0] for city in cities]
    else:
        city_options = []
    conn.close()
    return jsonify(cities=city_options)




@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect('/')





@app.route('/faces', methods=['GET'])
def display_faces():
    if 'email' not in session:
        return redirect('/login')
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
        # Connect to SQLite database
        conn = sqlite3.connect('faces.db')
        c = conn.cursor()

        # Get the email associated with the face_id from the faces table
        c.execute('SELECT email_id FROM faces WHERE id = ?', (face_id,))
        result = c.fetchone()
        
        if result:
            email_id = result[0]

            # Delete the face record from the faces table
            c.execute('DELETE FROM faces WHERE id = ?', (face_id,))
            
            # If email_id is present, delete the corresponding record from userlogin table
            if email_id:
                c.execute('DELETE FROM userlogin WHERE gmail = ?', (email_id,))

            conn.commit()
            flash('Face deleted successfully.', 'success')
        else:
            flash('Face not found.', 'error')

        conn.close()
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
        
        # Validate phone numbers and email
        valid_phone_1 = validate_phone_number(mobile_number_1)
        valid_phone_2 = validate_phone_number(mobile_number_2)
        valid_email = validate_email(email_id)
        
        if mobile_number_1 and not valid_phone_1:
            flash('Phone Number 1 must be exactly 10 digits if provided or remove all characters.', 'error')
            return redirect(url_for('modify_face', face_id=face_id))
        
        if mobile_number_2 and not valid_phone_2:
            flash('Phone Number 2 must be exactly 10 digits if provided or remove all characters.', 'error')
            return redirect(url_for('modify_face', face_id=face_id))
        
        if email_id and not valid_email:
            flash('Invalid email format.', 'error')
            return redirect(url_for('modify_face', face_id=face_id))

        # Connect to SQLite database
        conn = sqlite3.connect('faces.db')
        c = conn.cursor()

        # Get the old email from the faces table
        c.execute('SELECT email_id FROM faces WHERE id = ?', (face_id,))
        old_email = c.fetchone()[0]

        # Update the faces table
        c.execute('''UPDATE faces 
                     SET name = ?, 
                         mobile_number_1 = COALESCE(NULLIF(?, mobile_number_1), mobile_number_1), 
                         mobile_number_2 = COALESCE(NULLIF(?, mobile_number_2), mobile_number_2), 
                         email_id = COALESCE(NULLIF(?, email_id), email_id), 
                         address = ?, 
                         state = ?, 
                         city = ?, 
                         country = ? 
                     WHERE id = ?''', 
                  (name, mobile_number_1, mobile_number_2, email_id, address, state, city, country, face_id))
        # Update the recognition_logs table to reflect the name change
        c.execute('''UPDATE recognition_logs 
                     SET name = ? 
                     WHERE face_id = ?''', 
                  (name, face_id))

        
        # Check if the old email exists in the userlogin table
        c.execute('SELECT COUNT(*) FROM userlogin WHERE gmail = ?', (old_email,))
        old_email_exists = c.fetchone()[0] > 0
        

        if email_id != old_email:
            
            if not old_email_exists:
                # Old email does not exist, so insert a new entry with the new email
                insert_userlogin(email_id,c)
            else:
                # Old email exists, update the existing entry to reflect the new email
                c.execute('UPDATE userlogin SET gmail = ? WHERE gmail = ?', (email_id, old_email))
        elif old_email == email_id and not old_email_exists:
           
            # New email is the same as the old email but the old email is not in userlogin
            insert_userlogin(email_id,c)
        
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
    if 'email' not in session:
        return redirect('/login')
    sort_order = request.args.get('sort_order', 'all')
    faces = fetch_faces(sort_order)
    return render_template('analyze.html', faces=faces, sort_order=sort_order)






@app.route('/recognize')
def recognize():
    if 'email' not in session:
        return redirect('/login')
    return render_template('recogonize.html')







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