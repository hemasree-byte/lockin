import sqlite3

connection = sqlite3.connect('database.db')
cursor = connection.cursor()

cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")

connection.commit()
connection.close()

print("password_hash column added successfully.")