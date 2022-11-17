# trading-server
A multi-asset, multi-strategy, event-driven trade execution and management platform for running many algorithms/bots at many venues simultaneously, with unified risk management and reporting.

This is not a standalone trading bot. You need to install and run this on a server or VPS using your own trading algorithms.

## Installation

Using python 3.9

1. Install mongodb (https://www.mongodb.com/)
2. Install TA-Lib python bindings (links to wheels here https://blog.quantinsti.com/install-ta-lib-python/) and binaries (https://mrjbq7.github.io/ta-lib/install.html)
3. Set up a telegram bot, record the bot key in enviroment variable TELEGRAM_BOT_TOKEN. 
4. Create a whitelist for telegram account ID's you want to have control of the server, recorded in environment variable TELEGRAM_BOT_WHITELIST, eg [<USER_ID_1>, <USER_ID_2>]
5. Set up accounts for all venues you will trade at, recording API keys and secret keys in environment variables <VENUE_NAME>_API_KEY and <VENUE_NAME>_API_SECRET
6. Configure what venues, instruments, models and timeframes you want to trade in server.py and model.py.
7. Install dependencies in requirments.txt
8. Run the server with python server_test.py. Note it will take some time to fetch historical data for the instruments you are trading.


## Current features
Trade any API-accessible market with unified multi-strategy portfolio management, autonomously or semi-autonomously.

Allocation-based risk management (allocate x% of capital to specific strategies with y% exposure per strategy).

Porfolio performance metrics and tracking. Tracks the following:

<img src="https://drive.google.com/uc?export=view&id=1Nmai4R5nZbEeaW3Xj5w1005o4AC9ieI4">

Feature library - assemble new strategies quickly from existing features.

Trade consent via Telegram (or write your own messaging client). Accept, veto or tweak trade setups before they are actioned.

<img src="https://drive.google.com/uc?export=view&id=1bhYYNtHvn9V9sOXlzox0XvxF4V1XRI44">

## WIP features

Account multicasting - trade as many accounts on as many platforms as desired.

UI - web dashboard for portfolio stats and individual trade metrics 

Integration with Backtrader

Blockchain-based strategy auditing - publish trade signals to IPFS and Ethereum/BSC to empirically prove win rate over time

Accounting and compliance reporting

## Venue support

Venue |  Integration status   | Instrument types
---------|-----------|------------
[<img src="https://user-images.githubusercontent.com/1294454/27766319-f653c6e6-5ed4-11e7-933d-f0bc3699ae8f.jpg">](https://www.bitmex.com/register/hhGBvP) | Complete | Crypto derivatives
[<img src="https://user-images.githubusercontent.com/1294454/29604020-d5483cdc-87ee-11e7-94c7-d1a8d9169293.jpg">](https://www.binance.com/en/register?ref=39168428) | Planned | Crypto spot & derivatives
IG Markets | Planned | FX, equity, commodity & index CFD's
Interactive Brokers | Planned | FX, equity, commodity & index CFD's
Deribit | Planned | Crypto derivatives & options

## Market data
1 minute resolution OHLCV bars for all watched instruments are stored with MongoDB. 

This software works with 1 minute and above resolution strategies. Tick-resolution support planned later. With this in mind, the software converts tick data to 1 min bars where live tick data is available, but doesn't store ticks locally (i.e. it handles tick data but doesnt use it as is, yet).
 
## Strategy modellling
Individual strategy implementations are not included. A simple moving average cross model is included as an example only. 
Custom strategy implementations, collaboration or any other enquiries please email me at sam@sdbgroup.io.

## Collaboration
Feature requests and discussion regarding new features are very welcome, please reach out.

## External libraries
TA-LIB - https://mrjbq7.github.io/ta-lib/

Backtrader - https://www.backtrader.com/

## Acknowledgements
Based on architecture described by Michael Halls-Moore at QuantStart.com (qsTrader), and written works by E. Chan and M. Lopez de Prado. Thanks all.

## License
GNU GPLv3
