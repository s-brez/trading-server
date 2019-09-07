# trading-server
Event-driven execution and backtesting platform for trading common markets.

Use this software at your own risk. No responsibility taken for losses incurred.

## Exchange/broker support

Planned order of implementation: (this might change as exchanges come and go)

Exchange |  Status   | Asset classes
---------|-----------|------------
BitMEX | Complete | Crypto derivatives
IC Markets | WIP | FX, equity, commodity & index CFD's
FTX | NA | Crypto spot, options & derivatives
Binance | NA | Crypto spot
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
IG Markets | NA | FX, equity, commodity & index CFD's
Interactive Brokers | NA | FX, equity, commodity & index CFD's
Deribit | NA | Crypto derivatives & options

## Market data storage
Server stores 1 minute resolution OHLCV bars for all watched instruments in a mongoDB instance. 

Exchange modules parse tick data where a source is available, but don't store it locally. So tick-based strategies can be utilised.

## Strategy modelling
trading-server doesn't include strategy model implementations. A template (empty) model class is included as a guide. 

Custom model implementations or any other enquiries: sam@sdbgroup.io 

## Acknowledgements
Born from the designs described at QuantStart.com (QSTrader), and the writings of E. Chan and M. Lopez de Prado. Thanks all.

## License
This project is licensed under the MIT License.
