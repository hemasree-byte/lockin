from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import date, timedelta

app = Flask(__name__)
app.secret_key = 'dev-secret-key-change-later'

@app.route('/', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        tos = request.form.get('tos')

        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, email, agreed_to_tos) VALUES (?, ?, ?)",
                (username, email, bool(tos))
            )
            user_id = cursor.lastrowid
            connection.commit()
            connection.close()
            session['user_id'] = user_id
            return redirect(url_for('units'))
        except sqlite3.IntegrityError:
            connection.close()
            return "That username or email is already registered. Please try a different one."

    return render_template('signup.html')


@app.route('/units', methods=['GET', 'POST'])
def units():
    if request.method == 'POST':
        preferred_units = request.form.get('units')
        energy_unit = request.form.get('energy_unit')
        print(f"Units: {preferred_units}, Energy unit: {energy_unit}")
        return redirect(url_for('profile'))

    return render_template('units.html')


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        height = request.form.get('height')
        weight = request.form.get('weight')
        age = request.form.get('age')
        sex = request.form.get('sex')
        body_fat = request.form.get('body_fat')
        print(f"Profile: {height}cm, {weight}kg, age {age}, {sex}, body fat {body_fat}")
        return redirect(url_for('goals'))

    return render_template('profile.html')

from datetime import date, timedelta

@app.route('/goals', methods=['GET', 'POST'])
def goals():
    if request.method == 'POST':
        goal_mode = request.form.get('goal_mode')
        general_goal = request.form.get('general_goal')
        goal_weight = request.form.get('goal_weight')
        weekly_rate = request.form.get('weekly_rate')

        estimated_date = None

        if goal_mode == 'exact' and goal_weight and weekly_rate:
            # NOTE: this assumes we know the user's CURRENT weight
            # from the profile page — for now we'll hardcode a
            # placeholder until we connect it to the database
            current_weight = 60  # placeholder, replace once DB is connected
            weight_diff = abs(float(goal_weight) - current_weight)
            weeks_needed = weight_diff / abs(float(weekly_rate))
            estimated_date = date.today() + timedelta(weeks=weeks_needed)

        print(f"Goal mode: {goal_mode}, general: {general_goal}, exact weight: {goal_weight}, rate: {weekly_rate}, est. date: {estimated_date}")
        return f"Goal saved! Estimated completion: {estimated_date}" if estimated_date else "Goal saved! (general goal, no date estimate)"

    return render_template('goals.html')


if __name__ == '__main__':
    app.run(debug=True)