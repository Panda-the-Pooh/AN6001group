from flask import Flask, render_template, request
import sqlite3
import google.generativeai as genai
import os
from datetime import datetime

app = Flask(__name__)

api = os.getenv('makersuite')
genai.configure(api_key = api)
model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize the SQLite database
def init_db():
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weight_history (
            id INTEGER PRIMARY KEY, 
            date TEXT, 
            weight REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercise_data (
            id INTEGER PRIMARY KEY, 
            date TEXT, 
            heart_rate INTEGER, 
            steps INTEGER, 
            calories INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_data (
            id INTEGER PRIMARY KEY, 
            date TEXT, 
            food_list TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Main Home
@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

# Home - Health management main interface
@app.route("/health", methods=["GET", "POST"])
def health_index():
    return render_template("3_health/index.html")


# ========= Weight Update  =========

# Display the weight update form page
@app.route("/health/update_weight_form", methods=["GET", "POST"])
def update_weight_form():
    return render_template("3_health/1_update_weight.html")

# Handle weight update submission
@app.route("/health/update_weight", methods=["GET", "POST"])
def update_weight():
    weight = request.form.get("weight")
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO weight_history (date, weight) VALUES (?, ?)", (date, weight))
    conn.commit()
    conn.close()

    return render_template("3_health/dashboard.html", message="Weight data updated!")

# ========= Sports data submission =========

# Display the sports data form page
@app.route("/health/submit_exercise_form", methods=["GET", "POST"])
def submit_exercise_form():
    return render_template("3_health/2_submit_exercise.html")

# Processing motion data submission
@app.route("/health/submit_exercise", methods=["GET", "POST"])
def submit_exercise():
    heart_rate = request.form.get("heart_rate")
    steps = request.form.get("steps")
    calories = request.form.get("calories")
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO exercise_data (date, heart_rate, steps, calories) VALUES (?, ?, ?, ?)", 
                   (date, heart_rate, steps, calories))
    conn.commit()
    conn.close()

    return render_template("3_health/dashboard.html", message="Sports data recorded!")

# ========= Diet data submission =========

# Display the diet data form page
@app.route("/health/submit_food_form", methods=["GET", "POST"])
def submit_food_form():
    return render_template("3_health/3_submit_food.html")

# Process dietary data submission & call genAI to calculate calories
@app.route("/health/submit_food", methods=["GET", "POST"])
def submit_food():
    food_list = request.form.get("food_list")
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save to database
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO food_data (date, food_list) VALUES (?, ?)", (date, food_list))
    conn.commit()
    conn.close()

    # Call Gemini to calculate 
    prompt = f"Calculate the total calories and nutritional ratio (carbohydrate/protein/fat) of the following foods: {food_list}"
    
    response = model.generate_content(prompt)
    
    nutrition_result = response.text if response and response.text else "Unable to obtain nutritional analysis results"

    return render_template("3_health/dashboard.html", message="Diet data recorded!", nutrition_analysis=nutrition_result)

# ========= Generate health report ==========

@app.route("/health/generate_report", methods=["GET", "POST"])
def generate_report():
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()

    # Get the weight data for the last 7 days
    cursor.execute("SELECT date, weight FROM weight_history ORDER BY date DESC LIMIT 7")
    weight_history = cursor.fetchall()

    # Get the last 7 days of exercise data
    cursor.execute("SELECT date, heart_rate, steps, calories FROM exercise_data ORDER BY date DESC LIMIT 7")
    exercise_data = cursor.fetchall()

    conn.close()

    # Generate AI health recommendations (based on historical data)
    prompt = f"User's weight change in the last 7 days: {weight_history}, Sports data: {exercise_data}. Please provide an overall health analysis, including weight trends, exercise recommendations, and dietary modification plans."
    response = model.generate_content(prompt)
    
    health_advice = response.text if response and response.text else "Unable to obtain nutritional analysis results"

    return render_template("3_health/health_report.html", 
                       weight_history=weight_history, 
                       exercise_data=exercise_data,
                       health_advice=health_advice)
    
if __name__ == "__main__":
    app.run(debug=True)