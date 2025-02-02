from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io
import squarify

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests for frontend communication

import requests
from bs4 import BeautifulSoup

def convert_us_format(s):
    return float((s.replace("%","")).replace(",", ""))

def get_etf_holdings_from_stock_analysis(ticker):
    """Fetch mutual fund holdings from Morningstar"""
    url = f"https://stockanalysis.com/etf/{ticker}/holdings/"
    print(url)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.morningstar.com/",
        "Connection": "keep-alive"
    }

    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10)
        
        # Debugging: Print Response Code & First 500 characters of the response
        #print(f"Response Status Code: {response.status_code}")
        #print(response.text[:500])  # Print the first 500 characters to check if we got a proper response
        
        if response.status_code != 200:
            print(f"Failed to fetch data for {ticker}. HTTP Status: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        rows = table.find("tbody").find_all("tr")

        # Find holdings data table
        holdings = {}
        #for row in soup.select("table tbody tr"):
        for row in rows:
            columns = row.find_all("td")
            if len(columns) >= 2:
                stock_symbol = columns[1].text.strip()
                percent = columns[3].text.strip()
                holdings[stock_symbol] = convert_us_format(percent)
                #holdings.append((stock_symbol, percent))

        return holdings

    except requests.exceptions.RequestException as e:
        print(f"Error fetching holdings for {ticker}: {e}")
        return None

def get_mutualfunds_holdings_from_stock_analysis(ticker):
    """Fetch mutual fund holdings from Morningstar"""
    url = f"https://stockanalysis.com/quote/mutf/{ticker}/holdings/"
    print(url)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.morningstar.com/",
        "Connection": "keep-alive"
    }

    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10)
        
        # Debugging: Print Response Code & First 500 characters of the response
        #print(f"Response Status Code: {response.status_code}")
        #print(response.text[:500])  # Print the first 500 characters to check if we got a proper response
        
        if response.status_code != 200:
            print(f"Failed to fetch data for {ticker}. HTTP Status: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        rows = table.find("tbody").find_all("tr")

        # Find holdings data table
        holdings = {}
        #for row in soup.select("table tbody tr"):
        for row in rows:
            columns = row.find_all("td")
            if len(columns) >= 2:
                stock_symbol = columns[1].text.strip()
                percent = columns[3].text.strip()
                holdings[stock_symbol] = convert_us_format(percent)
                #holdings.append((stock_symbol, percent))

        return holdings

    except requests.exceptions.RequestException as e:
        print(f"Error fetching holdings for {ticker}: {e}")
        return None

def update_dict(dict1, dict2):
    for key, value in dict2.items():
        if key in dict1:
            dict1[key] += value  # Add values if key exists
        else:
            dict1[key] = value  # Add new key-value pair
    return dict1

def print_top_k(dictionary,kmax):
    sorted_items = sorted(dictionary.items(), key=lambda x: x[1], reverse=True)  # Sort by values (descending)
    top_k = sorted_items[:kmax]  # Get the top 10 items
    for key, value in top_k:
        print(f"{key}: {value}")

def add_prefix(dictionary):
    new_dict = {}
    for i,(key, value) in enumerate(dictionary.items(),1):
        mkey = f'{i:02d}_{key}'
        new_dict[mkey] = value
    return new_dict

def return_top_k(dictionary, kmax):
    sorted_items = sorted(dictionary.items(), key=lambda x: x[1], reverse=True)  # Sort by values (descending)
    top_k = sorted_items[:kmax]  # Get the top 10 items
    new_dict = {}
    for key,value in top_k:
        new_dict[key] = value
    return new_dict

def add_other(dictionary):
    total_percentage = sum(dictionary.values())
    dictionary["Others"] = 100-total_percentage
    return dictionary

def round_k_decimal(dictionary,k):
    for key,value in dictionary.items():
        dictionary[key] = round(value,k)
    return dictionary

@app.route('/calculate_exposure', methods=['POST'])
def calculate_exposure():
    global exposure_without_prefix
    data = request.json
    etfs = data.get('etfs', [])  # List of {'ticker': 'XYZ', 'amount': 10}
    mutualfunds = data.get('mutualFunds', [])  # List of {'ticker': 'XYZ', 'amount': 10}
    individual_stocks = data.get('individualStocks', [])  # List of {'ticker': 'XYZ', 'amount': 10}

    print(f"ETFs: {etfs}")
    print(f"Mutual Funds: {mutualfunds}")
    print(f"Stocks: {individual_stocks}")

    exposure = {}
    funds = etfs + mutualfunds + individual_stocks
    total_portfolio = sum(fund["amount"] for fund in funds)
    print(f"Total Portfolio Value: {total_portfolio}")

    holdings = {}

    print("Processing ETFs:")
    for fund in etfs:
        ticker = fund["ticker"]
        allocation = fund["amount"] / total_portfolio  # Normalize allocation
        #print(f"Fund: {ticker}, Allocation: {allocation}")

        etf_holdings = get_etf_holdings_from_stock_analysis(ticker)
        for stock in etf_holdings:
            etf_holdings[stock] = allocation * etf_holdings[stock]
        
        holdings = update_dict(holdings, etf_holdings)
        print_top_k(holdings,10)

    print("Processing Mutual Funds:")
    for fund in mutualfunds:
        ticker = fund["ticker"]
        allocation = fund["amount"] / total_portfolio  # Normalize allocation
        #print(f"Fund: {ticker}, Allocation: {allocation}")

        mf_holdings = get_mutualfunds_holdings_from_stock_analysis(ticker)
        for stock in mf_holdings:
            mf_holdings[stock] = allocation * mf_holdings[stock] 

        holdings = update_dict(holdings, mf_holdings)
        print_top_k(holdings,10)

    print("Processing Individual Stocks:")
    stocks_dict = {}
    for stock in individual_stocks:
        ticker = stock["ticker"]
        # Need to multipy by 100 because the ETF and MF report percentages
        allocation = 100*stock["amount"] / total_portfolio
        stocks_dict[ticker] = allocation

    holdings = update_dict(holdings, stocks_dict)
    exposure_without_prefix = return_top_k(holdings, 30)
    exposure = add_prefix(exposure_without_prefix)
    exposure = add_other(exposure)
    exposure = round_k_decimal(exposure,3)
    exposure_without_prefix = add_other(exposure_without_prefix)
    print(exposure)

    return jsonify({"exposure": exposure})

@app.route('/get_pie_chart')
def get_pie_chart():
    global exposure_without_prefix
    # Create Pie Chart
    labels = list(exposure.keys())
    sizes = list(exposure.values())

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')  # Equal aspect ratio ensures that pie chart is circular.

    # Save pie chart to a BytesIO object
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png')
    img_io.seek(0)
    plt.close()

    return send_file(img_io, mimetype='image/png')


@app.route('/get_treemap')
def get_treemap():
    global exposure_without_prefix

    labels = list(exposure_without_prefix.keys())
    sizes = list(exposure_without_prefix.values())

    plt.figure(figsize=(6, 6))
    squarify.plot(sizes=sizes, label=labels, alpha=0.7)
    plt.axis('off')
    plt.title("Portfolio Exposure Treemap")

    img_io = io.BytesIO()
    plt.savefig(img_io, format='png', bbox_inches="tight")
    img_io.seek(0)
    plt.close()

    print('Returning tree map')
    return send_file(img_io, mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

