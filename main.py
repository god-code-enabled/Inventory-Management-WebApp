from flask import Flask, render_template, request, redirect, url_for
import pickle

app = Flask(__name__)

# Load inventory from file or initialize an empty dictionary
inventory_file = "inventory.pickle"
try:
    with open(inventory_file, "rb") as f:
        inventory = pickle.load(f)
        for name, details in inventory.items():
            details["price"] = float(details["price"])
except FileNotFoundError:
    inventory = {}

# Define a custom Jinja2 filter for the round() function
@app.template_filter("round")
def _jinja2_filter_round(number, ndigits=0):
    return round(number, ndigits)

# Define the sum function as a global variable
def my_sum(iterable):
    return sum(iterable)
app.jinja_env.globals.update(sum=my_sum)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/add", methods=["GET", "POST"])
def add():
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
        return redirect(url_for("view"))
    return render_template("add.html")

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




@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        name = request.form["name"]
        filtered_inventory = {}
        for item_name, item_details in inventory.items():
            if name.lower() in item_name.lower():
                filtered_inventory[item_name] = item_details
        print(filtered_inventory)
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
