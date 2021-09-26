#!/usr/bin/env python3
"""
history server for BTC/ETH price.

samples prices every 5 minutes.

keeps track of the last hour.
"""
from gevent import spawn, spawn_later, joinall, monkey as _;_.patch_all()
import os, sys, time, requests, bottle
from datetime import datetime as dt

# optimize 
from orjson import dumps
bottle.app().install(bottle.JSONPlugin(dumps))


# delay between sampling loops
SAMPLING_DELAY = 300 # seconds

# the sliding window of time for the history
SLIDING_WINDOW = 3600 # seconds


# get BTC price
BTC_URL = 'https://api.blockchain.com/v3/exchange/tickers/BTC-USD'

# get ETH price
ETH_URL = 'https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=USD'


# global Storage area for the price history, shared across micro-threads
History = []


def utc_epoch_time():
    """
    utility function to get current epoch in UTC
    """
    return dt.utcnow().timestamp()


def query_price_looper(start_time):
    """
    loops forever every SAMPLING_DELAY seconds
    samples prices from URLs
    computes and saves the result in global History
    """
    global History

    # in python, you can't assign inside lambdas :(
    # so this is a cheat to allow return values
    btc_req, eth_req = [], []

    # perform the web calls all at once via microthreads
    # but wait for them all to get done before continuing
    before_time = time.time()  ## when the network calls start
    joinall([
        spawn(lambda: btc_req.append(requests.get(BTC_URL))),
        spawn(lambda: eth_req.append(requests.get(ETH_URL))),
    ])
    after_time = time.time()   ## when the network calls finish

    # estimated time, average round trip
    timestamp = int( (before_time + after_time) / 2)

    # do the data extraction
    btc_usd = btc_req[0].json()['last_trade_price']
    eth_usd = eth_req[0].json()['USD']

    # data computation
    btc_eth = btc_usd / eth_usd

    # delete all history records stamped outside the time ewindow
    window_start = start_time - SLIDING_WINDOW

    # strip out old timestamps and append new record
    # # assignment is atomic in Python so
    # # this is safe for threaded code
    History = [x for x in History if x[0] > window_start] + [[timestamp, btc_eth]]
    
    print("history:", History)

    # take into account processing time
    delay = SAMPLING_DELAY - (utc_epoch_time() - start_time)
    
    # see ya next time
    spawn_later(delay, query_price_looper, start_time + SAMPLING_DELAY)
    return


@bottle.get('/')
def _():
    # don't cache, it's live data!
    bottle.response.headers['Cache-Control'] = 'no-store; max-age=0'

    # massage the data from a simple list format to a list of dictionaries
    return {"BTCETHPriceHistory":
            [{"time": x[0], "price": x[1]} for x in History]}


if __name__=='__main__':
    
    try:
        port = int(os.getenv('PORT'))
    except:
        port = int(sys.argv[1])    
        pass
    
    try:
        debug = int(os.getenv('DEBUG'))
    except:
        debug = False
        pass
    
    try:
        start_time = int(os.getenv('START_AT'))
    except:
        start_time = 0
        pass

    now = utc_epoch_time()

    if start_time == 0:

        # 0 means start right now
        
        start_time = now

        delay = 0
        
    else:
        
        if start_time < now:
        
            # start_time's in the past...  we need to
            # time-shift start_time into the future
        
            time_diff = now - start_time

            intervals = (time_diff // SAMPLING_DELAY) + 1
        
            start_time += intervals * SAMPLING_DELAY

            pass
        
        # compute how long to wait initially
        delay = start_time - now

        pass

    if delay > 0:
        
        print(f"delaying {delay} seconds")
        
        pass

    # start price sampling microthread
    spawn_later(delay, query_price_looper, start_time)

    # start web server (in this thread)
    bottle.run(host="", port=port, server='gevent', debug=debug)
