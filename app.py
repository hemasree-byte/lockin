from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import date, timedelta


app = Flask(__name__)
app.secret_key = 'dev-secret-key-change-later'
@app.route('/', methods=['GET', 'POST'])

def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        tos = request.form.get('tos')

        password_hash = generate_password_hash(password)

        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, email, agreed_to_tos, password_hash) VALUES (?, ?, ?, ?)",
                (username, email, bool(tos), password_hash)
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute("SELECT user_id, password_hash FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        connection.close()

        if result and check_password_hash(result[1], password):
            session['user_id'] = result[0]
            return redirect(url_for('dashboard'))
        else:
            return "Invalid username or password. Please try again."

    return render_template('login.html')  
@app.route('/dashboard')


def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
    username = cursor.fetchone()[0]
    connection.close()

    return f"Welcome back, {username}! (Dashboard coming soon)" 


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

        return redirect(url_for('meal_preferences', meal_type='breakfast'))
    
    return render_template('meals.html')

MEAL_CATEGORIES = {
    'breakfast': ['Shakes & smoothies', 'Oatmeal & cereals', 'Sandwiches & wraps', 'Skillets & hashes', 'Nut/seed & dried fruits', 'High protein snacks'],
    'lunch': ['Salads & bowls', 'Sandwiches & wraps', 'Soups', 'Rice & grain based', 'High protein'],
    'dinner': ['One-pot meals', 'Grilled/roasted', 'Soups & stews', 'Rice & grain based', 'High protein'],
    'snack': ['Fruits & nuts', 'Protein bars/shakes', 'Yogurt based', 'Baked snacks']
}

MEAL_ORDER = ['breakfast', 'lunch', 'dinner', 'snack']

@app.route('/meal_preferences/<meal_type>', methods=['GET', 'POST'])
def meal_preferences(meal_type):
    categories = MEAL_CATEGORIES.get(meal_type, [])

    if request.method == 'POST':
        family_members = request.form.get('family_members')
        selected_categories = request.form.getlist('categories')
        categories_str = ",".join(selected_categories)
        user_id = session.get('user_id')

        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO meal_preferences (user_id, meal_type, additional_family_members, preferred_categories) VALUES (?, ?, ?, ?)",
            (user_id, meal_type, family_members, categories_str)
        )
        connection.commit()
        connection.close()

        current_index = MEAL_ORDER.index(meal_type)
        if current_index + 1 < len(MEAL_ORDER):
            next_meal = MEAL_ORDER[current_index + 1]
            return redirect(url_for('meal_preferences', meal_type=next_meal))
        else:
            return redirect(url_for('nutrition_targets'))
    return render_template('meal_preferences.html', meal_type=meal_type, categories=categories)

ACTIVITY_MULTIPLIERS = {
    'sedentary': 1.2,
    'lightly_active': 1.375,
    'moderately_active': 1.55,
    'very_active': 1.725,
    'extremely_active': 1.9
}

@app.route('/nutrition_targets', methods=['GET', 'POST'])
def nutrition_targets():
    user_id = session.get('user_id')
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    if request.method == 'POST':
        calories = request.form.get('calories')
        carbs = request.form.get('carbs')
        fat = request.form.get('fat')
        protein = request.form.get('protein')

        cursor.execute(
            "INSERT INTO nutrition_targets (user_id, calories, carbs_g, fat_g, protein_g) VALUES (?, ?, ?, ?, ?)",
            (user_id, calories, carbs, fat, protein)
        )
        connection.commit()
        connection.close()

        return redirect(url_for('reminders'))

    # GET: calculate the estimate
    cursor.execute(
        "SELECT height_cm, weight_kg, age, biological_sex, activity_level FROM physical_profile WHERE user_id = ?",
        (user_id,)
    )
    profile = cursor.fetchone()
    height, weight, age, sex, activity_level = profile

    cursor.execute(
        "SELECT general_goal, weekly_rate_kg FROM user_goals WHERE user_id = ?",
        (user_id,)
    )
    goal = cursor.fetchone()
    general_goal, weekly_rate = goal if goal else (None, None)
    connection.close()

    # Step 1: RMR
    if sex == 'male':
        rmr = 10*weight + 6.25*height - 5*age + 5
    elif sex == 'female':
        rmr = 10*weight + 6.25*height - 5*age - 161
    else:
        rmr = ((10*weight + 6.25*height - 5*age + 5) + (10*weight + 6.25*height - 5*age - 161)) / 2

    # Step 2: TDEE
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    tdee = rmr * multiplier

    # Step 3: Goal adjustment
    daily_adjustment = 0
    if weekly_rate:
        daily_adjustment = (float(weekly_rate) * 7700) / 7
        if general_goal in ['lose_weight', 'lose_fat']:
            daily_adjustment = -abs(daily_adjustment)
        elif general_goal == 'build_muscle':
            daily_adjustment = abs(daily_adjustment)

    calories = round(tdee + daily_adjustment)

    # Step 4: Macro split (40/30/30)
    carbs = round((calories * 0.4) / 4)
    protein = round((calories * 0.3) / 4)
    fat = round((calories * 0.3) / 9)

    return render_template('nutrition_targets.html', calories=calories, carbs=carbs, fat=fat, protein=protein)
@app.route('/reminders', methods=['GET', 'POST'])
def reminders():
    if request.method == 'POST':
        opt_in = request.form.get('opt_in')
        user_id = session.get('user_id')

        if opt_in == 'yes':
            return redirect(url_for('reminder_time'))
        else:
            connection = sqlite3.connect('database.db')
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO user_reminders (user_id, opted_in, reminder_time) VALUES (?, ?, ?)",
                (user_id, False, None)
            )
            connection.commit()
            connection.close()
            return "Onboarding complete! Welcome to Lockin."

    return render_template('reminders.html')


@app.route('/reminder_time', methods=['GET', 'POST'])
def reminder_time():
    if request.method == 'POST':
        reminder_time = request.form.get('reminder_time')
        custom_time = request.form.get('custom_time')
        final_time = custom_time if custom_time else reminder_time
        user_id = session.get('user_id')

        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO user_reminders (user_id, opted_in, reminder_time) VALUES (?, ?, ?)",
            (user_id, True, final_time)
        )
        connection.commit()
        connection.close()

        return "Onboarding complete! Welcome to Lockin."

    return render_template('reminder_time.html')

if __name__ == '__main__':
    app.run(debug=True)