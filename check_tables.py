import sqlite3

con = sqlite3.connect('database.db')
for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    print(row[0])
con.close()