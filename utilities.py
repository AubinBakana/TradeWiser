import csv
import pytz
import requests
import subprocess
import urllib
import uuid

from datetime import date, datetime, timedelta
from flask import redirect, render_template, session
from functools import wraps


def validate_DOB(DOB):
    """
        Validate date of birth: DOB must meet the following criteria:
        - Born anytime today & in the past. No upper boundary on age.

        Returns -1 if user inputs invalid date format.
        Returns 'Valid' if user is born today or earlier.
        Returns 'Invalid' if user is born in future.
    """
    # Define datetime strings format
    date_format = "%Y-%m-%d"
    today = str(date.today())

    today_str = datetime.strptime(today, date_format)
    # Check user input for date formats. Convert strings to datetime objects.
    try:
        dob = datetime.strptime(DOB, date_format)
    except ValueError:
        return -1

    # Validation
    if dob <= today_str:
        return "Valid"
    else:
        return "Invalid"


def apology(msg, code=400):
    """Exceptions Handler: Returns a gif with an image when an exception occurs."""
    def escape(line):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("_", "__"), ("-", "--"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"),
                         ("\"", "''"), ("?", "~q")]:
            line = line.replace(old, new)
        return line
    return render_template("apology.html", top=code, bottom=escape(msg)), code


def login_required(f):
    """
    Decorator: Makes successful login a requirement for access to decorated route.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def Fn(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return Fn


def currency_rate(currency):
    """API Request: Get current currency rate from ExchangeRate-API"""

    url = "https://v6.exchangerate-api.com/v6/30f4583ffe22cdf678ba820f/latest/USD"

    currency = currency.strip().upper()

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        rate = data["conversion_rates"][currency]
        return rate
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


def stock_lookup(symbol):
    """API Request: Get stock quote from provider for the previous 7 days from Yahoo finance"""

    # Request Parameters
    symbol = symbol.upper().strip()
    end = datetime.now(pytz.timezone("US/Eastern"))
    start = end - timedelta(days=7)

    url = (
        f"https://query1.finance.yahoo.com/v7/finance/download/{urllib.parse.quote_plus(symbol)}"
        f"?period1={int(start.timestamp())}"
        f"&period2={int(end.timestamp())}"
        f"&interval=1d&events=history&includeAdjustedClose=true"
    )

    try:
        response = requests.get(url, cookies={"session": str(uuid.uuid4())}, headers={"User-Agent": "python-requests", "Accept": "*/*"})
        response.raise_for_status()

        # CSV header: Date,Open,High,Low,Close,Adj Close,Volume
        quotes = list(csv.DictReader(response.content.decode("utf-8").splitlines()))
        quotes.reverse()
        price = round(float(quotes[0]["Adj Close"]), 2)
        return {
            "name": symbol,
            "price": price,
            "symbol": symbol
        }
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


"""
Format the value into the appropriate currency.

Top 10 currencies as of now include the following:
    1. Kuwaiti dinar (KWD)
    2. Bahraini dinar (BHD)
    3. Omani rial (OMR)
    4. Jordanian dinar (JOD)
    5. British pound (GBP)
    5. Gibraltar pound (GIP)
    7. Cayman Islands dollar (KYD)
    8. Swiss Franc (CHF)
    9. euro (EUR)
    10. US dollar (USD)

"""
def KWD_money(money):
    """Convert a given value to Kuwaiti dinar currency (KWD) format."""
    rate = currency_rate("KWD")
    if rate == None:
        return f"KD{money:,.2f}"

    money = rate * money
    return f"KD{money:,.2f}"


def BHD_money(money):
    """Convert a given value to Bahraini dinar (BHD) currency format."""

    rate = currency_rate("BHD")
    if rate == None:
        return f"{money:,.2f}BD"
    money = rate * money
    return f"{money:,.2f}BD"


def OMR_money(money):
    """Convert a given value to British pound currency (OMR) format."""
    rate = currency_rate("OMR")
    if rate == None:
        return f"{money:,.2f}OMR"
    money = rate * money
    return f"{money:,.2f}OMR"


def JOD_money(money):
    """Convert a given value to Jordanian dinar (JOD) currency format."""
    rate = currency_rate("JOD")
    if rate == None:
        return f"{money:,.2f}JOD"
    money = rate * money
    return f"{money:,.2f}JOD"


def GBP_money(money):
    """Convert a given value to GBP currency (£) format."""
    rate = currency_rate("GBP")
    if rate == None:
        return f"£{money:,.2f}"
    money = rate * money
    return f"£{money:,.2f}"


def GIP_money(money):
    """Convert a given value to Gibraltar pound(GIP£) currency format."""
    rate = currency_rate("GIP")
    if rate == None:
        return f"GIB £{money:,.2f}"
    money = rate * money
    return f"GIB £{money:,.2f}"


def KYD_money(money):
    """Convert a given value to Cayman Islands(CI$) dollar currency format."""
    rate = currency_rate("KYD")
    if rate == None:
        return f"CI${money:,.2f}"
    money = rate * money
    return f"CI${money:,.2f}"


def CHF_money(money):
    """Convert a given value to Swiss Franc (CHF) currency format."""
    rate = currency_rate("CHF")
    if rate == None:
        return f"{money:,.2f} SFr"
    money = rate * money
    return f"{money:,.2f} SFr"


def EUR_money(money):
    """Convert a given value to euro (€) currency format."""
    rate = currency_rate("EUR")
    if rate == None:
        return f"€{money:,.2f}"
    money = rate * money
    return f"€{money:,.2f}"


def USD_money(money):
    """Convert a given value to ($) currency format."""
    return f"${money:,.2f}"
