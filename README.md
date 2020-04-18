# trading-server
Multi-asset, multi-strategy, event-driven trade execution and management platform (OEMS) for trading common markets.

## Planned features
Trade crypto, FX, CFD's, traditional markets etc with unified portfolio management at any API-accessible venue.

Allocation-based risk management (allocate x% market exposure to specific strategies).

Discrete strategy feature library.

Account multicasting - trade as many accounts on as many platforms as desired.

Trade consent message via Telegram - Accept or veta snapshots of trade setup about to trigger.

Blockchain signal auditing - publish trade signals to IPFS and Ethereum to emperically prove a models win rate

Order-splitting same-asset trades across venues for large account sizes.

Event-driven backtesting.

Execution simulation (paper trading/forward testing).

Walk forward optimisation (walk forward analysis).

Back office: accounting and compliance reporting

Browser frontend.

## Venue support

Exchange |  Status   | Asset classes
---------|-----------|------------
BitMEX | Complete | Crypto derivatives
IC Markets | WIP | FX, equity, commodity & index CFD's
FTX | NA | Crypto spot, options & derivatives
Binance | NA | Crypto spot
IG Markets | NA | FX, equity, commodity & index CFD's
Interactive Brokers | NA | FX, equity, commodity & index CFD's
Deribit | NA | Crypto derivatives & options
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
1 minute resolution OHLCV bars for all watched instruments are stored with MongoDB.

Parses tick data where a source is available, but doesn't store ticks locally. So tick-based models can be used.

## Strategy modelling
Strategy model implementations are not included. A simeple moving average cross model class is included as a guide. 

Custom model implementations or any other enquiries: sam@sdbgroup.io.

## Acknowledgements
Based on architecture described at QuantStart.com (QSTrader), and the writings of E. Chan and M. Lopez de Prado. Thanks all.

## License
GNU GPLv3
