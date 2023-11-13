# Evaluates and analyses net worth and track how it fairs when taking into account the world current top 10 currencies. Userassets here only include trading stock and financial credit.

import os

from cs50 import SQL
from datetime import datetime
from decimal import *
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from utilities import apology, login_required, currency_rate, stock_lookup, KWD_money, BHD_money, OMR_money, JOD_money, GBP_money, GIP_money, KYD_money, CHF_money, EUR_money, USD_money, validate_DOB
from werkzeug.security import check_password_hash, generate_password_hash


# Application configuration
app = Flask(__name__)

# Custom money formatting filter
app.jinja_env.filters["kwd"] = KWD_money
app.jinja_env.filters["bhd"] = BHD_money
app.jinja_env.filters["cmr"] = OMR_money
app.jinja_env.filters["jod"] = JOD_money
app.jinja_env.filters["gbp"] = GBP_money
app.jinja_env.filters["gip"] = GIP_money
app.jinja_env.filters["kyd"] = KYD_money
app.jinja_env.filters["chf"] = CHF_money
app.jinja_env.filters["eur"] = EUR_money
app.jinja_env.filters["usd"] = USD_money


# COOKIES SETTINGS: Use filesystem store cookies settings. This data will be store in data for production.
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Connect to the database.
db = SQL("sqlite:///tradewiser.db")


# Disable CACHE
@app.after_request
def after_request(response):
    """Applies no CASHE policy on responses, i.e. responses will not be cached"""

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Summary Report"""

    CURRENT_USER = session["user_id"]
    total_holdings = 0

    balance = db.execute("SELECT funds FROM users where id = ?", CURRENT_USER)[0]["funds"]
    stock_movement = db.execute("SELECT * FROM stock WHERE owner = ?", CURRENT_USER)
    if len(stock_movement) == 0:
        return render_template("index.html", net=balance, balance=balance, total_holdings=total_holdings)

    for row in stock_movement:
        # Get current price. New price is remains as previous if no price update
        stock_lookup_update = stock_lookup(row["symbol"])
        updated_price = stock_lookup_update["price"]
        row["price"] = updated_price

        shares = int(row["num_shares"])

        # Deduct holdings per stock
        holdings = updated_price * shares
        row["holdings"] = holdings

        # Accumulate the total holdings
        total_holdings += holdings

    # Inform user when currency data is unavailable from API provider.
    if currency_rate("EUR") == None:
        flash(f"ATTENTION: Currency data not up to date. Please check with API povider")
    net = balance + total_holdings
    return render_template("index.html", net=net, balance=balance, total_holdings=total_holdings)


@app.route("/trading")
@login_required
def trading():
    """ A list of trading acting for the month """

    CURRENT_USER = session["user_id"]
    total_holdings = 0
    stock_movement = db.execute("SELECT * FROM trading WHERE owner = ? and date  > DATETIME('now', 'start of month')", CURRENT_USER)
    for row in stock_movement:
        # Get current price. New price is remains as previous if no price update
        stock_lookup_update = stock_lookup(row["symbol"])
        updated_price = stock_lookup_update["price"]
        row["price"] = updated_price

        shares = int(row["num_shares"])

        # Deduct holdings per stock
        holdings = updated_price * shares
        row["holdings"] = holdings

        # Accumulate the total holdings
        total_holdings += holdings

    return render_template("trading.html", stock_movement=stock_movement, total_holdings=total_holdings)


@app.route("/finance")
@login_required
def finance():
    """ A list of financial transactions for the month """

    CURRENT_USER = session["user_id"]
    finance = db.execute("SELECT * FROM finance WHERE owner = ? and date  >= DATETIME('now', 'start of month')", CURRENT_USER)
    balance = db.execute("SELECT funds FROM users where id = ?", CURRENT_USER)[0]["funds"]

    return render_template("finance.html", finance=finance, balance=balance)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register User"""
    now = datetime.now()
    # current_dateTime = datetime.timestamp(now)
    current_dateTime = datetime.now()

    # POST REQUEST: Process User registration
    if request.method == "POST":
        # Acquire user entry
        username = request.form.get("username").strip()
        firstname = request.form.get("firstname").strip()
        middlenames = request.form.get("middlenames").strip()
        lastname = request.form.get("lastname").strip()
        initial_credit = request.form.get("initialCredit")
        birthday = request.form.get("birthday")
        if validate_DOB(birthday) == "Invalid":
            return apology("Invalid date of birth.")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        users = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(users) != 0:
            return apology("This username is taken. Please try something different.")
        elif not username or not firstname or not lastname or not birthday or not password or not confirmation:
            return apology("All fields marked with * must be filled")
        elif password != confirmation:
            return apology("Ensure password confirmation matches with password.")

        pw_hash = generate_password_hash(password)

        db.execute("INSERT INTO users (creation_date, username, firstname, lastname, middlenames, born, pw_hash, funds) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   current_dateTime, username, firstname, lastname, middlenames, birthday, pw_hash, initial_credit)

        # Update balance table
        id = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]
        db.execute(
            "INSERT INTO balance (owner, funds, stock, net_worth) VALUES (?, ?, ?, ?)",
            id,
            initial_credit,
            0,
            initial_credit
        )

        # Record transaction: Update finance table
        db.execute(
            "INSERT INTO finance (date, owner, type, amount, running_balance) VALUES (?, ?, ?, ?, ?)",
                current_dateTime,
                id,
                "INITIAL DEPOSIT",
                initial_credit,
                initial_credit
        )

        return redirect("/login")

    # GET Request: Redirect user to registration form
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log User in"""

    # Forget any previous session
    session.clear()

    # POST request: Authenticate user
    if request.method == "POST":
        # Acquire Userlogin credentials & Validate
        username = request.form.get("username").strip()
        if not username:
            return apology("Invalid username and/or password", 403)
        password = request.form.get("password")
        if not password:
            return apology("Invalid username and/or password", 403)
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        pw_hash = rows[0]["pw_hash"]
        if len(rows) != 1 or not check_password_hash(pw_hash, password):
            return apology("Invalid username and/or password", 403)

        # Set Cookie to remember User. Usermay get access now. Redirect Userto home page
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]
        return redirect("/")

    # GET request: Usermust first authenticate to login.
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Log Userout"""

    # CLEAR COOKIES: Forget & Redirect to login route
    session.clear()
    return redirect("/")


@app.route("/search")
def search():
    q = request.args.get("q")
    if q:
        yahoofinance = db.execute("SELECT * FROM yahoofinance WHERE symbol LIKE ? LIMIT 50", "%" + q + "%")
    else:
        shows = []
    return jsonify(shows)


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get Stock Quotation."""

    # POST REQUEST: Get user's request and return quote
    companies = db.execute("SELECT * FROM yahoofinance")
    if request.method == "POST":
        symbol = request.form.get("symbol").strip()
        quote = stock_lookup(symbol)
        if not symbol:
            return apology("You must enter a stock symbol.")
        elif not quote:
            return apology(f"Stock data not available for {symbol}")

        # Returns quote. codDisplays alert if currency API provider has returns an exception
        if currency_rate("EUR") == None:
            flash(f"ATTENTION: Currency data not up to date. Please check with API povider")
        return render_template("quote.html", quote=quote, companies=companies)

    return render_template("quote.html", companies=companies)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy Stock Shares"""

    CURRENT_USER = session["user_id"]
    current_dateTime = datetime.now()
    companies = db.execute("SELECT * FROM yahoofinance")

    # POST REQUEST: Get user's request and process stock purchase.
    if request.method == "POST":
        # Get user's request.
        symbol = request.form.get("symbol").upper().strip()
        if len(symbol) == 0:
            return apology("Invalid Symbol.")
        if not symbol:
            return apology("Invalid: Field cannot be empty. Please enter a valid stock symbol.")
        num_shares = request.form.get("shares").strip()
        if not num_shares or not num_shares.isdigit() or int(num_shares) <= 0:
            return apology("Invalid: Number of share must be a positive integer. Field cannot be empty.")

        # Get current stock data.
        stock_update = stock_lookup(symbol)
        if not stock_update:
            return apology(f"Stock data not available for {symbol}")

        # Record user request
        stock_name = stock_update["name"]
        stock_price = stock_update["price"]
        amount = stock_price * int(num_shares)

        # Get user balance & check for sufficient funds
        funds = db.execute("SELECT funds FROM users WHERE id = ?", CURRENT_USER)[0]["funds"]
        if funds < stock_price:
            return apology("You have insuficienct funds in this account", 409)

        # Update balance in users & balance tables.
        shares = int(num_shares)
        new_balance = funds - stock_update["price"] * shares
        db.execute("UPDATE users SET funds = ? WHERE id = ?", new_balance, CURRENT_USER)
        db.execute("UPDATE balance SET funds = ? WHERE owner = ?", new_balance, CURRENT_USER)

        # Update stock table
        db.execute(
            "INSERT INTO stock (date, name, symbol, num_shares, owner, price) VALUES (?, ?, ?, ?, ?, ?)",
            current_dateTime,
            stock_name,
            symbol,
            shares,
            CURRENT_USER,
            stock_price,
        )

        # Compute the new value for stock, and update the balance table.
        current_stock = db.execute(
            "SELECT stock FROM (SELECT owner, SUM(total) AS stock FROM (SELECT owner, num_shares * price AS total FROM stock) GROUP BY owner) WHERE owner = ?", CURRENT_USER
        )[0]["stock"]
        db.execute("UPDATE balance SET stock = ? WHERE owner = ?", current_stock, CURRENT_USER)

        # Record transaction
        db.execute(
            "INSERT INTO trading (date, owner, type, symbol, name, num_shares, price, running_balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            current_dateTime,
            CURRENT_USER,
            "BUY STOCK",
            symbol,
            stock_name,
            shares,
            stock_price,
            new_balance,
        )

        # Update finance table
        db.execute("INSERT INTO finance (date, owner, type, amount, running_balance) VALUES (?, ?, ?, ?, ?)",
                    current_dateTime,
                    CURRENT_USER,
                    "BUY STOCK",
                    amount,
                    new_balance
                   )

        # Redirect to user home page and display a transaction confirmation message.
        flash(
            f"You bought {shares} shares of {symbol} at {USD_money(stock_price)} each!"
        )
        return redirect("/")

    # GET REQUEST: Redirect user to fill in purchase form.
    return render_template("buy.html", companies=companies)


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell stock shares"""
    CURRENT_USER = session["user_id"]
    current_dateTime = datetime.now()

    # POST REQUEST: Get user's request. Validate & process sale transactions
    if request.method == "POST":
        symbol = request.form.get("symbol")
        sell_shares = request.form.get("shares")
        try:
            sell_shares = int(sell_shares)
        except ValueError:
            return apology("You must enter a positive integer for shares")
        name = request.form.get("name")

        # Get current price
        price = stock_lookup(symbol)["price"]
        amount = sell_shares * price

        # Get current balance to check for sufficient funds
        current_balance = db.execute(
            "SELECT funds FROM users WHERE id = ?", CURRENT_USER
        )[0]["funds"]
        cost = price * sell_shares

        shares = db.execute(
            "SELECT shares FROM (SELECT symbol, SUM(num_shares) AS shares FROM stock WHERE owner = ? GROUP BY symbol) WHERE symbol = ?",
            CURRENT_USER,
            symbol,
        )[0]["shares"]

        if (
            not symbol
            or not sell_shares
            or int(sell_shares) <= 0
            or int(sell_shares) >= shares
            or current_balance < cost
        ):
            return apology("Please select a stock option and a positive integer value for shares to sell.\nCheck that you have enough shares to sell\n and that you have sufficient funds."
            )

        # Update database with sale record
        quote_update = stock_lookup(symbol)
        if not quote_update:
            return apology(
                f"Data not available for {quote_update['symbol']}", 404
            )
        price = quote_update["price"]
        name = quote_update["name"]
        deduce_shares = (-1) * sell_shares
        db.execute(
            "INSERT INTO stock (date, name, symbol, num_shares, owner, price) VALUES (?, ?, ?, ?, ?, ?)",
            current_dateTime,
            name,
            symbol,
            deduce_shares,
            CURRENT_USER,
            price,
        )

        # Update balance in users & balance tables.
        new_balance = current_balance + sell_shares * price
        db.execute("UPDATE users SET funds = ? WHERE id = ?", new_balance, CURRENT_USER)
        db.execute("UPDATE balance SET funds = ? WHERE owner = ?", new_balance, CURRENT_USER)

        # Compute the current stock total, and update the balance table.
        current_stock = db.execute(
            "SELECT stock FROM (SELECT owner, SUM(total) AS stock FROM (SELECT owner, num_shares * price AS total FROM stock) GROUP BY owner) WHERE owner = ?",
            CURRENT_USER
        )[0]["stock"]
        db.execute("UPDATE balance SET stock = ? WHERE owner = ?", current_stock, CURRENT_USER)

        # Record transaction to database
        db.execute(
            "INSERT INTO trading (date, owner, type, symbol, name, num_shares, price, running_balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            current_dateTime,
            CURRENT_USER,
            "SELL",
            symbol,
            name,
            sell_shares,
            price,
            new_balance,
        )

        # Update finance table
        db.execute("INSERT INTO finance (date, owner, type, amount, running_balance) VALUES (?, ?, ?, ?, ?)",
                    current_dateTime,
                    CURRENT_USER,
                    "STOCK SALE",
                    amount,
                    new_balance
                   )
        # Redirect to user home page and display a transaction confirmation message.
        flash(
            f"You've just deposited {USD_money(amount)}!"
        )

        flash(
            f"Sold {sell_shares} of {symbol} at {USD_money(price)} per share!"
        )
        return redirect("/")

    # Populate stock options in template to match with user's existing stock and pass on to template.
    symbols = db.execute(
        "SELECT DISTINCT symbol FROM stock WHERE owner = ?", CURRENT_USER
    )

    # GET REQUEST: Redirect user to submit sell form
    return render_template("sell.html", symbols=symbols)


@app.route("/tradewiser")
@login_required
def tradewiser():

    return render_template("tradewiser.html")


@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    """Deposit Funds"""

    CURRENT_USER = session["user_id"]
    current_dateTime = datetime.now()

    if request.method == "POST":
        amount = request.form.get("deposit")
        try:
            amount = float(amount)
        except ValueError:
            return apology("Amount must be a positive decimal greater than 0.")
        if not amount or amount <= 0:
            return apology("Field cannot be empty.")

        # Update user's balance.
        funds = db.execute("SELECT funds FROM users WHERE id = ?", CURRENT_USER)[0]["funds"]
        new_balance = funds + amount
        db.execute("UPDATE users SET funds = ? WHERE id =?", new_balance, CURRENT_USER)
        db.execute("UPDATE balance SET funds = ? WHERE owner = ?", new_balance, CURRENT_USER)

        # Update finance table
        db.execute("INSERT INTO finance (date, owner, type, amount, running_balance) VALUES (?, ?, ?, ?, ?)",
                    current_dateTime,
                    CURRENT_USER,
                    "DEPOSIT",
                    amount,
                    new_balance
                   )
        # Redirect to user home page and display a transaction confirmation message.
        flash(
            f"You've just deposited {USD_money(amount)}!"
        )
        return redirect("/")

    # GET REQUEST: Redirect user to deposit form
    return render_template("/deposit.html")


@app.route("/withdraw", methods = ["GET", "POST"])
@login_required
def withdraw():
    """ Withdraw case from funds """

    CURRENT_USER = session["user_id"]
    current_dateTime = datetime.now()

    # POST REQUEST: Process withdrawl
    if request.method == "POST":
        amount = request.form.get("withdraw")
        try:
            amount = float(amount)
        except ValueError:
            return apology("Amount must be a positive decimal greater than 0.")
        if not amount or amount <= 0:
            return apology("Invalid: Field cannot be empty. Amount must be > 0.")

        # Check for sufficient funds
        funds = db.execute("SELECT funds FROM users WHERE id = ?", CURRENT_USER)[0]["funds"]
        if funds < amount:
            return apology("You do not have enough funds for this transaction")

        new_balance = funds - amount

        # Update the database.
        db.execute("UPDATE users SET funds = ? WHERE id = ?", new_balance, CURRENT_USER)
        db.execute("UPDATE balance SET funds = ? WHERE owner = ?", new_balance, CURRENT_USER)

        # Update finance table
        db.execute("INSERT INTO finance (date, owner, type, amount, running_balance) VALUES (?, ?, ?, ?, ?)",
                    current_dateTime,
                    CURRENT_USER,
                    "WITHDRAWAL",
                    amount,
                    new_balance
                   )
        # Redirect to user home page and display a transaction confirmation message.
        flash(
            f"You've just withdrawn {USD_money(amount)}!"
        )
        return redirect("/")

    return render_template("withdraw.html")


@app.route("/transactions")
def transactions():
    """
    Show all combined transactions: Deposit, Widthdrawls, Buy, Sales.

    IMPORTANT: The resulted table should be a UNION table that combines both stock & finance tables. However, SQLite does not support such operation.
    Using a JOIN statement only to have data to fill in this section for the purpose of CS50 final project submission.

    """

    CURRENT_USER = session["user_id"]
    transactions = db.execute("WITH user_finance AS (SELECT f.id, f.date, f.owner, f.type, f.amount, f.running_balance FROM finance AS f JOIN trading AS t ON f.id = f.id WHERE f.owner = ?) SELECT DISTINCT * FROM user_finance", CURRENT_USER)

    return render_template("transactions.html", transactions=transactions)


@app.route("/watch")
def watch():
    """ A page with a summary report with live currency and stock data """

    user = session["user_id"]
    balance = db.execute("SELECT * FROM balance WHERE owner = ?", user)
    return render_template("watch.html", balance=balance)
