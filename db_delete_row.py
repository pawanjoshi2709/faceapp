import sqlite3

def delete_userlogin(gmail):
    # Connect to the existing database
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()

    try:
        # Execute the delete statement
        c.execute('DELETE FROM userlogin WHERE gmail = ?', (gmail,))
        
        # Commit the changes
        conn.commit()
        print("User login deleted successfully.")
        
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        
    finally:
        # Close the connection
        conn.close()

def main():
    """ Main function to read and display data. """
    #print("Fetching and saving images from the database...")
    #fetch_images()
    
    #print("Inspecting 'faces' table structure and contents...")
    delete_userlogin('Nonea@dd.com')
    #fetch_encodings()
if __name__ == '__main__':
    main()
