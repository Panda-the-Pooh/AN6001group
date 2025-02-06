from flask import Flask, render_template, request
import sqlite3
import google.generativeai as genai
import os
from datetime import datetime

# Flask 应用配置
app = Flask(__name__)

# 配置 genai API（用于计算饮食营养）
api = os.getenv('makersuite')
genai.configure(api_key = api)
model = genai.GenerativeModel("gemini-1.5-flash")

# 初始化 SQLite 数据库
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

# 主页 - 健康管理主界面
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# ========= 体重更新 & BMI 计算 =========

# 显示体重更新表单页面
@app.route("/update_weight_form", methods=["GET"])
def update_weight_form():
    return render_template("1_update_weight.html")

# 处理体重更新提交
@app.route("/update_weight", methods=["POST"])
def update_weight():
    weight = request.form.get("weight")
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO weight_history (date, weight) VALUES (?, ?)", (date, weight))
    conn.commit()
    conn.close()

    return render_template("dashboard.html", message="体重数据已更新！")

# ========= 运动数据提交 =========

# 显示运动数据表单页面
@app.route("/submit_exercise_form", methods=["GET"])
def submit_exercise_form():
    return render_template("2_submit_exercise.html")

# 处理运动数据提交
@app.route("/submit_exercise", methods=["POST"])
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

    return render_template("dashboard.html", message="运动数据已记录！")

# ========= 饮食数据提交 =========

# 显示饮食数据表单页面
@app.route("/submit_food_form", methods=["GET"])
def submit_food_form():
    return render_template("3_submit_food.html")

# 处理饮食数据提交 & 调用 OpenAI 计算热量
@app.route("/submit_food", methods=["POST"])
def submit_food():
    food_list = request.form.get("food_list")
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 存入数据库
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO food_data (date, food_list) VALUES (?, ?)", (date, food_list))
    conn.commit()
    conn.close()

    # 调用 Gemini 计算热量
    prompt = f"计算以下食物的总热量和营养比例（碳水/蛋白质/脂肪）：{food_list}"
    
    response = model.generate_content(prompt)
    
    # 获取 AI 返回的文本
    nutrition_result = response.text if response and response.text else "无法获取营养分析结果"

    return render_template("dashboard.html", message="饮食数据已记录！", nutrition_analysis=nutrition_result)

# ========= 生成健康报告 =========

@app.route("/generate_report", methods=["GET"])
def generate_report():
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()

    # 获取最近 7 天体重数据
    cursor.execute("SELECT date, weight FROM weight_history ORDER BY date DESC LIMIT 7")
    weight_history = cursor.fetchall()

    # 获取最近 7 天运动数据
    cursor.execute("SELECT date, heart_rate, steps, calories FROM exercise_data ORDER BY date DESC LIMIT 7")
    exercise_data = cursor.fetchall()

    conn.close()

    # 生成 AI 健康建议（基于历史数据）
    prompt = f"用户最近 7 天的体重变化: {weight_history}，运动数据: {exercise_data}。请提供整体健康分析，包括体重趋势、运动建议、饮食调整方案。"
    response = model.generate_content(prompt)
    
    health_advice = response.text if response and response.text else "无法获取营养分析结果"

    return render_template("health_report.html", 
                           weight_history=weight_history, 
                           exercise_data=exercise_data,
                           health_advice=health_advice)
    
if __name__ == "__main__":
    app.run(debug=True)