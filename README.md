# trading-server
An event-driven execution and backtesting platform for trading common markets.

## Planned Features
Trade crypto, FX, traditional markets with unified risk allocations at any API-accessible venue.

Event-driven backtesting.

Execution simulation (paper trading).

Live execution.

Dynamic, allocation-based risk management.

Discrete feature library.

Strategy sandbox.

Browser frontend.

Account multicasting.

Order-splitting across venues.

Back office: accounting and compliance reports.

Walk forward testing and optimisation.

IPFS/blockhcain signal publishing.

## Venue support

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
1 minute resolution OHLCV bars for all watched instruments are stored with MongoDB. 

Parses tick data where a source is available, but doesn't store ticks locally. So tick-based models can be used.

## Strategy modelling
Strategy model implementations are not included. A template model class is included as a guide. 

Custom model implementations or any other enquiries: sam@sdbgroup.io 

## Acknowledgements
Based on architecture described at QuantStart.com (QSTrader), and the writings of E. Chan and M. Lopez de Prado. Thanks all.

## License
GNU GPLv3
