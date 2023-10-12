import plotly.graph_objs as go
import logging
import plotly
import json
from datetime import datetime
import requests
from flask import Flask, render_template, request, redirect, url_for, flash
import pickle
import secrets
import gunicorn.app.base
import os

# Retrieve the current date/time
response = requests.get('http://worldtimeapi.org/api/ip')
data = response.json()
now = datetime.fromisoformat(data['datetime'])

port = int(os.getenv('PORT', '8080'))


# Create gunicorn application
class StandaloneApplication(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items() if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


# Create Flask application
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Initialize data structures
x_data = []
y_item_count = []
y_total_cost = []
y_grand_total = []

inventory_file = "inventory.pickle"
try:
    with open(inventory_file, "rb") as f:
        inventory = pickle.load(f)
        for name, details in inventory.items():
            details["price"] = float(details["price"])
except FileNotFoundError:
    inventory = {}


# Load budget from file or initialize an empty one
def load_budget():
    try:
        with open('budget.json', 'r') as f:
            budget_data = json.load(f)
            # Ensure that the data read is a dictionary and that the "budget" key exists.
            return budget_data.get("budget", 0) if isinstance(budget_data, dict) else 0
    except (FileNotFoundError, json.JSONDecodeError):
        return 0


budget = load_budget()


@app.template_filter("round")
def _jinja2_filter_round(number, ndigits=0):
    return round(number, ndigits)


@app.route("/update_budget", methods=['POST'])
def update_budget():
    new_budget = request.form['budget']
    # Remove commas and try to convert the value to an integer
    try:
        sanitized_budget = int(new_budget.replace(",", ""))
    except ValueError:
        # If conversion fails, redirect to the index with an error message
        return redirect(url_for('index', error="Invalid budget value provided."))

    # If conversion is successful, save the new budget value
    with open('budget.json', 'w') as f:
        json.dump({'budget': sanitized_budget}, f)

    return redirect(url_for('index'))


@app.route("/")
def index():
    # Load data
    budget = load_budget()
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
            x_data = data.get("x_data", []) if isinstance(data, dict) else []
            y_grand_total = data.get("y_grand_total", []) if isinstance(data, dict) else []
    except (FileNotFoundError, json.JSONDecodeError):
        x_data, y_grand_total = [], []

    current_inventory_state = str(inventory)
    grand_total = 0

    # Check if the inventory is valid and not empty before processing
    if inventory and isinstance(inventory, dict):
        # Check if the last state of inventory differs from the current state
        if not x_data or current_inventory_state != data.get("last_inventory_state"):
            grand_total = sum(
                details["price"] * details["quantity"]
                for details in inventory.values()
                if details and isinstance(details, dict) and "price" in details and "quantity" in details
            )
            x_data.append(now.strftime("%m/%d/%Y %I:%M:%S %p"))
            y_grand_total.append(grand_total)
            with open("data.json", "w") as f:
                json.dump(
                    {"x_data": x_data, "y_grand_total": y_grand_total, "last_inventory_state": current_inventory_state},
                    f
                )
        elif y_grand_total:
            grand_total = y_grand_total[-1]
    else:
        grand_total = 0

    data_for_graph = [
        {"x": x_data, "y": y_grand_total, "name": "Grand Total", "mode": "lines+markers",
         "marker": {"size": 5, "color": "blue"}, "line": {"width": 1}},
        {"x": x_data, "y": [budget] * len(x_data), "name": "Budget", "mode": "lines",
         "line": {"width": 1, "dash": "dash", "color": "gray"}}
    ]
    layout = go.Layout(title="Spending Trend",
                       xaxis=dict(title="Date and Time", tickfont=dict(size=6)),
                       yaxis=dict(title="Grand Total", tickformat="$,.2f"),
                       plot_bgcolor='rgb(125, 175, 200)',
                       paper_bgcolor='rgb(140, 180, 180)',
                       hovermode="closest",
                       autosize=True,
                       xaxis_fixedrange=True,
                       yaxis_fixedrange=True,
                       height=600,
                       width=600,
                       margin=dict(l=100))

    graphJSON = json.dumps({"data": data_for_graph, "layout": layout}, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template("index.html", graphJSON=graphJSON, grand_total=grand_total, budget=budget)



@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        name = request.form["name"].title()
        price = float(request.form["price"])
        quantity = int(request.form["quantity"])
        grand_total = sum(details["price"] * details["quantity"] for details in inventory.values())
        if grand_total + price * quantity > budget:
            flash("Exceeds max budget.", "error")
        else:
            flash("Item added successfully!", "success")
            inventory[name] = inventory.get(name, {"price": price, "quantity": 0})
            inventory[name]["quantity"] += quantity
            with open(inventory_file, "wb") as f:
                pickle.dump(inventory, f)
            now = datetime.now()
            x_data.append(now.strftime("%m/%d/%Y %I:%M:%S %p"))
            y_grand_total.append(grand_total + price * quantity)
            with open("data.json", "w") as f:
                json.dump({"x_data": x_data, "y_grand_total": y_grand_total, "last_inventory_state": str(inventory)}, f)

    layout = go.Layout(title="Inventory Statistics",
                       xaxis=dict(title="Date and Time"),
                       yaxis=dict(title="Grand Total"))

    graphJSON = json.dumps({
        "data": [
            go.Bar(x=x_data, y=y_item_count, name="Item Count", marker=dict(color='blue')),
            go.Scatter(x=x_data, y=y_total_cost, name="Total Cost", mode="lines+markers",
                       marker=dict(size=5, color='red'), line=dict(width=1)),
            go.Scatter(x=x_data, y=y_grand_total, name="Grand Total", mode="lines+markers",
                       marker=dict(size=5, color='green'), line=dict(width=1))
        ],
        "layout": layout
    }, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template("add.html", graphJSON=graphJSON)


@app.route("/remove/<name>")
def remove(name):
    qty_to_remove = request.args.get('qty', default=0, type=int)
    item = inventory.get(name)

    if item and 0 < qty_to_remove <= item["quantity"]:
        item["quantity"] -= qty_to_remove
        if item["quantity"] == 0:
            inventory.pop(name)
            flash(f'{name} removed from inventory.', 'success')
        else:
            flash(f'{qty_to_remove} {name} removed from inventory.', 'success')
        with open(inventory_file, 'wb') as f:
            pickle.dump(inventory, f)
        now = datetime.now()
        x_data.append(now.strftime('%m/%d/%Y %I:%M:%S %p'))
        y_grand_total.append(sum(details['price'] * details['quantity'] for details in inventory.values()))
        with open("data.json", "w") as f:
            json.dump({"x_data": x_data, "y_grand_total": y_grand_total, "last_inventory_state": str(inventory)}, f)
    else:
        flash(f'{name} not found in inventory or invalid quantity.', 'error')
    return redirect(url_for('view'))


@app.route("/view")
def view():
    sort_by = request.args.get("sort_by", "name")
    sort_order = request.args.get("sort_order", "asc")

    sorted_inventory = sorted(inventory.items(), key=lambda x: x[0].lower())
    if sort_by == "quantity":
        sorted_inventory = sorted(sorted_inventory, key=lambda x: x[1]["quantity"])
    elif sort_by == "price":
        sorted_inventory = sorted(sorted_inventory, key=lambda x: x[1]["price"])
    if sort_order == "desc":
        sorted_inventory = reversed(sorted_inventory)

    return render_template("view.html", inventory=sorted_inventory,
                           total=sum(details["price"] * details["quantity"] for _, details in sorted_inventory),
                           sort_by=sort_by, sort_order=sort_order)


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        name = request.form["name"]
        filtered_inventory = {item_name: item_details for item_name, item_details in inventory.items() if
                              name.lower() in item_name.lower()}
        if filtered_inventory:
            item_total = sum(details["price"] * details["quantity"] for details in filtered_inventory.values())
            return render_template("search.html", name=name, details=filtered_inventory, total=item_total)
        else:
            return render_template("search.html", message="No matching items found")
    else:
        return render_template("search.html")


if __name__ == '__main__':
    bind = "127.0.0.1:9090"
    workers = 1
    loglevel = "debug"
    accesslog = "-"
    errorlog = "-"
    proc_name = "inventory-app"
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    gunicorn_config = {'bind': bind, 'workers': workers, 'loglevel': loglevel, 'accesslog': accesslog,
                       'errorlog': errorlog, 'proc_name': proc_name}
    StandaloneApplication(app, gunicorn_config).run()
