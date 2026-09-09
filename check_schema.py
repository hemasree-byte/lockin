import sqlite3

connection = sqlite3.connect('database.db')
cursor = connection.cursor()

cursor.execute("PRAGMA table_info(physical_profile)")
for column in cursor.fetchall():
    print(column)

connection.close()