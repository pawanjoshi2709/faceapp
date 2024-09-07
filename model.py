import pickle
import cv2
import face_recognition
import sqlite3
from datetime import datetime

def save_face(name, mobile_number_1, encoding, frame, mobile_number_2=None, email_id=None, address=None, state=None, city=None, country=None):
    if name is None:
        name = "Unknown"
    
    encoding_binary = pickle.dumps(encoding)
    _, image_binary = cv2.imencode('.jpg', frame)

    conn = sqlite3.connect('faces.db')
    c = conn.cursor()

    c.execute('''
        INSERT INTO faces (name, mobile_number_1, mobile_number_2, email_id, address, state, city, country, encoding, image)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, mobile_number_1, mobile_number_2, email_id, address, state, city, country, encoding_binary, image_binary.tobytes()))
    
    conn.commit()
    conn.close()

def load_encodings():
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    c.execute('SELECT id, name, mobile_number_1, encoding FROM faces')
    data = c.fetchall()
    conn.close()
    
    known_face_encodings = []
    known_face_names = []
    known_face_metadata = []
    for face_id, name, phone, encoding in data:
        known_face_encodings.append(pickle.loads(encoding))
        known_face_names.append(name)
        known_face_metadata.append((face_id, name, phone))
    
    return known_face_encodings, known_face_names, known_face_metadata

def is_encoding_in_database(encoding):
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    c.execute('SELECT encoding FROM faces')
    data = c.fetchall()
    conn.close()
    
    for stored_encoding in data:
        stored_encoding = pickle.loads(stored_encoding[0])
        matches = face_recognition.compare_faces([stored_encoding], encoding)
        if True in matches:
            return True
    return False

def is_unknown_face_in_database(encoding):
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    c.execute('SELECT encoding FROM faces WHERE name = "Unknown"')
    data = c.fetchall()
    conn.close()
    
    for stored_encoding in data:
        stored_encoding = pickle.loads(stored_encoding[0])
        matches = face_recognition.compare_faces([stored_encoding], encoding)
        if True in matches:
            return True
    return False

from datetime import datetime
import sqlite3

def log_recognition(face_id, name, is_known):
    today = datetime.now().strftime('%Y-%m-%d')
    now = datetime.now()

    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    
    if is_known:
        c.execute('''
            SELECT id, start_time, total_time FROM recognition_logs 
            WHERE face_id = ? AND date = ?
        ''', (face_id, today))
        
        result = c.fetchone()
        
        if result:
            log_id, start_time, total_time = result
            start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            duration = (now - start_time).total_seconds() / 60.0
            new_total_time = total_time + duration
            c.execute('''
                UPDATE recognition_logs 
                SET total_time = ?, start_time = ?, last_recorded_time = ?
                WHERE id = ?
            ''', (new_total_time, start_time.strftime('%Y-%m-%d %H:%M:%S'), now.strftime('%Y-%m-%d %H:%M:%S'), log_id))
        else:
            c.execute('''
                INSERT INTO recognition_logs (face_id, name, date, start_time, total_time, last_recorded_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (face_id, name, today, now.strftime('%Y-%m-%d %H:%M:%S'), 0, now.strftime('%Y-%m-%d %H:%M:%S')))
    
    else:
        c.execute('''
            SELECT id, start_time, total_time FROM recognition_logs 
            WHERE face_id IS NULL AND date = ?
        ''', (today,))
        
        result = c.fetchone()
        
        if result:
            log_id, start_time, total_time = result
            start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            duration = (now - start_time).total_seconds() / 60.0
            new_total_time = total_time + duration
            c.execute('''
                UPDATE recognition_logs 
                SET total_time = ?, start_time = ?, last_recorded_time = ?
                WHERE id = ?
            ''', (new_total_time, start_time.strftime('%Y-%m-%d %H:%M:%S'), now.strftime('%Y-%m-%d %H:%M:%S'), log_id))
        else:
            c.execute('''
                INSERT INTO recognition_logs (face_id, name, date, start_time, total_time, last_recorded_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (None, 'Unknown', today, now.strftime('%Y-%m-%d %H:%M:%S'), 0, now.strftime('%Y-%m-%d %H:%M:%S')))
    
    conn.commit()
    conn.close()


