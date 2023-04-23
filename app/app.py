from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template,
    current_app,
    jsonify,
)
import random

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy import Table, Column, Integer, ForeignKey

import datetime

import openai
import re

import subprocess
import os


def generate_tasks(
    list_name, list=None, num_tasks=10, num_seconds=60, difficulty=1, reflect=False
):
    full_prompt = f"""
Please respond as Badger AI.
Badger AI helps people (end users) accomplish their goals by breaking down themes, concepts or goals into small, actionable steps (action items) which can be done in {num_seconds} seconds or less.
Badger will provide action items that do not require many resources, existing knowledge or time, so that anyone can have a chance to complete them.
Respond only with the action item(s) separated by the pipe character (|). Do not include any other text in your response. Do not number the item(s) or use any other punctuation.\n\n
End user request: Please generate {num_tasks} action item(s) related to {list_name} that can be accomplished in {num_seconds} seconds or less.
"""
    # items = [item.description for item in list.items]
    # if len(items) > 0:
    #     full_prompt += f"\n\nDo not include the following items in your response: {', '.join(exclude)}."
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": full_prompt}],
    )

    response_raw = completion.choices[0].message.content
    response_split = response_raw.split("|")
    response_trimmed = [item.strip() for item in response_split]
    if reflect:
        for i, item in enumerate(response_trimmed):
            full_prompt = f"How long would you estimate the following task to take, in seconds? Respond with the number of seconds only.\n\n{item}"
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": full_prompt}],
            )
            print(
                "Original item:",
                item,
                "\nResponse: ",
                completion.choices[0].message.content,
            )
            # Select the first string of numbers from response with regex
            response_trimmed[i] = {
                "description": response_trimmed[i],
                "seconds": int(
                    re.search(r"\d+", completion.choices[0].message.content).group(0)
                ),
            }
    else:
        response_trimmed = [
            {"description": item, "seconds": 0} for item in response_trimmed
        ]

    return response_trimmed


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://phacend:phacend@localhost:5432/badger"
db = SQLAlchemy(app)
migrate = Migrate(app, db)
load_dotenv()
CORS(app)

import os
import openai


openai.api_key = os.getenv("OPENAI_API_KEY")


class List(db.Model):
    __tablename__ = "lists"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)

    items = db.relationship("Item", backref="list")

    active = db.Column(db.Boolean, nullable=False, default=True)
    task_every_secs = db.Column(db.Integer, nullable=False, default=900)
    task_length_secs = db.Column(db.Integer, nullable=False, default=60)
    difficulty = db.Column(db.Integer, nullable=False, default=1)  # 1 to 3
    start_hour_of_day = db.Column(db.Integer, nullable=False, default=8)
    end_hour_of_day = db.Column(db.Integer, nullable=False, default=20)


class Item(db.Model):
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(256), nullable=False)
    est_seconds = db.Column(db.Integer, nullable=True)

    list_id = db.Column(db.Integer, db.ForeignKey("lists.id"), nullable=False)


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    last_sent = db.Column(db.DateTime, nullable=False)


@app.route("/")
def index():
    lists = List.query.all()
    # Reverse lists
    lists = lists[::-1]
    return render_template("index.html", lists=lists)


@app.route("/list/new", methods=["POST"])
def new_list():
    name = request.form["name"]
    list = List(name=name)
    db.session.add(list)
    db.session.commit()
    # return redirect(url_for("new_list_splash"), list_id=new_list.id)
    tasks = generate_tasks(
        name, num_tasks=10, num_seconds=60, difficulty=1, reflect=False
    )
    for item in list.items:
        db.session.delete(item)
    for task in tasks:
        new_item = Item(
            description=task["description"],
            est_seconds=task["seconds"],
            list_id=list.id,
        )
        db.session.add(new_item)
    db.session.commit()
    return render_template("accordion_item.html", list=list)


@app.route("/list/<int:list_id>/generate_tasks", methods=["POST"])
def generate_list_tasks(list_id):
    list = List.query.get_or_404(list_id)
    tasks = generate_tasks(
        list.name, num_tasks=10, num_seconds=60, difficulty=1, reflect=False
    )
    for item in list.items:
        db.session.delete(item)
    for task in tasks:
        new_item = Item(
            description=task["description"],
            est_seconds=task["seconds"],
            list_id=list.id,
        )
        db.session.add(new_item)
    db.session.commit()
    return render_template("accordion_tasks.html", list=list)


@app.route("/list/<int:list_id>/delete", methods=["POST"])
def delete_list(list_id):
    list = List.query.get_or_404(list_id)
    for item in list.items:
        db.session.delete(item)
    db.session.delete(list)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/list/<int:list_id>/toggle_active", methods=["POST"])
def toggle_active(list_id):
    # update the active property of the list with the given id
    list = List.query.get_or_404(list_id)
    list.active = not list.active
    db.session.commit()
    return render_template("notification_toggle.html", list=list)


@app.route("/item/<int:item_id>/edit", methods=["POST"])
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    item.description = request.form["description"]
    db.session.commit()
    list = List.query.get_or_404(item.list_id)
    return render_template("accordion_tasks.html", list=list)


@app.route("/item/<int:item_id>/delete", methods=["POST"])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    list = List.query.get_or_404(item.list_id)
    return render_template("accordion_tasks.html", list=list)


@app.route("/get_random_item")
def random_notification():
    # Query the database for Items
    items = Item.query.all()
    # Select a random item
    if len(items) == 0:
        return jsonify(body=None)
    item = random.choice(items)
    # Return the item as JSON
    return jsonify(
        {
            "id": item.id,
            "title": item.list.name,
            "body": item.description,
            "image": "/static/img/badger-1.png",
            "badge": "/static/img/badger-1.png",
            "icon": "/static/img/badger-1.png",
        }
    )


from flask import make_response, send_from_directory


@app.route("/service-worker.js")
def sw():
    response = make_response(
        send_from_directory(
            "static", "service-worker.js", mimetype="application/javascript"
        )
    )
    # change the content header file. Can also omit; flask will handle correctly.
    response.headers["Content-Type"] = "application/javascript"
    return response


if __name__ == "__main__":
    app.run(debug=True)
