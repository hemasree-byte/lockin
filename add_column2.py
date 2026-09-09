import sqlite3

connection = sqlite3.connect('database.db')
cursor = connection.cursor()

cursor.execute("ALTER TABLE physical_profile ADD COLUMN diet_type TEXT")

connection.commit()
connection.close()

print("diet_type column added successfully.")