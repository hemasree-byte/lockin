import sqlite3

connection = sqlite3.connect('database.db')
cursor = connection.cursor()

print("--- USERS ---")
cursor.execute("SELECT * FROM users")
for row in cursor.fetchall():
    print(row)

print("\n--- PHYSICAL PROFILE ---")
cursor.execute("SELECT * FROM physical_profile")
for row in cursor.fetchall():
    print(row)

print("\n--- USER GOALS ---")
cursor.execute("SELECT * FROM user_goals")
for row in cursor.fetchall():
    print(row)

connection.close()