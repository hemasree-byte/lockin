import sqlite3

connection = sqlite3.connect('database.db')
cursor = connection.cursor()

cursor.execute("ALTER TABLE physical_profile ADD COLUMN allergies TEXT")

connection.commit()
connection.close()

print("allergies column added successfully.")