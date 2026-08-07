from flask import Flask, render_template, request, redirect, session, Response
import sqlite3
import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image
from datetime import datetime

app = Flask(__name__)
app.secret_key = "kakeibo_secret"

conn = sqlite3.connect("expenses.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    amount INTEGER,
    category TEXT,
    expense_date TEXT
)
""")

conn.commit()



@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "1234":

            session["user"] = username

            return redirect("/")

    return render_template("login.html")


@app.route("/", methods=["GET", "POST"])
def home():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        name = request.form.get("name")
        amount = request.form.get("amount")
        category = request.form.get("category")
        expense_date = request.form.get("expense_date")

        if name and amount:

            cursor.execute(
    "INSERT INTO expenses (name, amount, category, expense_date) VALUES (?, ?, ?, ?)",
    (name, amount, category, expense_date)
)

            conn.commit()

        return redirect("/")

    search = request.args.get("search", "")

    if search:

        cursor.execute(
            "SELECT * FROM expenses WHERE name LIKE ?",
            ("%" + search + "%",)
        )

    else:

        cursor.execute("SELECT * FROM expenses")

    expenses = cursor.fetchall()

    total = 0
    budget = 100000

    for item in expenses:
        total += item[2]

    remaining = budget - total

    warning = ""
    ai_advice = ""

    if total >= budget:
        warning = "🚨 Budget Exceeded!"

    elif total >= (budget * 0.8):
        warning = "⚠️ Warning! Budget almost reached."

    categories = {}

    for item in expenses:

        category = item[3]

        if category in categories:
            categories[category] += item[2]
        else:
            categories[category] = item[2]

    top_category = "None"
    food_total = categories.get("Food", 0)
    transport_total = categories.get("Transport", 0)
    shopping_total = categories.get("Shopping", 0)
    bills_total = categories.get("Bills", 0)
    other_total = categories.get("Other", 0)
    average_expense = 0

    if len(expenses) > 0:
        average_expense = total / len(expenses)

    highest_expense = 0
    highest_expense_name = "None"

    for item in expenses:

        if item[2] > highest_expense:
            highest_expense = item[2]
            highest_expense_name = item[1]

    if categories:

        top_category = max(
            categories,
            key=categories.get
        )

    if total > 0:

        food_amount = categories.get("Food", 0)
        shopping_amount = categories.get("Shopping", 0)
        bills_amount = categories.get("Bills", 0)

        if food_amount > (total * 0.5):

            ai_advice = "🤖 AI Advice: Food expenses are high. Try reducing restaurant or snack spending."

        elif shopping_amount > (total * 0.4):

            ai_advice = "🤖 AI Advice: Shopping expenses are high this month. Consider delaying non-essential purchases."

        elif bills_amount > (total * 0.5):

            ai_advice = "🤖 AI Advice: Most of your spending is on bills and fixed costs."

        elif remaining < (budget * 0.2):

            ai_advice = "🤖 AI Advice: You have used most of your budget. Spend carefully."

        else:

            ai_advice = "🤖 AI Advice: Your spending is currently balanced."
    plt.clf()

    plt.pie(
        categories.values(),
        labels=categories.keys(),
        autopct="%1.1f%%"
    )

    plt.title("Expenses by Category")

    if not os.path.exists("static"):
        os.makedirs("static")
    plt.savefig("static/chart.png")
    trend_data = {}

    for item in expenses:

        date = item[4]

        if date in trend_data:
            trend_data[date] += item[2]
        else:
            trend_data[date] = item[2]

    plt.clf()

    plt.plot(
        list(trend_data.keys()),
        list(trend_data.values()),
        marker="o"
    )

    plt.title("Daily Expense Trend")
    plt.xlabel("Date")
    plt.ylabel("Amount (¥)")

    plt.xticks(rotation=45)

    plt.tight_layout()

    plt.savefig("static/trend_chart.png")
    print("Remaining =", remaining)
    print("Progress =", max(0, min(100, int((remaining / 20000) * 100))))
    
    return render_template(
    "index.html",
    expenses=expenses,
    total=total,
    budget=budget,
    remaining=remaining,
    top_category=top_category,
    food_total=food_total,
    transport_total=transport_total,
    shopping_total=shopping_total,
    bills_total=bills_total,
    other_total=other_total,
    search=search,
    warning=warning,
    ai_advice=ai_advice,
    average_expense=average_expense,
    highest_expense=highest_expense,
    highest_expense_name=highest_expense_name,
    savings_goal=20000,
    current_savings=remaining,
    savings_progress=round((remaining / budget) * 100, 1)
)

@app.route("/delete/<int:index>")
def delete(index):

 cursor.execute(
        "DELETE FROM expenses WHERE id = ?",
        (index,)
    )

 conn.commit()

 return redirect("/")


@app.route("/japanese")
def japanese():

    cursor.execute("SELECT * FROM expenses")
    expenses = cursor.fetchall()

    total = 0
    budget = 100000

    for item in expenses:
        total += item[2]

    remaining = budget - total

    warning = ""

    if total >= budget:

        warning = "🚨 Budget Exceeded!"

    elif total >= (budget * 0.8):

        warning = "⚠️ Warning! Budget almost reached."

    return render_template(
        "japanese.html",
        expenses=expenses,
        total=total,
        budget=budget,
        remaining=remaining,
        warning=warning
    )
@app.route("/export")
def export():

    cursor.execute("SELECT * FROM expenses")
    expenses = cursor.fetchall()

    csv_data = "Date,Name,Amount,Category\n"

    for item in expenses:

        csv_data += f"{item[4]},{item[1]},{item[2]},{item[3]}\n"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=expenses.csv"
        }
    )
@app.route("/pdf")
def pdf():

    cursor.execute("SELECT * FROM expenses")
    expenses = cursor.fetchall()

    total = 0
    budget = 100000

    for item in expenses:
        total += item[2]

    remaining = budget - total

    average_expense = 0

    if len(expenses) > 0:
        average_expense = round(total / len(expenses), 2)

    highest_expense = 0
    highest_expense_name = "None"

    for item in expenses:
        if item[2] > highest_expense:
            highest_expense = item[2]
            highest_expense_name = item[1]

    categories = {}

    for item in expenses:
        category = item[3]

        if category in categories:
            categories[category] += item[2]
        else:
            categories[category] = item[2]

    top_category = "None"

    if categories:
        top_category = max(categories, key=categories.get)
        doc = SimpleDocTemplate("report.pdf")

    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph("Kakeibo AI Monthly Report", styles["Title"]))
    today = datetime.now().strftime("%Y-%m-%d")

    story.append(
    Paragraph(f"Generated on: {today}", styles["BodyText"])
)


    story.append(Paragraph("<br/>", styles["BodyText"]))

    story.append(Paragraph(f"Budget : ¥{budget}", styles["BodyText"]))
    story.append(Paragraph(f"Total Expenses : ¥{total}", styles["BodyText"]))
    story.append(Paragraph(f"Remaining : ¥{remaining}", styles["BodyText"]))
    story.append(Paragraph(f"Average Expense : ¥{average_expense}", styles["BodyText"]))
    story.append(Paragraph(f"Highest Expense : {highest_expense_name} (¥{highest_expense})", styles["BodyText"]))
    story.append(Paragraph(f"Top Category : {top_category}", styles["BodyText"]))

    story.append(Paragraph("<br/>", styles["BodyText"]))

    if os.path.exists("static/chart.png"):
        story.append(Image("static/chart.png", width=4*inch, height=4*inch))

    if os.path.exists("static/trend_chart.png"):
        story.append(Image("static/trend_chart.png", width=5*inch, height=3*inch))
        story.append(Paragraph("<br/><br/>", styles["BodyText"]))

    story.append(
    Paragraph("Generated by Kakeibo AI", styles["BodyText"])
)

    story.append(
    Paragraph("Developed by Iresha Dhanandani", styles["BodyText"])
)

    doc.build(story)
    return Response(
        open("report.pdf", "rb"),
        mimetype="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=Kakeibo_Report.pdf"
        }
    )

@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect("/login")

app.run(debug=True)