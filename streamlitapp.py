import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import requests
from bs4 import BeautifulSoup
import io
import squarify

st.set_page_config(page_title="Portfolio X-ray", layout="wide")

def convert_us_format(s):
    return float((s.replace("%", "")).replace(",", ""))

def get_etf_holdings_from_stock_analysis(ticker):
    url = f"https://stockanalysis.com/etf/{ticker}/holdings/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        rows = table.find("tbody").find_all("tr")

        holdings = {}
        for row in rows:
            columns = row.find_all("td")
            if len(columns) >= 2:
                stock_symbol = columns[1].text.strip()
                percent = columns[3].text.strip()
                holdings[stock_symbol] = convert_us_format(percent)
        return holdings
    except:
        return None

def get_mutualfunds_holdings_from_stock_analysis(ticker):
    url = f"https://stockanalysis.com/quote/mutf/{ticker}/holdings/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        rows = table.find("tbody").find_all("tr")

        holdings = {}
        for row in rows:
            columns = row.find_all("td")
            if len(columns) >= 2:
                stock_symbol = columns[1].text.strip()
                percent = columns[3].text.strip()
                holdings[stock_symbol] = convert_us_format(percent)
        return holdings
    except:
        return None

def update_dict(dict1, dict2):
    """ 
    Maintain a cumulative percentage for each stock
    Sometimes the %weight is zero for some stocks.
    In this case, make it at least 0.01 so that the treemap function does not complain
    """
    for key, value in dict2.items():
        dict1[key] = max(dict1.get(key, 0) + value, 0.01)
    return dict1

def return_top_k(dictionary, kmax=30):
    sorted_items = sorted(dictionary.items(), key=lambda x: x[1], reverse=True)
    kmax = min(len(sorted_items),kmax)
    top_k = sorted_items[:kmax]
    return {key: value for key, value in top_k}

def add_other(dictionary):
    total_percentage = sum(dictionary.values())
    dictionary["Others"] = max(0.01, 100 - total_percentage)
    return dictionary

def calculate_exposure(etfs, mutualfunds, stocks):
    exposure = {}
    total_portfolio = sum(fund["amount"] for fund in etfs + mutualfunds + stocks)

    for fund in etfs:
        ticker = fund["ticker"]
        allocation = fund["amount"] / total_portfolio
        etf_holdings = get_etf_holdings_from_stock_analysis(ticker) or {}
        exposure = update_dict(exposure, {k: v * allocation for k, v in etf_holdings.items()})

    for fund in mutualfunds:
        ticker = fund["ticker"]
        allocation = fund["amount"] / total_portfolio
        mf_holdings = get_mutualfunds_holdings_from_stock_analysis(ticker) or {}
        exposure = update_dict(exposure, {k: v * allocation for k, v in mf_holdings.items()})

    for stock in stocks:
        ticker = stock["ticker"]
        allocation = 100 * stock["amount"] / total_portfolio
        exposure[ticker] = exposure.get(ticker, 0) + allocation

    exposure = return_top_k(exposure, 40)
    exposure = add_other(exposure)

    return exposure

def plot_treemap(exposure):
    labels = list(exposure.keys())
    sizes = list(exposure.values())

    plt.figure(figsize=(6, 6))
    squarify.plot(sizes=sizes, label=labels, alpha=0.7)
    plt.axis("off")
    plt.title("Portfolio Exposure Treemap")

    img_io = io.BytesIO()
    plt.savefig(img_io, format="png", bbox_inches="tight")
    img_io.seek(0)
    return img_io

def main():
    st.title("Portfolio X-ray")

    col1, col2, col3 = st.columns(3)

    # ETFs Input
    with col1:
        st.subheader("ETFs")
        etfs = []
        num_etfs = st.number_input("Number of ETFs", min_value=0, max_value=10, step=1, key="etf_count")
        for i in range(num_etfs):
            cols = st.columns([1, 2])  # Ticker (1/3 width), Amount (2/3 width, slightly larger)
            ticker = cols[0].text_input(f"Ticker {i+1}", key=f"etf_ticker_{i}")
            amount = cols[1].number_input(f"Amount {i+1}", min_value=0.0, key=f"etf_amount_{i}")
            if ticker and amount:
                etfs.append({"ticker": ticker, "amount": amount})

    # Mutual Funds Input
    with col2:
        st.subheader("Mutual Funds")
        mutualfunds = []
        num_mutualfunds = st.number_input("Number of Mutual Funds", min_value=0, max_value=10, step=1, key="mf_count")
        for i in range(num_mutualfunds):
            cols = st.columns([1, 2])
            ticker = cols[0].text_input(f"Ticker {i+1}", key=f"mf_ticker_{i}")
            amount = cols[1].number_input(f"Amount {i+1}", min_value=0.0, key=f"mf_amount_{i}")
            if ticker and amount:
                mutualfunds.append({"ticker": ticker, "amount": amount})

    # Stocks Input
    with col3:
        st.subheader("Stocks")
        stocks = []
        num_stocks = st.number_input("Number of Stocks", min_value=0, max_value=10, step=1, key="stock_count")
        for i in range(num_stocks):
            cols = st.columns([1, 2])
            ticker = cols[0].text_input(f"Ticker {i+1}", key=f"stock_ticker_{i}")
            amount = cols[1].number_input(f"Amount {i+1}", min_value=0.0, key=f"stock_amount_{i}")
            if ticker and amount:
                stocks.append({"ticker": ticker, "amount": amount})

    if st.button("Take X-ray"):
        if not (etfs or mutualfunds or stocks):
            st.warning("Please add at least one asset.")
        else:
            exposure = calculate_exposure(etfs, mutualfunds, stocks)

            col_data, col_chart = st.columns([1, 1.5])
            with col_data:
                st.subheader("X-ray Data")
                exposure_df = pd.DataFrame(exposure.items(), columns=["Stock", "Portfolio Exposure (%)"])
                st.dataframe(exposure_df)

            with col_chart:
                st.subheader("X-ray Tree map")
                treemap_img = plot_treemap(exposure)
                st.image(treemap_img)

if __name__ == "__main__":
    main()