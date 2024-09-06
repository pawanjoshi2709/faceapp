import sqlite3
import cv2
import numpy as np
from PIL import Image
import pickle
# Path to your SQLite database
DATABASE_PATH = 'faces.db'

def connect_db():
    """ Connect to the SQLite database. """
    return sqlite3.connect(DATABASE_PATH)

def fetch_images():
    """ Fetch and save images from the database. """
    conn = connect_db()
    cursor = conn.cursor()
    
    # Query to fetch image data from 'faces' table
    cursor.execute("SELECT image FROM faces")  # Ensure 'image_data' is the correct column name
    
    # Fetch all the image data
    images = cursor.fetchall()
    
    for i, image in enumerate(images):
        # Convert the binary data to a NumPy array
        np_image = np.frombuffer(image[0], np.uint8)
        
        # Decode the image from the NumPy array
        img = cv2.imdecode(np_image, cv2.IMREAD_COLOR)
        
        # Save the image to disk
        image_filename = f'image_{i+1}.png'
        cv2.imwrite(image_filename, img)
        print(f'Saved image {i+1} as {image_filename}')
    
    # Close the database connection
    conn.close()

def inspect_specific_tables():
    """ Inspect the 'faces' table structure and data. """
    conn = connect_db()
    cursor = conn.cursor()
    
    # Inspect the 'faces' table
    print("\nContents of the 'userlogin' table:")
    cursor.execute("PRAGMA table_info(userlogin);")  # Get column names for 'faces'
    columns = [description[1] for description in cursor.fetchall()]
    print("Columns:", columns)
    
    cursor.execute("SELECT * FROM userlogin;")
    faces_data = cursor.fetchall()
    for row in faces_data:
        print(row)
    
    # Close the connection
    conn.close()
def fetch_encodings():
    """ Fetch and display encodings from the database. """
    conn = connect_db()
    cursor = conn.cursor()
    
    # Query to fetch encoding data from 'faces' table
    cursor.execute("SELECT id, name, encoding FROM faces")
    
    # Fetch all the encoding data
    encodings = cursor.fetchall()
    
    for row in encodings:
        id, name, encoding_data = row
        print(f"ID: {id}, Name: {name}, Raw Encoding Data: {encoding_data[:100]}...")  # Print first 100 bytes of data for inspection
        
        try:
            # Deserialize the pickled data
            encoding = pickle.loads(encoding_data)
            print(f"Encoding (after unpickling): {encoding}")

            # Optionally, you can check the type of the deserialized object
            if isinstance(encoding, np.ndarray):
                print(f"Encoding shape: {encoding.shape}, dtype: {encoding.dtype}")
            else:
                print(f"Encoding is not a NumPy array. Type: {type(encoding)}")
        
        except Exception as e:
            print(f"Error decoding: {e}")
    
    # Close the database connection
    conn.close()
def main():
    """ Main function to read and display data. """
    #print("Fetching and saving images from the database...")
    #fetch_images()
    
    #print("Inspecting 'faces' table structure and contents...")
    inspect_specific_tables()
    #fetch_encodings()
if __name__ == '__main__':
    main()
