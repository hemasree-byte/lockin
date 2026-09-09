import sqlite3

connection = sqlite3.connect('database.db')
cursor = connection.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    agreed_to_tos BOOLEAN NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS physical_profile (
    user_id INTEGER PRIMARY KEY REFERENCES users(user_id),
    preferred_units TEXT,
    preferred_energy_unit TEXT,
    height_cm REAL,
    weight_kg REAL,
    age INTEGER,
    biological_sex TEXT,
    body_fat_level TEXT,
    activity_level TEXT,
    diet_type TEXT,
    allergies TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_goals (
    user_id INTEGER PRIMARY KEY REFERENCES users(user_id),
    goal_mode TEXT,
    general_goal TEXT,
    goal_weight_kg REAL,
    weekly_rate_kg REAL,
    estimated_completion_date TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS meal_preferences (
    user_id INTEGER REFERENCES users(user_id),
    meal_type TEXT,
    additional_family_members INTEGER,
    preferred_categories TEXT,
    PRIMARY KEY (user_id, meal_type)
)
''')


connection.commit()
connection.close()


print("Database and all tables created successfully.")

 