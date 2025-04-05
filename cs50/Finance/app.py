import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


# def lookup(symbol):
#     """Look up quote for symbol."""

#     if symbol == 'IBM':
#         return {"price": 189.12, "symbol": 'IBM'}
#     elif symbol == 'TYO':
#         return {"price": 12.62, "symbol": 'TYO'}
#     else:
#         return None  # or handle other cases


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks = db.execute("SELECT * FROM stocks WHERE user_id = ?", session["user_id"])
    total_stock = 0.0
    for stock in stocks:
        total_stock += float(stock["total"])
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])[0]
    return render_template('index.html', stocks=stocks, total_stock=total_stock, user=user)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)

        # Ensure shares was submitted
        elif not request.form.get("shares"):
            return apology("must provide shares", 403)

        # Get the symbol and shares after make sure they submitted
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        share_data = lookup(symbol)

        # Ensure the symbol is valid
        if share_data is None:
            return apology("Invalid symbol", 400)

        # Ensure fractional, negative and non numeric shares can't passed through
        if not shares.isnumeric():
            return apology("Invalid shares", 400)

        # Ensure the shares is valid
        if int(shares) < 1:
            return apology("Invalid shares", 400)

        # get the stock price and total
        price = float(share_data['price'])
        total = price * float(shares)

        # check for the user data especially the user cash
        user_data = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        user_cash = user_data[0]["cash"]

        # ensure the user actually have the money to buy the shares stock
        if user_cash < total:
            return apology("Can't Afford", 400)

        # check for the stock table
        check_stock_table = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = 'stocks'")

        # ensure the table exists
        if not check_stock_table:
            db.execute("CREATE TABLE IF NOT EXISTS stocks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, symbol TEXT NOT NULL, shares INTEGER NOT NULL, price NUMERIC NOT NULL, total NUMERIC NOT NULL, FOREIGN KEY (user_id) REFERENCES users (id));")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_symbol ON stocks (user_id, symbol);")

        stock_data = db.execute(
            "SELECT * FROM stocks WHERE user_id = ? AND symbol = ?", session["user_id"], symbol)
        print(stock_data)

        if not stock_data:
            # insert new stocks data if the users doesn't have
            db.execute("INSERT INTO stocks (user_id, symbol, shares, price, total) VALUES(?, ?, ?, ?, ?)",
                       session["user_id"], symbol, shares, price, total)
        else:
            # update new stock data
            old_share = stock_data[0]["shares"]
            old_total = stock_data[0]["total"]
            db.execute("UPDATE stocks SET shares=?, total=? WHERE user_id=? AND symbol=?", int(
                old_share) + int(shares), float(old_total) + float(total), session["user_id"], symbol)

        # check for the histories table
        check_histories_table = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = 'histories'")

        # ensure the table exists
        if not check_histories_table:
            db.execute("CREATE TABLE IF NOT EXISTS histories (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, symbol TEXT NOT NULL, type TEXT NOT NULL, shares INTEGER NOT NULL, price NUMERIC NOT NULL,  total NUMERIC NOT NULL, transacted TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES users (id));")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_symbol ON histories (user_id, symbol);")

        history_data = db.execute(
            "SELECT * FROM histories WHERE user_id = ?", session["user_id"])
        print(history_data)

        transacted = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

        # add histories data
        db.execute("INSERT INTO histories (user_id, symbol, type, shares, price, total, transacted) VALUES(?, ?, ?, ?, ?, ?, ?)",
                   session["user_id"], symbol, 'bought', shares, price, total, transacted)

        # subtract the user money after buying the shares
        db.execute("UPDATE users SET cash=? WHERE id = ?", user_cash - total, session["user_id"])

        flash('Bought!')

        # Redirect user to home page
        return redirect('/')

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        print(db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = 'stocks'"))
        return render_template('buy.html')


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # check for the histories table
    check_histories_table = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = 'histories'")

    # ensure the table exists
    if not check_histories_table:
        db.execute("CREATE TABLE IF NOT EXISTS histories (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, symbol TEXT NOT NULL, type TEXT NOT NULL, shares INTEGER NOT NULL, price NUMERIC NOT NULL,  total NUMERIC NOT NULL, transacted TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES users (id));")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_symbol ON histories (user_id, symbol);")

    history_data = db.execute(
        "SELECT * FROM histories WHERE user_id = ?", session["user_id"])
    print(history_data)

    return render_template('history.html', histories=history_data)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol", 400)

        # Request the symbol user input
        symbol = request.form.get("symbol")
        result = lookup(symbol)

        # Check if th
        result = lookup(symbol)
        print(result)

        # Ensure the result isn't None
        if result is None:
            return apology("Invalid symbol", 400)
        else:
            # Render quoted template
            return render_template('quoted.html', result=result)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("missing username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("missing password", 400)

        # Ensure repeat password was submitted
        elif not request.form.get("confirmation"):
            return apology("password don't match", 400)

        # Query database for username and the request.form needed
        username = request.form.get("username")
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", username
        )
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure username doesn't exists
        if len(rows) == 1:
            if rows[0]["username"] == username:
                return apology("Username taken", 400)

        # Ensure the password and the repeated are the same
        if str(password).lower() != str(confirmation).lower():
            return apology("Password don't match", 400)

        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)",
                   username, generate_password_hash(password))

        # Remember which user has logged in
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", username
        )
        session["user_id"] = rows[0]['id']

        flash('Registered!')

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    our_stocks = db.execute("SELECT * FROM stocks WHERE user_id = ?", session["user_id"])

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)

        # Ensure shares was submitted
        elif not request.form.get("shares"):
            return apology("must provide shares", 403)

        # Get the symbol and shares after make sure they submitted
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        share_data = lookup(symbol)
        print(share_data)
        our_stock = db.execute(
            "SELECT * FROM stocks WHERE user_id = ? AND symbol = ?", session["user_id"], symbol)

        # Ensure the symbol is valid
        if share_data is None:
            return apology("Invalid symbol", 400)

        # Ensure the shares is valid
        if int(shares) < 1:
            return apology("Invalid shares", 400)

        # Ensure that user can sold their stock first
        if int(shares) > int(our_stock[0]["shares"]):
            return apology("Too much shares", 400)

        # get the stock price and total
        price = float(share_data['price'])
        total = price * float(shares)

        # check for the user data especially the user cash
        user_data = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        user_cash = user_data[0]["cash"]

        # check for the stock table
        check_stock_table = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = 'stocks'")

        # ensure the table exists
        if not check_stock_table:
            db.execute("CREATE TABLE IF NOT EXISTS stocks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, symbol TEXT NOT NULL, shares INTEGER NOT NULL, price NUMERIC NOT NULL, total NUMERIC NOT NULL, FOREIGN KEY (user_id) REFERENCES users (id));")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_symbol ON stocks (user_id, symbol);")

        stock_data = db.execute(
            "SELECT * FROM stocks WHERE user_id = ? AND symbol = ?", session["user_id"], symbol)
        our_shares = stock_data[0]["shares"]
        print(stock_data)

        if our_shares-shares <= 0:
            # delete the shares because the user doesn't have the shares anymore
            db.execute("DELETE FROM stocks WHERE user_id=? AND symbol=?",
                       session["user_id"], symbol)
        else:
            # update new stock data
            old_share = stock_data[0]["shares"]
            old_total = stock_data[0]["total"]
            db.execute("UPDATE stocks SET shares=?, total=? WHERE user_id=? AND symbol=?", int(
                old_share) - int(shares), float(old_total) - float(total), session["user_id"], symbol)

        # check for the histories table
        check_histories_table = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = 'histories'")

        # ensure the table exists
        if not check_histories_table:
            db.execute("CREATE TABLE IF NOT EXISTS histories (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, symbol TEXT NOT NULL, type TEXT NOT NULL, shares INTEGER NOT NULL, price NUMERIC NOT NULL,  total NUMERIC NOT NULL, transacted TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES users (id));")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_symbol ON histories (user_id, symbol);")

        history_data = db.execute(
            "SELECT * FROM histories WHERE user_id = ?", session["user_id"])
        print(history_data)

        transacted = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

        # add histories data
        db.execute("INSERT INTO histories (user_id, symbol, type, shares, price, total, transacted) VALUES(?, ?, ?, ?, ?, ?, ?)",
                   session["user_id"], symbol, 'sold', shares, price, total, transacted)

        # subtract the user money after buying the shares
        db.execute("UPDATE users SET cash=? WHERE id = ?", user_cash + total, session["user_id"])

        flash('Sold!')

        # Redirect user to home page
        return redirect('/')
    else:
        return render_template('sell.html', stocks=our_stocks)
