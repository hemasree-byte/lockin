import sqlite3

connection = sqlite3.connect('database.db')
cursor = connection.cursor()

cursor.execute("ALTER TABLE physical_profile ADD COLUMN meals TEXT")

connection.commit()
connection.close()

print("meals column added successfully.")
