import plotly.graph_objs as go
import plotly
import json
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import pickle
import secrets


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
x_data = []
y_item_count = []
y_total_cost = []
y_grand_total = []  # Initialize the list here

# Load inventory from file or initialize an empty dictionary
inventory_file = "inventory.pickle"
try:
    with open(inventory_file, "rb") as f:
        inventory = pickle.load(f)
        for name, details in inventory.items():
            details["price"] = float(details["price"])
except FileNotFoundError:
    inventory = {}


if os.path.isfile('budget.json'):
    # Load the budget from the file
    with open('budget.json', 'r') as f:
        try:
            budget = json.load(f)
        except json.JSONDecodeError:
            # Handle empty or invalid file
            budget = 0
else:
    # Initialize the budget variable to a default value
    budget = 0

# read data from json create new if not found
try:
    with open('data.json', 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    data = {}

# to get budget and draw line on chart
@app.route('/update_budget', methods=['POST'])
def update_budget():
    # Get the new budget value from the form data
    new_budget = request.form['budget']

    # Load the budget data from the JSON file
    with open('budget.json') as f:
        budget_data = json.load(f)

    # Update the budget value in the budget data
    budget_data['budget'] = int(new_budget.replace(",", ""))

    # Save the updated budget data to the JSON file
    with open('budget.json', 'w') as f:
        json.dump(budget_data, f)

    # Redirect back to the index page with the budget query parameter set
    return redirect(url_for('index', budget=new_budget))



# Define a custom Jinja2 filter for the round() function
@app.template_filter("round")
def _jinja2_filter_round(number, ndigits=0):
    return round(number, ndigits)

@app.route("/data")
def data():
    data = {"x": x_data[-1], "y": y_grand_total[-1]}
    return json.dumps(data)


# Define the sum function as a global variable
def my_sum(iterable):
    return sum(iterable)
app.jinja_env.globals.update(sum=my_sum)



@app.route("/")
def index():
    # Load x_data and y_grand_total from file
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
            x_data = data.get("x_data", [])
            y_grand_total = data.get("y_grand_total", [])
            last_inventory_state = data.get("last_inventory_state")
    except FileNotFoundError:
        x_data = []
        y_grand_total = []
        last_inventory_state = None

    # Check if inventory has changed since last update
    current_inventory_state = str(inventory)
    if current_inventory_state != last_inventory_state:
        # Calculate the grand total from the inventory
        grand_total = round(sum(details["price"] * details["quantity"] for details in inventory.values()), 2)

        # Add the current date/time and grand total to the data for the graph
        now = datetime.now()
        x_data.append(now.strftime("%m/%d/%Y %I:%M:%S %p"))
        y_grand_total.append(grand_total)

        # Update the last inventory state
        last_inventory_state = current_inventory_state

        # Write the updated data to the JSON file
        data = {"x_data": x_data, "y_grand_total": y_grand_total, "last_inventory_state": last_inventory_state}
        with open("data.json", "w") as f:
            json.dump(data, f)
    else:
        grand_total = y_grand_total[-1] if y_grand_total else 0

    # Load budget from file
    try:
        with open('budget.json', 'r') as f:
            budget_data = json.load(f)
            budget = budget_data.get("budget", 0)
    except FileNotFoundError:
        budget = 0

    # Create the real-time graph
    data = [{"x": x_data, "y": y_grand_total, "name": "Grand Total", "mode": "lines+markers", "marker": {"size": 5, "color": "blue"}, "line": {"width": 1}},
            {"x": x_data, "y": [budget] * len(x_data), "name": "Budget", "mode": "lines", "line": {"width": 1, "dash": "dash", "color": "gray"}}]
    layout = go.Layout(title="Spending Trend",
                       xaxis=dict(title="Date and Time", tickfont=dict(size=8)),
                       yaxis=dict(title="Grand Total", tickformat= "$, 2f"),
                       plot_bgcolor='rgb(125, 175, 200)',
                       paper_bgcolor='rgb(140, 180, 180)',
                       height=600,
                       width=625,
                       margin=dict(l=100))

    graphJSON = json.dumps({"data": data, "layout": layout}, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template("index.html", graphJSON=graphJSON, grand_total=grand_total, budget=budget)




@app.route("/add", methods=["GET", "POST"])
def add():
    # Load x_data and y_grand_total from file
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
            x_data = data.get("x_data", [])
            y_grand_total = data.get("y_grand_total", [])
    except FileNotFoundError:
        x_data = []
        y_grand_total = []

    if request.method == "POST":
        name = request.form["name"]
        price = float(request.form["price"])
        quantity = int(request.form["quantity"])
        if name in inventory:
            # Update quantity of existing item
            inventory[name]["quantity"] += quantity
        else:
            # Add new item to inventory
            inventory[name] = {"price": price, "quantity": quantity}
        with open(inventory_file, "wb") as f:
            pickle.dump(inventory, f)
        
        # Append the item's total cost and new grand total to the respective lists
        item_total_cost = round(price * quantity, 2)
        y_item_count.append(quantity)
        y_total_cost.append(item_total_cost)
        y_grand_total.append(round(sum(details["price"] * details["quantity"] for details in inventory.values()), 2))

        # Load existing data from file or initialize empty data
        try:
            with open('data.json', 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {"x_data": [], "y_grand_total": [], "last_inventory_state": None}
            
        # Add the current date/time to the x_data list
        now = datetime.now()
        x_data.append(now.strftime("%m/%d/%Y %I:%M:%S %p"))
        
        # Append the current date/time and new grand total to the existing data
        now = datetime.now()
        data["x_data"].append(now.strftime("%m/%d/%Y %I:%M:%S %p"))
        data["y_grand_total"].append(y_grand_total[-1])
        data["last_inventory_state"] = str(inventory)

        # Write the updated data to the JSON file
        with open("data.json", "w") as f:
            json.dump(data, f)

    # Update the graph layout
    layout = go.Layout(title="Inventory Statistics",
                       xaxis=dict(title="Date and Time"),
                       yaxis=dict(title="Grand Total"),
                        )

    # Create the traces for the item count, total cost and grand total
    item_count_trace = go.Bar(x=x_data, y=y_item_count, name="Item Count", marker=dict(color='blue'))
    total_cost_trace = go.Scatter(x=x_data, y=y_total_cost, name="Total Cost", mode="lines+markers", marker=dict(size=5, color='red'), line=dict(width=1))
    grand_total_trace = go.Scatter(x=x_data, y=y_grand_total, name="Grand Total", mode="lines+markers", marker=dict(size=5, color='green'), line=dict(width=1))
    data = [item_count_trace, total_cost_trace, grand_total_trace]
    
    # Create the graph with the data and layout
    graphJSON = json.dumps({"data": data, "layout": layout}, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template("add.html", graphJSON=graphJSON)



@app.route("/remove/<name>")
def remove(name):
    # Get the quantity to remove from the query string parameter
    qty_to_remove = request.args.get('qty', default=0, type=int)

    # Get the item from the inventory
    item = inventory.get(name)

    if item:
        # Validate the input
        if not 0 < qty_to_remove <= item['quantity']:
            flash('Invalid quantity.', 'error')
            return redirect(url_for('view'))

        # Update the item quantity and total cost
        item['quantity'] -= qty_to_remove
        item_total_cost = round(item['price'] * item['quantity'], 2)

        # If the item quantity is 0, remove the item from the inventory
        if item['quantity'] == 0:
            inventory.pop(name, None)
            flash(f'{name} removed from inventory.', 'success')
        else:
            flash(f'{qty_to_remove} {name} removed from inventory.', 'success')

        # Update the inventory file
        with open(inventory_file, 'wb') as f:
            pickle.dump(inventory, f)

        # Update the chart data
        y_grand_total.append(round(sum(details['price'] * details['quantity'] for details in inventory.values()), 2))
        y_item_count.append(item['quantity'])
        y_total_cost.append(item_total_cost)
        now = datetime.now()
        x_data.append(now.strftime('%m/%d/%Y %I:%M:%S %p'))

          # Load existing data from file or initialize empty data
        try:
            with open('data.json', 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {"x_data": [], "y_grand_total": [], "last_inventory_state": None}

            # Append the current date/time and new grand total to the existing data
        data["x_data"].append(now.strftime('%m/%d/%Y %I:%M:%S %p'))
        data["y_grand_total"].append(y_grand_total[-1])
        data["last_inventory_state"] = str(inventory)
    
        # Write the updated data to the JSON file
        with open('data.json', 'w') as f:
            json.dump(data, f)


    else:
        flash(f'{name} not found in inventory.', 'error')

    return redirect(url_for('view'))




      
# route to view html
@app.route("/view")
def view():
    # Retrieve query parameters for sorting order
    sort_by = request.args.get("sort_by", "name")
    sort_order = request.args.get("sort_order", "asc")

    # Sort the inventory based on the query parameters
    sorted_inventory = sorted(inventory.items(), key=lambda x: x[0].lower())
    if sort_by == "quantity":
        sorted_inventory = sorted(sorted_inventory, key=lambda x: x[1]["quantity"])
    elif sort_by == "price":
        sorted_inventory = sorted(sorted_inventory, key=lambda x: x[1]["price"])
    else:
        sorted_inventory = sorted_inventory[::-1]  # Sort by name in descending order
    if sort_order == "desc":
        sorted_inventory = reversed(sorted_inventory)

    item_totals = []
    for name, details in sorted_inventory:
        item_total = round(details["price"] * details["quantity"], 2)
        item_totals.append(item_total)
    total = round(sum(item_totals), 2)
    return render_template("view.html", inventory=sorted_inventory, total=total,
                           sort_by=sort_by, sort_order=sort_order)


# routes to search.html
@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        name = request.form["name"] # gets input
        filtered_inventory = {}
        for item_name, item_details in inventory.items(): 
            if name.lower() in item_name.lower(): # check if name exists
                filtered_inventory[item_name] = item_details # adds details
        print(filtered_inventory)#
        if filtered_inventory:
            item_total = 0
            for item in filtered_inventory.values():
                item_total += round(item["price"] * item["quantity"], 2)
            return render_template("search.html", name=name, details=filtered_inventory, total=item_total)
        else:
            message = "No matching items found"
            return render_template("search.html", message=message)
    else:
        return render_template("search.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)

