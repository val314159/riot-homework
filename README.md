# riot-homework
pricing feed + api call

## Quickstart

### Install

  - make sure you have `/usr/local/bin/` in your path

  - execute:

```
sudo make install
```

  - *Optional:* Use nginx.conf as a guide for a front end proxy server

### Run

#### To run on port 6666

```
price_history_server.py 6666
```

## More Options

#### Other ways to run it

  - get the port from the environment

```
PORT=6666 price_history_server.py
```

  - run in debug mode (better error messages)

```
DEBUG=1 price_history_server.py 6666
```

  - START_AT is meant to syncronize ticks to an expected time, so
    instead of starting whenever the process starts, we can delay
    a little bit and force the sampling ticks to be synchronized
    to, say, the hour mark.

  - if START_AT is in the past (the expected case), time-shift to the future.

  - if START_AT is in the future, start sampling delay to that time

  - if not specified, we just start at the current time and no delay.

  - start at 2021-09-26T00:00:00 (midnight)

```
START_AT=1632632400 price_history_server.py 6666
```

Mix n Match

```
START_AT=1632632400 DEBUG=1 PORT=6666 price_history_server.py
```

