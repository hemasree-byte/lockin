import sqlite3

connection = sqlite3.connect('database.db')
cursor = connection.cursor()

cursor.execute("ALTER TABLE physical_profile ADD COLUMN activity_level TEXT")

connection.commit()
connection.close()

print("activity_level column added successfully.")