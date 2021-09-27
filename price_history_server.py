#!/usr/bin/env python3
"""
history server for BTC/ETH price.

samples prices every 5 minutes.

keeps track of the last hour.

This doesn't do anythign with timezones, so it's all localtime.
If your server is set to UTC (recommended) this won't matter.
"""
from gevent import spawn, spawn_later, joinall, monkey as _;_.patch_all()
import os, sys, time, requests, bottle
from datetime import datetime as dt

# optimize , this makes bottle process JSON faster.
import orjson
bottle.app().install(bottle.JSONPlugin(orjson.dumps))


# delay between sampling loops
SAMPLING_DELAY = 300 # seconds

# the sliding window of time for the history
SLIDING_WINDOW = 3600 # seconds
#SAMPLING_DELAY, SLIDING_WINDOW = 6, 30

# Making the grand assumption that the window must be a multiple of the sampling delay
assert((SLIDING_WINDOW % SAMPLING_DELAY) == 0)

# Making the grand assumption that the window is a multiple of the sampling delay
MAX_TICKS = int(SLIDING_WINDOW / SAMPLING_DELAY)

# get BTC price
BTC_URL = 'https://api.blockchain.com/v3/exchange/tickers/BTC-USD'

# get ETH price
ETH_URL = 'https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=USD'


# global Storage area for the price history, shared across micro-threads
History = []


def query_price_looper(start_time):
    """
    loops forever every SAMPLING_DELAY seconds
    samples prices from URLs
    computes and saves the result in global History

    Params:
    start_time: the exact time we were scheduled to start
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

    # take the last MAX_TICKS (minus one) out of the History
    trimmed_history = History[-(MAX_TICKS-1):]

    # create new record
    new_record = [timestamp, btc_eth]

    # swap out old History list for new one
   
    # # assignment is atomic in Python so
    # # this is safe for threaded code
    History = trimmed_history + [new_record]

    iso = dt.fromtimestamp(timestamp).isoformat()
    print(f"history @ {iso}: {History}")

    # take into account processing time
    delay = SAMPLING_DELAY - (time.time() - start_time)
    
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

    if start_time == 0:

        # 0 means start right now
        
        start_time = time.time()

        delay = 0
        
    else:

        # means start_time is set to a local epoch time

        if start_time < time.time():

            # start_time's in the past...  we need to
            # time-shift start_time into the future
        
            time_diff = time.time() - start_time

            intervals = (time_diff // SAMPLING_DELAY) + 1

            start_time += intervals * SAMPLING_DELAY

            pass

        # compute how long to wait initially
        delay = start_time - time.time()

        pass

    if delay > 0:
        
        print(f"delaying {delay} seconds")
        
        pass

    # start price sampling microthread
    spawn_later(delay, query_price_looper, start_time)

    # start web server (in this thread)
    bottle.run(host="", port=port, server='gevent', debug=debug)
