# Inventory Management Web App

This Flask web app allows users to manage an inventory of items. It supports the addition of new items, updating the quantity of existing items, viewing the current inventory, and searching for items by name. Additionally, the web app includes a budget tracking chart powered by Plotly.

## Dependencies

To run this web app, ensure you have the following dependencies installed:

- Flask==3.0.0
- gunicorn==21.2.0
- plotly==5.17.0
- Requests==2.31.0

You can install these dependencies using the `requirements.txt` file:

```
pip install -r requirements.txt
```

## Usage

To use the Inventory Management Web App:

1. **Clone the Repository**:
   ```
   git clone [repository_url]
   ```
   Replace `[repository_url]` with the URL of this repository.

2. **Navigate to the Repository**:
   ```
   cd path_to_repository
   ```
   Replace `path_to_repository` with the path to where you've cloned the repository.

3. **Install Dependencies**:
   ```
   pip install -r requirements.txt
   ```

4. **Run the App with Gunicorn**:
   ```
   gunicorn -b 127.0.0.1:9090 -w 1 main:app --log-level debug --access-logfile - --error-logfile -
   ```

5. **Access the Web App**:
   Open your favorite browser and navigate to `http://127.0.0.1:9090`.

---

Feel free to adjust or expand upon this content as needed. 
