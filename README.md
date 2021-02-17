# trading-server
Multi-asset, multi-strategy, event-driven trade execution and management platform for trading common markets autonomously on 1min+ timeframes.

![telegram ui](https://github.com/s-brez/trading-server/blob/master/demo-telegram-ui.jpg?raw=true)


## Current features
Trade FX, crypto, CFD's, traditional markets etc (any venue with an API) with unified portfolio management

Allocation-based risk management (allocate x% exposure to specific strategies)

Strategy feature library - assemble new strategies from existing features

Trade consent via Telegram (or write your own messaging client) - Accept, veto or tweak trade setups prior to triggering

## WIP features

Account multicasting - trade as many accounts on as many platforms as desired

UI - web dashboard for portfolio stats and individual trade metrics 

Integration with Backtrader

Blockchain-based strategy auditing - publish trade signals to IPFS and Ethereum/BSC to empirically prove win rate over time

Accounting and compliance reporting

## Venue support

Exchange |  Status   | Asset classes
---------|-----------|------------
BitMEX | Complete | Crypto derivatives
Binance | NA | Crypto spot & derivatives
FTX | NA | Crypto spot, options & derivatives
Deribit | NA | Crypto derivatives & options
IG Markets | NA | FX, equity, commodity & index CFD's
Interactive Brokers | NA | FX, equity, commodity & index CFD's
Bitfinex | NA | Crypto spot
OKEx | NA | Crypto spot
Huobi Global | NA | Crypto spot
Bithumb | NA | Crypto spot
Kraken | NA | Crypto spot
Bitstamp | NA | Crypto spot
Coinbase | NA | Crypto spot
Upbit | NA | Crypto spot
Kucoin | NA | Crypto spot
Bittrex | NA | Crypto spot
Poloniex| NA | Crypto spot
Bitflyer | NA | Crypto spot

## Market data
1 minute resolution OHLCV bars for all watched instruments are stored with MongoDB (or please write your own DB wrapper and submit a pull request). 

Software currently works for 1Min+ resolution strategies with tick-resolution strategy support planned later. With this in mind, the software converts tick data to 1 min bars where live tick data is available, but doesn't store ticks locally (i.e. it can handle tick data but doesnt yet use it).
 
## Strategy modelling
Strategy implementations are not included. A simple moving average cross model is included as a guide only. 
Custom strategy implementations, collaboration or any other enquiries: sam@sdbgroup.io.

## Collaboration
Pull requests and discussion regarding new features are very welcome, please reach out.

## External libraries
TA-LIB - https://mrjbq7.github.io/ta-lib/

Backtrader - https://www.backtrader.com/

## Acknowledgements
Based on architecture described by Michael Halls-Moore at QuantStart.com (qsTrader), and written works by E. Chan and M. Lopez de Prado. Thanks all.

## License
GNU GPLv3
