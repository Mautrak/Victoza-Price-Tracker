import re
import sqlite3
import requests
from datetime import datetime, date, timedelta
import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk

def adapt_date(date_obj):
    return date_obj.isoformat()
def convert_date(date_str):
    return datetime.strptime(date_str.decode('utf-8'), '%Y-%m-%d').date()

sqlite3.register_adapter(date, adapt_date)
sqlite3.register_converter("DATE", convert_date)

# Constants
URL1 = "https://liki24.com/uk/p/viktoza-r-r-d-6-mgml-kartridzh-vlozh-v-shpric-ruchku-3-ml-2-novo-nordisk/"
URL2 = "https://tabletki.ua/Виктоза/25550/"
XPATH1 = "/html/body/div[3]/div[1]/div[5]/div[2]/div[2]/div[3]/div[2]/div[1]/div[3]/span"
XPATH2 = "/html/body/div[2]/main/div[1]/div[1]/div[1]/article/div/div/section[1]/div/div[2]/div[1]/div[2]/div[1]/div[1]/span"
DB_FILE = "prices.db"

stop_event = threading.Event()

def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False
def wait_until_next_run():
    now = datetime.now()
    next_run = datetime(now.year, now.month, now.day, 11, 0) + timedelta(days=1)
    while datetime.now() < next_run:
        if stop_event.is_set():
            return
        time.sleep(60)
def get_price(driver, url, xpath):
    driver.get(url)
    price_text = driver.find_element(By.XPATH, xpath).text
    price = re.search(r'[\d\s]+[\.,]?\d*', price_text).group()
    price = price.replace(' ', '').replace(',', '.')
    return float(price)
def setup_db():
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drug TEXT,
        price REAL,
        price_change REAL,
        percentage_change REAL,
        site TEXT,
        date DATE
    )
    ''')
    conn.commit()
    conn.close()

def write_to_db(price, site):
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    # Check if there's already an entry for the current day
    today = datetime.now().date()
    cursor.execute("SELECT * FROM prices WHERE date = ?", (today,))
    existing_entry = cursor.fetchone()

    # Check for an entry from yesterday
    yesterday = today - timedelta(days=1)
    cursor.execute("SELECT * FROM prices WHERE date = ?", (yesterday,))
    yesterday_entry = cursor.fetchone()

    # Calculate price change and percentage change
    if yesterday_entry:
        price_change = price - yesterday_entry[2]
        percentage_change = (price_change / yesterday_entry[2]) * 100
    else:
        price_change = 0
        percentage_change = 0

    if existing_entry:
        cursor.execute("UPDATE prices SET price = ?, price_change = ?, percentage_change = ?, site = ? WHERE date = ?",
                       (price, price_change, percentage_change, site, today))
        print("Updated existing entry for today.")
    else:
        cursor.execute("INSERT INTO prices (drug, price, price_change, percentage_change, site, date) VALUES (?, ?, ?, ?, ?, ?)",
                       ('Victoza', price, price_change, percentage_change, site, today))
        print("Added new entry for today.")

    conn.commit()
    conn.close()

def fetch_from_db():
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prices")
    data = cursor.fetchall()
    conn.close()
    return data


def main():
    try:
        setup_db()  # Initialize the database
        while not stop_event.is_set():
            today = datetime.now().date()
            while not is_connected():
                print("No internet connection. Waiting...")
                time.sleep(60)

            options = FirefoxOptions()
            options.add_argument("--headless")
            driver = webdriver.Firefox(options=options)

            print("Connecting to URL1...")
            try:
                price1 = get_price(driver, URL1, XPATH1)
                print(f"Successfully reached URL1. Price found: {price1}")
            except Exception as e:
                print(f"Failed to get price from URL1: {e}")
                price1 = float('inf')

            print("Connecting to URL2...")
            try:
                price2 = get_price(driver, URL2, XPATH2)
                print(f"Successfully reached URL2. Price found: {price2}")
            except Exception as e:
                print(f"Failed to get price from URL2: {e}")
                price2 = float('inf')

            final_price = min(price1, price2)
            site_used = "Liki24" if final_price == price1 else "Tabletki"

            original_price = 4185.00
            if final_price <= original_price * 0.7:
                print("Alert: Price dropped significantly!")

            print("Updating the SQLite database with the price.")
            write_to_db(final_price, site_used)  # Store data in SQLite

            driver.quit()
            print("Done for today. Waiting until tomorrow.")
            wait_until_next_run()
    except KeyboardInterrupt:
        print("Script terminated by user. Cleaning up...")
        stop_event.set()
canvas_widget = None
def create_gui():
    root = tk.Tk()
    root.title("Price Tracker")

    tree = ttk.Treeview(root, columns=('Drug', 'Date', 'Site', 'Price', 'Price Change', 'Percentage Change'))
    tree.heading('#0', text='ID')
    tree.heading('#1', text='Drug')
    tree.heading('#2', text='Date')
    tree.heading('#3', text='Site')
    tree.heading('#4', text='Price')
    tree.heading('#5', text='Price Change')
    tree.heading('#6', text='Percentage Change')
    tree.pack(fill='both', expand=True)

    def plot_graph():
        data = fetch_from_db()
        # Get the current date
        today = datetime.now().date()
        # Calculate the date range: 5 weeks before and after the current date
        start_date = today - timedelta(weeks=5)
        end_date = today + timedelta(weeks=5)
        # Filter the data to only include entries within the date range
        filtered_data = [row for row in data if start_date <= row[6] <= end_date]
        # Extract dates and prices for the filtered data
        dates = [row[6] for row in filtered_data]
        prices = [row[2] for row in filtered_data]
        # Plot the data
        fig, ax = plt.subplots()
        ax.plot(dates, prices, marker='o', linestyle='-')
        ax.set_xlabel("Date")
        ax.set_ylabel("Price")
        ax.set_title("Price Trend")
        # Explicitly set x-axis limits
        ax.set_xlim([start_date, end_date])
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
        return fig
    def update_data():
        # Clear existing data from the treeview
        for row in tree.get_children():
            tree.delete(row)
        # Fetch and insert new data
        for row in fetch_from_db():
            tree.insert('', 'end', text=row[0], values=(row[1], row[6], row[5], row[2], row[3], f"{row[4]:.2f}%"))
        global canvas_widget  # Add this line
        if canvas_widget:
            canvas_widget.destroy()
        fig = plot_graph()
        canvas = FigureCanvasTkAgg(fig, master=root)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack()
        canvas.draw()
        plt.close(fig)

    def periodic_update():
        update_data()
        root.after(10000, periodic_update)

    def on_closing():
        print("Closing GUI...")
        stop_event.set()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    update_data_button = ttk.Button(root, text="Update Data", command=update_data)
    update_data_button.pack()

    # Call periodic_update once to start the periodic updates
    periodic_update()

    root.mainloop()

if __name__ == "__main__":
    try:
        threading.Thread(target=main).start()
        create_gui()
    except KeyboardInterrupt:
        print("Script terminated by user. Cleaning up...")
        stop_event.set()