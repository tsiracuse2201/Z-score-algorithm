import yfinance as yf
import pandas as pd
import time
import json
import os
from datetime import datetime, timedelta
import pytz
import requests
from ib_insync import *
import nest_asyncio
import asyncio
nest_asyncio.apply()
# Initialize empty containers for tickers and pairs
# Initialize and connect to Interactive Brokers through IB Gateway or TWS
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)


def get_exchange(stock_symbol):
    """ Fetch the exchange code for the stock symbol using Yahoo Finance API. """
    info = yf.Ticker(stock_symbol).info
    return info.get('exchange', '')

def place_order_and_wait(symbol, is_buy, quantity):
    """Places an order based on the symbol and waits for it to be filled."""
    exchange = 'SMART'  # Use SMART routing for all exchanges
    
    # Check if the last letter of the ticker is 'W' to determine if it's a warrant
    if symbol[-1].upper() == 'W':
        contract = Contract(
            symbol=symbol,
            secType='WAR',
            exchange=exchange,
            currency='USD'
        )
        asset_type = "Warrant"
    else:
        contract = Stock(symbol, exchange, 'USD')
        asset_type = "Stock"
    
    order_type = 'BUY' if is_buy else 'SELL'
    order = MarketOrder(order_type, quantity)
    trade = ib.placeOrder(contract, order)

    # Wait for the order to be filled, checking periodically
    print(f"Placing {order_type} order for {quantity} shares of {symbol} ({asset_type}) on {exchange}.")
    while not trade.isDone():
        ib.sleep(1)  # Check every second

    print(f"Order for {symbol} ({asset_type}) {order_type} {quantity} shares has been filled.")
    return symbol, order_type, quantity




tickers = set()
pairs = []

# File to store the current trades
current_trades_file = 'current_trades2.json'
file_path = r"C:\Users\maske\Documents\IBKR_Flow\special_pairs5m.txt"

# Read pairs from the file
with open(file_path, 'r') as file:
    for line in file.readlines():
        parts = line.strip().split(', Profit: ')
        stocks = parts[0].replace('Pair: ', '').split(' and ')
        tickers.update(stocks)
        pairs.append((stocks[0], stocks[1]))

# Load current trades if available
def load_current_trades():
    try:
        with open(current_trades_file, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}  # Return an empty dictionary if no file exists or if an error occurs

current_trades = load_current_trades()

# Store last 40 data points for each ticker
ticker_data = {}

api_key = 'Q2oFv70FvYhklunfDLrMnO1sQNvdd2Vm'


def fetch_initial_data():
    
    # Define the US/Eastern timezone, which handles daylight saving time (EST/EDT)
    eastern = pytz.timezone('US/Eastern')
    
    for ticker in tickers:
        # Define the time range: from now to the last 200 minutes to ensure we get enough data points
        end_time = datetime.now(eastern)  # Get the current time in US/Eastern (handles EDT/EST)
        start_time = end_time - timedelta(minutes=500)
        
        # Convert times to UTC for API request, formatted as YYYY-MM-DD
        start_date = start_time.astimezone(pytz.utc).strftime("%Y-%m-%d")
        end_date = end_time.astimezone(pytz.utc).strftime("%Y-%m-%d")
        
        url = f'https://api.polygon.io/v2/aggs/ticker/{ticker}/range/5/minute/{start_date}/{end_date}?apiKey={api_key}'
        
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()

            if 'results' in data and len(data['results']) > 0:
                df = pd.DataFrame(data['results'])
                
                # Convert timestamp from UTC to US/Eastern (handles EDT/EST)
                df['timestamp'] = pd.to_datetime(df['t'], unit='ms').dt.tz_localize('UTC').dt.tz_convert(eastern)
                
                df.set_index('timestamp', inplace=True)
                df = df[['c']]  # Use 'c' for close prices
                df.columns = ['Close']

                # We only want the last 40 most recent prices
                #df = df.tail(40)

                # Store the data in the same structure as the original script
                ticker_data[ticker] = {
                    'close_prices': df['Close'],
                    'current_price': df['Close'].iloc[-1]
                }
            else:
                print(f"No data available for {ticker}.")
        else:
            print(f"Failed to fetch data for {ticker}: {response.status_code} - {response.text}")
    
    return ticker_data
def calculate_current_z_score(ticker1, ticker2):
    #if ticker1 in ticker_data and ticker2 in ticker_data and ticker_data[ticker1]['close_prices'] is not None and ticker_data[ticker2]['close_prices'] is not None:
    spread = ticker_data[ticker1]['close_prices'] - ticker_data[ticker2]['close_prices']
    spread= spread.fillna(method='ffill')
    mean_spread = spread.rolling(window=40).mean()
    std_spread = spread.rolling(window=40).std()
    z_score = (spread - mean_spread) / std_spread
    return z_score.iloc[-1]
    #if not z_score.empty else None
    #return None


def save_current_trades():
    with open(current_trades_file, 'w') as file:
        json.dump(current_trades, file)

def place_trades():
    # Calculate z-scores for all pairs and prepare for trading evaluation
    z_scores = []
    for first_stock, second_stock in pairs:
        z_score = calculate_current_z_score(first_stock, second_stock)
        print(first_stock,second_stock,z_score)
        if z_score is not None:  # Ensure z_score is calculable
            ticker1_price = ticker_data[first_stock]['current_price']
            ticker2_price = ticker_data[second_stock]['current_price']
            z_scores.append((first_stock, second_stock, z_score, ticker1_price, ticker2_price))
            pair_key = f"{first_stock}-{second_stock}"
            if pair_key in current_trades:
                # Update current trades with the latest z-score and prices
                current_trades[pair_key]['current_price1'] = ticker1_price
                current_trades[pair_key]['current_price2'] = ticker2_price
                current_trades[pair_key]['z_score'] = z_score

    # Sort by absolute z_score in descending order and select the top 5
    top_z_scores = sorted(z_scores, key=lambda x: abs(x[2]), reverse=True)

    # Collect all stocks that are currently in trades to avoid trading them again
    active_stocks = set()
    for trade in current_trades.values():
        active_stocks.add(trade['first_stock'])
        active_stocks.add(trade['second_stock'])
    trade_ord_cnt = 0
    for first_stock, second_stock, z_score, ticker1_price, ticker2_price in top_z_scores:
        pair_key = f"{first_stock}-{second_stock}"
        if first_stock in active_stocks or second_stock in active_stocks:
            continue  # Skip if any stock in the pair is already involved in another trade

        cash = 500
        if trade_ord_cnt>10:
            break
        if pair_key not in current_trades and abs(z_score)>2:
            direction1 = 'BUY' if z_score < 0 else 'SELL'
            direction2 = 'SELL' if z_score < 0 else 'BUY'
            amt1 = int(cash / ticker1_price)
            amt2 = int(cash / ticker2_price)

            current_trades[pair_key] = {
                'first_stock': first_stock, 'second_stock': second_stock,
                'direction1': direction1, 'direction2': direction2,
                'quantity1': amt1, 'quantity2': amt2, 'z_score': z_score,
                'current_price1': ticker1_price, 'current_price2': ticker2_price
            }

            print(f'Placing new trade: {direction1} {first_stock}, {direction2} {second_stock}')
            if direction1 == "BUY":
                place_order_and_wait(first_stock, True, amt1)
                place_order_and_wait(second_stock, False, amt2)
            else:
                place_order_and_wait(second_stock, True, amt2)
                place_order_and_wait(first_stock, False, amt1)
            active_stocks.add(first_stock)
            active_stocks.add(second_stock)
            trade_ord_cnt+=1
    save_current_trades()

    print("current trades: ",current_trades)


def order_management():
    keys_to_remove = []
    for key, trade_info in current_trades.items():
        ticker1, ticker2 = key.split('-')
   
        z_score = calculate_current_z_score(ticker1, ticker2)
        direction1 = current_trades[key]['direction1']
        direction2 = current_trades[key]['direction2']
        quantity1= current_trades[key]['quantity1']
        quantity2 = current_trades[key]['quantity2']
        #print(direction1, ": is direction of fist stock ", ticker1, " ", direction2, "is direction of second stock, ", ticker2)
        if z_score is not None and -0.5 < z_score < 0.5:
            if direction1 == "BUY":
                buy_stock = ticker2
                sell_stock = ticker1
                buy_result = place_order_and_wait(buy_stock, True, quantity2)
                sell_result = place_order_and_wait(sell_stock, False, quantity1)
            elif direction1 == "SELL":
                buy_stock = ticker1
                sell_stock = ticker2
                buy_result = place_order_and_wait(buy_stock, True, quantity1)
                sell_result = place_order_and_wait(sell_stock, False, quantity2)

            keys_to_remove.append(key)
            print(f'Exiting trade for {ticker1} and {ticker2} due to z_score of {z_score}')
    for key in keys_to_remove:
        del current_trades[key]
        print(f'Removed trade: {key}')
    if keys_to_remove:
        save_current_trades()

def run_periodically():
    while True:
        fetch_initial_data()
        place_trades()
        print(f'Currently active trades: {current_trades}')
        time.sleep(1)  # Sleep for 30 seconds to simulate time between checks
        order_management()
        time.sleep(75)
# Start the periodic trading function
run_periodically()
