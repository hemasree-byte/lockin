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
        user_id = session.get('user_id')

        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO physical_profile (user_id, preferred_units, preferred_energy_unit) VALUES (?, ?, ?)",
            (user_id, preferred_units, energy_unit)
        )
        connection.commit()
        connection.close()

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
        user_id = session.get('user_id')

        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE physical_profile SET height_cm = ?, weight_kg = ?, age = ?, biological_sex = ?, body_fat_level = ? WHERE user_id = ?",
            (height, weight, age, sex, body_fat, user_id)
        )
        connection.commit()
        connection.close()

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
        user_id = session.get('user_id')

        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()

        cursor.execute("SELECT weight_kg FROM physical_profile WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        current_weight = result[0] if result else None

        estimated_date = None
        if goal_mode == 'exact' and goal_weight and weekly_rate and current_weight:
            weight_diff = abs(float(goal_weight) - current_weight)
            weeks_needed = weight_diff / abs(float(weekly_rate))
            estimated_date = date.today() + timedelta(weeks=weeks_needed)

        cursor.execute(
            "INSERT INTO user_goals (user_id, goal_mode, general_goal, goal_weight_kg, weekly_rate_kg, estimated_completion_date) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, goal_mode, general_goal, goal_weight, weekly_rate, str(estimated_date) if estimated_date else None)
        )
        connection.commit()
        connection.close()

        return redirect(url_for('activity'))

    return render_template('goals.html')

@app.route('/activity', methods=['GET', 'POST'])
def activity():
    if request.method == 'POST':
        activity_level = request.form.get('activity_level')
        user_id = session.get('user_id')

        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE physical_profile SET activity_level = ? WHERE user_id = ?",
            (activity_level, user_id)
        )
        connection.commit()
        connection.close()

        return redirect(url_for('diet'))

    return render_template('activity.html')

@app.route('/diet', methods=['GET', 'POST'])
def diet():
    if request.method == 'POST':
        diet_type = request.form.get('diet_type')
        user_id = session.get('user_id')

        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE physical_profile SET diet_type = ? WHERE user_id = ?",
            (diet_type, user_id)
        )
        connection.commit()
        connection.close()

        return redirect(url_for('allergies'))

    return render_template('diet.html')



DIET_EXCLUSIONS = {
    'keto': ['gluten'],
    'vegetarian': ['shellfish'],
    'vegan': ['dairy', 'eggs', 'shellfish'],
    'paleo': ['dairy', 'gluten', 'soy'],
    'mediterranean': [],
    'anything': []
}

ALLERGENS = ['dairy', 'eggs', 'gluten', 'peanuts', 'sesame', 'shellfish', 'soy', 'tree nuts']

@app.route('/allergies', methods=['GET', 'POST'])
def allergies():
    user_id = session.get('user_id')
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute("SELECT diet_type FROM physical_profile WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    diet_type = result[0] if result else 'anything'
    already_excluded = DIET_EXCLUSIONS.get(diet_type, [])

    if request.method == 'POST':
        selected_allergies = request.form.getlist('allergies')
        allergies_str = ",".join(selected_allergies)

        cursor.execute(
            "UPDATE physical_profile SET allergies = ? WHERE user_id = ?",
            (allergies_str, user_id)
        )
        connection.commit()
        connection.close()

        return redirect(url_for('meals'))

    connection.close()
    return render_template('allergies.html', allergens=ALLERGENS, already_excluded=already_excluded, diet_type=diet_type)


@app.route('/meals', methods=['GET', 'POST'])
def meals():
    if request.method == 'POST':
        selected_meals = request.form.getlist('meals')
        meals_str = ",".join(selected_meals)
        user_id = session.get('user_id')

        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE physical_profile SET meals = ? WHERE user_id = ?",
            (meals_str, user_id)
        )
        connection.commit()
        connection.close()

        return "Meals saved! Onboarding flow complete so far."

    return render_template('meals.html')



if __name__ == '__main__':
    app.run(debug=True)