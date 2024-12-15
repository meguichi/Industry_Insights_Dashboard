import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Streamlit App Configuration
st.set_page_config(page_title="Industry Insights Dashboard", layout="wide")

# Tickers for industry-specific ETFs and indices
tickers = {
    'Food': '1617.T',
    'Energy Resources': '1618.T',
    'Construction Materials': '1619.T',
    'Chemicals': '1620.T',
    'Pharmaceuticals': '1621.T',
    'Automobiles': '1622.T',
    'Steel & Nonferrous Metals': '1623.T',
    'Machinery': '1624.T',
    'Electronics': '1625.T',
    'IT & Services': '1626.T',
    'Electric Power & Gas': '1627.T',
    'Transportation': '1628.T',
    'Trading Companies': '1629.T',
    'Retail': '1630.T',
    'Banking': '1631.T',
    'Finance (excl. Banking)': '1632.T',
    'Real Estate': '1633.T',
    'Nikkei 225': '^N225',
    'USD/JPY': 'JPY=X',
    'S&P 500': '^GSPC'
}

# Sidebar inputs
st.sidebar.header("Input Parameters")
days = st.sidebar.number_input("Period (days)", min_value=1, max_value=3650, value=30, step=1)  # デフォルト30日
short_window = st.sidebar.number_input("Short Moving Average (days)", min_value=1, max_value=365, value=5, step=1)
long_window = st.sidebar.number_input("Long Moving Average (days)", min_value=1, max_value=365, value=25, step=1)

end_date = datetime.today()
start_date = end_date - timedelta(days=days)

# Data fetch start date (365 days before the start date for moving average calculation)
fetch_start_date = start_date - timedelta(days= 5*365)

# Fetch data (with caching to reduce redundant downloads)
@st.cache_data
def fetch_data(tickers, start_date, end_date):
    df = pd.DataFrame()
    for sector, ticker in tickers.items():
        data = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        if 'Close' in data.columns:
            df[sector] = data['Close']
    return df.dropna(axis=1)

df = fetch_data(tickers, fetch_start_date, end_date)

# Normalize data for plotting based on the start date of the selected period
def normalize_to_start_period(data, start_date):
    # Normalize the data relative to the first date in the selected period
    period_data = data.loc[start_date:]
    normalized = period_data / period_data.iloc[0]
    return normalized

normalized_df = normalize_to_start_period(df, start_date)

# Sidebar: Select industries to display
st.sidebar.subheader("Select Industries to Display")

# All industries checkbox for bulk selection
select_all = st.sidebar.checkbox("Select All", value=False)  # デフォルトで全てオフ
industry_visibility = {}

# Generate individual checkboxes for industries
for sector in normalized_df.columns:
    industry_visibility[sector] = st.sidebar.checkbox(f"{sector}", value=select_all)

# Update the state of checkboxes when "Select All" is toggled
if select_all:
    for sector in normalized_df.columns:
        industry_visibility[sector] = True

# Main content
st.title("Industry Insights Dashboard")

# Section: Normalized Performance
st.subheader(f"Normalized Performance of Industries (Last {days} Days)")
plt.figure(figsize=(14, 8))

# Display selected industries
for sector, visible in industry_visibility.items():
    if visible:
        plt.plot(normalized_df.index, normalized_df[sector], label=sector)

plt.title(f"Normalized Performance of Industries (Last {days} Days)")
plt.xlabel("Date")
plt.ylabel("Normalized Price")
plt.legend(loc="upper left", bbox_to_anchor=(1.05, 1))
plt.grid(True)
st.pyplot(plt.gcf())

# Generate crossovers DataFrame
def create_crossovers_dataframe(data, short_window, long_window):
    results = []
    for column in data.columns:
        short_ma = data[column].rolling(window=short_window).mean()
        long_ma = data[column].rolling(window=long_window).mean()
        signal = pd.Series(0, index=data.index)
        signal[short_ma > long_ma] = 1
        crossover = signal.diff()

        for idx, value in crossover.dropna().items():
            if value == 1:
                results.append({"Stock": column, "Date": idx, "Signal": "Golden Cross"})
            elif value == -1:
                results.append({"Stock": column, "Date": idx, "Signal": "Dead Cross"})

    return pd.DataFrame(results)

crossovers_df = create_crossovers_dataframe(df, short_window, long_window)

# Filter last cross in the specified period
def filter_last_cross_in_period(crossovers_df, start_date, end_date):
    crossovers_df["Date"] = pd.to_datetime(crossovers_df["Date"]).dt.tz_localize(None)
    filtered = crossovers_df[(crossovers_df["Date"] >= start_date) & (crossovers_df["Date"] <= end_date)]
    return filtered.sort_values("Date").groupby("Stock").tail(1).reset_index(drop=True)

last_cross_df = filter_last_cross_in_period(crossovers_df, start_date, end_date)

# Section: Crossovers
st.subheader("Last Crossovers in Selected Period")
st.write(last_cross_df)

if not last_cross_df.empty:
    for _, row in last_cross_df.iterrows():
        stock = row["Stock"]
        signal = row["Signal"]
        date = row["Date"]

        short_ma = df[stock].rolling(window=short_window).mean()
        long_ma = df[stock].rolling(window=long_window).mean()

        # Restrict data for plotting
        analysis_period_data = df.loc[start_date:end_date]

        plt.figure(figsize=(12, 6))
        plt.plot(analysis_period_data.index, analysis_period_data[stock], label=f"{stock} Close", alpha=0.7)
        plt.plot(analysis_period_data.index, short_ma.loc[start_date:end_date], label=f"{short_window}-day MA", linestyle="--")
        plt.plot(analysis_period_data.index, long_ma.loc[start_date:end_date], label=f"{long_window}-day MA", linestyle="--")
        plt.scatter(date, analysis_period_data.loc[date, stock],
                    color="green" if signal == "Golden Cross" else "red",
                    label=signal, marker="o", s=100)
        plt.title(f"{stock} - {signal}")
        plt.xlabel("Date")
        plt.ylabel("Price")
        plt.legend()
        plt.grid(True)
        st.pyplot(plt.gcf())
