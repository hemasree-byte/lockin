from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import date, timedelta

app = Flask(__name__)
app.secret_key = 'dev-secret-key-change-later'


# ---------------------------------------------------------------
# ACCOUNT: signup, login, logout, dashboard
# ---------------------------------------------------------------

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


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def db_one(query, user_id):
    connection = sqlite3.connect('database.db')
    try:
        cursor = connection.cursor()
        cursor.execute(query, (user_id,))
        return cursor.fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        connection.close()


GOAL_LABELS = {
    'lose_weight': 'Lose weight',
    'lose_fat': 'Lose fat',
    'maintain_weight': 'Maintain weight',
    'build_muscle': 'Build muscle',
}


@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = db_one("SELECT username FROM users WHERE user_id = ?", user_id)
    username = user[0] if user else ''

    targets = db_one("SELECT calories, protein_g FROM nutrition_targets WHERE user_id = ?", user_id)
    profile = db_one("SELECT height_cm, weight_kg, age, biological_sex, activity_level, diet_type, allergies, meals FROM physical_profile WHERE user_id = ?", user_id)
    goal = db_one("SELECT general_goal FROM user_goals WHERE user_id = ?", user_id)
    safety = db_one("SELECT monthly_expenses, emergency_savings FROM finance_safety WHERE user_id = ?", user_id)
    split = db_one("SELECT monthly_income, savings_pct, emergency_pct, investments_pct, fixed_deposit_pct, trading_pct FROM finance_split WHERE user_id = ?", user_id)
    actual = db_one("SELECT savings_amt, emergency_amt, investments_amt, fixed_deposit_amt, trading_amt FROM finance_actual WHERE user_id = ?", user_id)

    calories = round(float(targets[0])) if targets and targets[0] else None
    protein = round(float(targets[1])) if targets and targets[1] else None
    goal_text = GOAL_LABELS.get(goal[0], '-') if goal and goal[0] else '-'

    reserve_months = round(safety[1] / safety[0], 1) if safety and safety[0] else None
    planned_savings = round(split[0] * split[1] / 100) if split and split[0] else None

    allocation = []
    if split:
        for i, (key, label) in enumerate(FINANCE_CATEGORIES):
            allocation.append((label, split[i + 1]))

    health_score = None
    if profile:
        height, weight, age, sex, activity, diet_type, allergies, meals_str = profile
        filled = sum(1 for v in (height, weight, age, sex, activity, diet_type, meals_str) if v not in (None, ''))
        if allergies is not None:
            filled += 1
        health_score = round(filled / 8 * 100)

    parts = []
    if reserve_months is not None:
        parts.append(min(reserve_months / 6, 1) * 100)
    if split and actual and split[0]:
        on_track = 0
        for i in range(5):
            target = split[i + 1]
            if target > 0 and actual[i] == 0:
                continue
            if abs(actual[i] / split[0] * 100 - target) <= 5:
                on_track += 1
        parts.append(on_track / 5 * 100)
    finance_score = round(sum(parts) / len(parts)) if parts else None

    return render_template(
        'dashboard.html', username=username, calories=calories, protein=protein,
        goal_text=goal_text, reserve_months=reserve_months, planned_savings=planned_savings,
        allocation=allocation, health_score=health_score, finance_score=finance_score
    )

# ---------------------------------------------------------------
# ONBOARDING (Health): units -> profile -> goals -> activity ->
# diet -> allergies -> meals -> meal preferences -> nutrition
# targets -> reminders
# ---------------------------------------------------------------

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
    'vegetarian': ['shellfish', 'meat', 'fish'],
    'vegan': ['dairy', 'eggs', 'shellfish', 'meat', 'fish'],
    'paleo': ['dairy', 'gluten', 'soy'],
    'mediterranean': [],
    'anything': []
}

ALLERGENS = ['dairy', 'eggs', 'gluten', 'peanuts', 'sesame', 'shellfish', 'soy', 'tree nuts']

FOODS = [
    {'name': 'Oatmeal with banana', 'meal': 'breakfast', 'contains': [], 'kcal': 320, 'protein': 9},
    {'name': 'Scrambled eggs on toast', 'meal': 'breakfast', 'contains': ['eggs', 'gluten'], 'kcal': 380, 'protein': 20},
    {'name': 'Fruit smoothie with yogurt', 'meal': 'breakfast', 'contains': ['dairy'], 'kcal': 280, 'protein': 10},
    {'name': 'Peanut butter sandwich', 'meal': 'breakfast', 'contains': ['peanuts', 'gluten'], 'kcal': 420, 'protein': 15},
    {'name': 'Vegetable salad bowl', 'meal': 'lunch', 'contains': [], 'kcal': 250, 'protein': 8},
    {'name': 'Chicken wrap', 'meal': 'lunch', 'contains': ['gluten', 'meat'], 'kcal': 520, 'protein': 32},
    {'name': 'Rice with dal', 'meal': 'lunch', 'contains': [], 'kcal': 480, 'protein': 16},
    {'name': 'Paneer rice bowl', 'meal': 'lunch', 'contains': ['dairy'], 'kcal': 580, 'protein': 24},
    {'name': 'Grilled vegetables with quinoa', 'meal': 'dinner', 'contains': [], 'kcal': 450, 'protein': 15},
    {'name': 'Fish curry with rice', 'meal': 'dinner', 'contains': ['fish'], 'kcal': 560, 'protein': 30},
    {'name': 'Veg pasta', 'meal': 'dinner', 'contains': ['gluten'], 'kcal': 520, 'protein': 16},
    {'name': 'Tofu stir fry', 'meal': 'dinner', 'contains': ['soy', 'sesame'], 'kcal': 400, 'protein': 22},
    {'name': 'Mixed fruit bowl', 'meal': 'snack', 'contains': [], 'kcal': 150, 'protein': 2},
    {'name': 'Roasted almonds', 'meal': 'snack', 'contains': ['tree nuts'], 'kcal': 170, 'protein': 6},
    {'name': 'Greek yogurt cup', 'meal': 'snack', 'contains': ['dairy'], 'kcal': 140, 'protein': 12},
    {'name': 'Peanut chikki', 'meal': 'snack', 'contains': ['peanuts'], 'kcal': 190, 'protein': 5},
]


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
            "INSERT OR REPLACE INTO meal_preferences (user_id, meal_type, additional_family_members, preferred_categories) VALUES (?, ?, ?, ?)",
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
            "INSERT OR REPLACE INTO nutrition_targets (user_id, calories, carbs_g, fat_g, protein_g) VALUES (?, ?, ?, ?, ?)",
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

    # Step 1: RMR (Mifflin-St Jeor)
    if sex == 'male':
        rmr = 10 * weight + 6.25 * height - 5 * age + 5
    elif sex == 'female':
        rmr = 10 * weight + 6.25 * height - 5 * age - 161
    else:
        rmr = ((10 * weight + 6.25 * height - 5 * age + 5) + (10 * weight + 6.25 * height - 5 * age - 161)) / 2

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
                "INSERT OR REPLACE INTO user_reminders (user_id, opted_in, reminder_time) VALUES (?, ?, ?)",
                (user_id, False, None)
            )
            connection.commit()
            connection.close()
            return redirect(url_for('dashboard'))

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
            "INSERT OR REPLACE INTO user_reminders (user_id, opted_in, reminder_time) VALUES (?, ?, ?)",
            (user_id, True, final_time)
        )
        connection.commit()
        connection.close()

        return redirect(url_for('dashboard'))

    return render_template('reminder_time.html')


# ---------------------------------------------------------------
# HEALTH: meal plan
# ---------------------------------------------------------------

@app.route('/meal_plan')
def meal_plan():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    connection = sqlite3.connect('database.db')
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT diet_type, allergies, meals FROM physical_profile WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        try:
            cursor.execute("SELECT calories, protein_g FROM nutrition_targets WHERE user_id = ?", (user_id,))
            target = cursor.fetchone()
        except sqlite3.OperationalError:
            target = None
    finally:
        connection.close()

    if row is None:
        return redirect(url_for('units'))

    diet_type, allergies_str, meals_str = row

    allergies_list = [a for a in (allergies_str or '').split(',') if a]
    chosen_meals = [m for m in (meals_str or '').split(',') if m]

    blocked = set(allergies_list) | set(DIET_EXCLUSIONS.get(diet_type, []))

    plan = {}
    for meal in chosen_meals:
        plan[meal] = [
            food for food in FOODS
            if food['meal'] == meal and not (set(food['contains']) & blocked)
        ]

    target_kcal = round(float(target[0])) if target and target[0] else None
    target_protein = round(float(target[1])) if target and target[1] else None

    return render_template('meal_plan.html', plan=plan,
                           target_kcal=target_kcal, target_protein=target_protein)


# ---------------------------------------------------------------
# ETIQUETTES
# ---------------------------------------------------------------

@app.route('/etiquette')
def etiquette():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    tips = {
        'Dining': [
            'Wait for everyone to be served before you start eating.',
            'Keep your phone off the table.',
            'Chew with your mouth closed and do not talk with food in it.',
        ],
        'Workplace': [
            'Be on time, and message early if you will be late.',
            'Reply to emails within a working day.',
            'Greet people properly when you enter a room.',
        ],
        'Online and phone': [
            'Do not call late at night unless it is urgent.',
            'Use a clear, polite tone in messages.',
            'Think before you post something you cannot take back.',
        ],
    }
    return render_template('etiquette.html', tips=tips)


# ---------------------------------------------------------------
# FINANCE
# ---------------------------------------------------------------

# The order here must match the order of the shares in finance_plan()
# and the columns in the finance_split table.
FINANCE_CATEGORIES = [
    ('savings_pct', 'Savings'),
    ('emergency_pct', 'Emergency fund'),
    ('investments_pct', 'Investments'),
    ('fixed_deposit_pct', 'Fixed deposit'),
    ('trading_pct', 'Trading capital'),
]

ACTUAL_COLUMNS = ['savings_amt', 'emergency_amt', 'investments_amt', 'fixed_deposit_amt', 'trading_amt']


@app.route('/finance_plan', methods=['GET', 'POST'])
def finance_plan():
    """The app works out a suggested split for the user (rule-based)."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    error = None
    plan = None

    if request.method == 'POST':
        try:
            income = float(request.form.get('income'))
            expenses = float(request.form.get('expenses'))
            savings_now = float(request.form.get('savings_now') or 0)
        except (TypeError, ValueError):
            error = 'Please enter numbers only.'
        else:
            if income <= 0 or expenses <= 0:
                error = 'Income and expenses must be more than 0.'
            elif savings_now < 0:
                error = 'Savings cannot be negative.'
            elif expenses >= income:
                error = 'Your essential expenses are as high as your income, so there is nothing left to split. Reducing expenses or raising income comes first.'

        if error is None:
            remaining = income - expenses
            months_raw = savings_now / expenses

            # Order matches FINANCE_CATEGORIES:
            # savings, emergency, investments, fixed deposit, trading
            if months_raw < 3:
                shares = [20, 50, 15, 15, 0]
                reason = 'Your safety net covers under 3 months, so the biggest share goes to the emergency fund and nothing goes to trading.'
            elif months_raw < 6:
                shares = [20, 30, 25, 20, 5]
                reason = 'Your safety net covers 3 to 6 months. You can start growing money while still topping up the emergency fund.'
            else:
                shares = [20, 10, 40, 20, 10]
                reason = 'Your safety net covers 6 months or more, so more can go towards growth.'

            amounts = [round(remaining * s / 100, 2) for s in shares]
            pcts_of_income = [round(remaining * s / income, 1) for s in shares]

            connection = sqlite3.connect('database.db')
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO finance_split (user_id, monthly_income, savings_pct, emergency_pct, investments_pct, fixed_deposit_pct, trading_pct) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, income, *pcts_of_income)
                )
                cursor.execute(
                    "INSERT OR REPLACE INTO finance_safety (user_id, monthly_expenses, emergency_savings) VALUES (?, ?, ?)",
                    (user_id, expenses, savings_now)
                )
                connection.commit()
            finally:
                connection.close()

            rows = [
                (label, shares[i], amounts[i])
                for i, (key, label) in enumerate(FINANCE_CATEGORIES)
            ]
            plan = {
                'income': income,
                'expenses': expenses,
                'remaining': round(remaining, 2),
                'months': round(months_raw, 1),
                'reason': reason,
                'rows': rows,
            }

    return render_template('finance_plan.html', plan=plan, error=error)


@app.route('/finance', methods=['GET', 'POST'])
def finance():
    """Manual option: the user sets the percentages themselves (must total 100)."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    error = None

    if request.method == 'POST':
        try:
            income = float(request.form.get('income'))
            values = [float(request.form.get(key) or 0) for key, label in FINANCE_CATEGORIES]
        except (TypeError, ValueError):
            error = 'Please enter numbers only.'

        if error is None:
            total = sum(values)
            if income <= 0:
                error = 'Income must be more than 0.'
            elif any(v < 0 for v in values):
                error = 'Percentages cannot be negative.'
            elif round(total, 2) != 100:
                error = f'Your split adds up to {total:g}%. It must be exactly 100%.'

        if error is None:
            connection = sqlite3.connect('database.db')
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO finance_split (user_id, monthly_income, savings_pct, emergency_pct, investments_pct, fixed_deposit_pct, trading_pct) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, income, *values)
                )
                connection.commit()
            finally:
                connection.close()
            return redirect(url_for('finance'))

    connection = sqlite3.connect('database.db')
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT monthly_income, savings_pct, emergency_pct, investments_pct, fixed_deposit_pct, trading_pct FROM finance_split WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
    finally:
        connection.close()

    saved = None
    saved_income = None
    if row:
        saved_income = row[0]
        saved = [
            (label, row[i + 1], round(row[0] * row[i + 1] / 100, 2))
            for i, (key, label) in enumerate(FINANCE_CATEGORIES)
        ]

    return render_template('finance.html', categories=FINANCE_CATEGORIES, error=error,
                           saved=saved, saved_income=saved_income)


@app.route('/finance_progress', methods=['GET', 'POST'])
def finance_progress():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    connection = sqlite3.connect('database.db')
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT monthly_income, savings_pct, emergency_pct, investments_pct, fixed_deposit_pct, trading_pct FROM finance_split WHERE user_id = ?",
            (user_id,)
        )
        split = cursor.fetchone()
    finally:
        connection.close()

    if split is None:
        return redirect(url_for('finance_plan'))

    income = split[0]
    targets = split[1:]
    error = None

    if request.method == 'POST':
        try:
            amounts = [float(request.form.get(col) or 0) for col in ACTUAL_COLUMNS]
        except ValueError:
            error = 'Please enter numbers only.'
        else:
            if any(a < 0 for a in amounts):
                error = 'Amounts cannot be negative.'

        if error is None:
            connection = sqlite3.connect('database.db')
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO finance_actual (user_id, savings_amt, emergency_amt, investments_amt, fixed_deposit_amt, trading_amt) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, *amounts)
                )
                connection.commit()
            finally:
                connection.close()
            return redirect(url_for('finance_progress'))

    connection = sqlite3.connect('database.db')
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT savings_amt, emergency_amt, investments_amt, fixed_deposit_amt, trading_amt FROM finance_actual WHERE user_id = ?",
            (user_id,)
        )
        actual = cursor.fetchone()
    finally:
        connection.close()

    rows = []
    missing = []
    if actual:
        for i, (key, label) in enumerate(FINANCE_CATEGORIES):
            target = targets[i]
            actual_pct = round(actual[i] / income * 100, 1)
            diff = round(actual_pct - target, 1)
            if target > 0 and actual[i] == 0:
                status = 'Not considered yet. Nothing is going into this area.'
                missing.append(label)
            elif abs(diff) <= 5:
                status = 'On track'
            elif diff < 0:
                status = f'Under target by {abs(diff):g} points. Put more here.'
            else:
                status = f'Over target by {diff:g} points. Check your other areas.'
            rows.append((label, target, actual_pct, status))

    fields = list(zip(ACTUAL_COLUMNS, [label for key, label in FINANCE_CATEGORIES]))
    return render_template('finance_progress.html', rows=rows, fields=fields, error=error,
                           income=income, missing=missing)


@app.route('/finance_safety', methods=['GET', 'POST'])
def finance_safety():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    error = None

    if request.method == 'POST':
        try:
            expenses = float(request.form.get('monthly_expenses'))
            savings = float(request.form.get('emergency_savings'))
        except (TypeError, ValueError):
            error = 'Please enter numbers only.'
        else:
            if expenses <= 0:
                error = 'Monthly expenses must be more than 0.'
            elif savings < 0:
                error = 'Savings cannot be negative.'

        if error is None:
            connection = sqlite3.connect('database.db')
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO finance_safety (user_id, monthly_expenses, emergency_savings) VALUES (?, ?, ?)",
                    (user_id, expenses, savings)
                )
                connection.commit()
            finally:
                connection.close()
            return redirect(url_for('finance_safety'))

    connection = sqlite3.connect('database.db')
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT monthly_expenses, emergency_savings FROM finance_safety WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
    finally:
        connection.close()

    result = None
    if row:
        expenses, savings = row
        months = round(savings / expenses, 1)
        target_amount = round(expenses * 6, 2)
        shortfall = max(round(target_amount - savings, 2), 0)

        if months >= 6:
            status = 'Strong. Your reserve covers 6 months or more.'
        elif months >= 3:
            status = 'Getting there. A common guideline is 3 to 6 months of expenses.'
        else:
            status = 'Below 3 months. Building this reserve is a good first priority.'

        result = {'months': months, 'status': status,
                  'target_amount': target_amount, 'shortfall': shortfall}

    return render_template('finance_safety.html', result=result, error=error)


# ---------------------------------------------------------------
# WHERE YOU STAND: summary of the three areas
# ---------------------------------------------------------------

@app.route('/standing')
def standing():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    def fetch_one(query):
        connection = sqlite3.connect('database.db')
        try:
            cursor = connection.cursor()
            cursor.execute(query, (user_id,))
            return cursor.fetchone()
        except sqlite3.OperationalError:
            return None
        finally:
            connection.close()

    targets = fetch_one("SELECT calories, protein_g FROM nutrition_targets WHERE user_id = ?")
    safety = fetch_one("SELECT monthly_expenses, emergency_savings FROM finance_safety WHERE user_id = ?")
    split = fetch_one("SELECT monthly_income, savings_pct, emergency_pct, investments_pct, fixed_deposit_pct, trading_pct FROM finance_split WHERE user_id = ?")
    actual = fetch_one("SELECT savings_amt, emergency_amt, investments_amt, fixed_deposit_amt, trading_amt FROM finance_actual WHERE user_id = ?")

    health_lines = []
    if targets:
        health_lines.append(f'Daily target: {round(float(targets[0]))} kcal and {round(float(targets[1]))} g protein.')
        health_lines.append('Your meal plan is ready.')
    else:
        health_lines.append('Not set up yet. Finish onboarding to get your targets.')

    finance_lines = []
    if safety and safety[0]:
        months = round(safety[1] / safety[0], 1)
        if months >= 6:
            level = 'strong'
        elif months >= 3:
            level = 'getting there'
        else:
            level = 'needs attention'
        finance_lines.append(f'Safety net: {months} months of expenses covered ({level}).')
    if split and actual and split[0]:
        on_track = 0
        not_considered = 0
        for i in range(5):
            target = split[i + 1]
            if target > 0 and actual[i] == 0:
                not_considered += 1
                continue
            actual_pct = actual[i] / split[0] * 100
            if abs(actual_pct - target) <= 5:
                on_track += 1
        finance_lines.append(f'{on_track} of 5 money areas on track this month.')
        if not_considered:
            finance_lines.append(f'{not_considered} area(s) not considered yet.')
    elif split:
        finance_lines.append('Money plan saved. Log this month to see progress.')
    if not finance_lines:
        finance_lines.append('Not set up yet. Start with your money plan.')

    etiquette_lines = ['Not assessed yet. Read the guide to get started.']

    cards = [
        ('Physical Health', health_lines, 'meal_plan', 'Open meal plan'),
        ('Financial Health', finance_lines, 'finance_plan', 'Open money plan'),
        ('Etiquettes', etiquette_lines, 'etiquette', 'Open guide'),
    ]
    return render_template('standing.html', cards=cards)

@app.route('/trading_risk', methods=['GET', 'POST'])
def trading_risk():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    error = None
    result = None

    if request.method == 'POST':
        try:
            capital = float(request.form.get('capital'))
            risk_pct = float(request.form.get('risk_pct'))
            losses = int(request.form.get('losses'))
        except (TypeError, ValueError):
            error = 'Please enter numbers only.'
        else:
            if capital <= 0:
                error = 'Trading capital must be more than 0.'
            elif risk_pct <= 0 or risk_pct > 100:
                error = 'Risk per trade must be between 0 and 100 percent.'
            elif losses < 1:
                error = 'Losses in a row must be at least 1.'

        if error is None:
            max_loss = capital * risk_pct / 100
            remaining = capital * (1 - risk_pct / 100) ** losses
            lost = capital - remaining
            result = {
                'max_loss': round(max_loss, 2),
                'losses': losses,
                'remaining': round(remaining, 2),
                'lost': round(lost, 2),
                'lost_pct': round(lost / capital * 100, 1),
            }

    suggested = None
    connection = sqlite3.connect('database.db')
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT monthly_income, trading_pct FROM finance_split WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row[0] is not None and row[1] is not None:
            suggested = row[0] * row[1] / 100
    except sqlite3.OperationalError:
        suggested = None
    finally:
        connection.close()

    return render_template('trading_risk.html', error=error, result=result, suggested=suggested)

DOCUMENTS = [
    ('aadhaar', 'Aadhaar', 'Identity', 'Identity and address proof used for many services.', 'https://uidai.gov.in/'),
    ('pan', 'PAN card', 'Identity and finance', 'Needed for tax filing and many financial activities.', 'https://www.incometax.gov.in/'),
    ('voter_id', 'Voter ID (EPIC)', 'Civic', 'For eligible citizens aged 18 or above who want to vote.', 'https://voters.eci.gov.in/'),
    ('bank_account', 'Bank account', 'Finance', 'An account to receive and manage your money.', None),
    ('driving_licence', 'Driving licence', 'Transport', 'Needed to drive a vehicle legally. Eligibility rules apply.', 'https://parivahan.gov.in/'),
    ('passport', 'Passport', 'Travel', 'Needed for international travel. Not required for everyone.', 'https://www.passportindia.gov.in/'),
]

STATUSES = ['Not applied', 'Pending', 'Issued', 'Needs updating', 'Not applicable']


@app.route('/documents', methods=['GET', 'POST'])
def documents():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    if request.method == 'POST':
        connection = sqlite3.connect('database.db')
        try:
            cursor = connection.cursor()
            for key, name, category, description, url in DOCUMENTS:
                status = request.form.get('status_' + key)
                if status not in STATUSES:
                    status = 'Not applied'
                cursor.execute(
                    "INSERT OR REPLACE INTO user_documents (user_id, doc_key, status) VALUES (?, ?, ?)",
                    (user_id, key, status)
                )
            connection.commit()
        finally:
            connection.close()
        return redirect(url_for('documents'))

    saved = {}
    connection = sqlite3.connect('database.db')
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT doc_key, status, updated_at FROM user_documents WHERE user_id = ?", (user_id,))
        saved = {key: (status, updated) for key, status, updated in cursor.fetchall()}
    except sqlite3.OperationalError:
        saved = {}
    finally:
        connection.close()

    rows = []
    counts = {s: 0 for s in STATUSES}
    for key, name, category, description, url in DOCUMENTS:
        status, updated = saved.get(key, ('Not applied', None))
        counts[status] = counts.get(status, 0) + 1
        rows.append({'key': key, 'name': name, 'category': category,
                     'description': description, 'url': url,
                     'status': status, 'updated': updated})

    return render_template('documents.html', rows=rows, statuses=STATUSES, counts=counts)


if __name__ == '__main__':
    app.run(debug=True)