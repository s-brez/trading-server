# trading-server
Event-driven execution and backtesting platform for trading common markets.

Use this software at your own risk. No responsibility taken for losses incurred.

## Exchange/broker support

Planned order of implementation:

Exchange | Status
-------|---------
BitMEX | Complete
IC Markets | WIP
FTX | NA
Binance | NA
Bitfinex | NA
Bithumb | NA
Kraken | NA
Bitstamp | NA
Coinbase | NA
Poloniex| NA
Huobi | NA
IG Markets | NA
Interactive Brokers | NA
Deribit | NA

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
