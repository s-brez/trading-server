# trading-server
Multi-asset, multi-strategy, event-driven trade execution and management server for trading common markets autonomously on 1min and higher timeframes.

[<img src="https://github.com/s-brez/trading-server/blob/master/demo-telegram-ui.jpg">]



## Current features
Trade any API-accessible market with unified multi-strategy portfolio management, autonomously or semi-autonomously.

Allocation-based risk management (allocate x% of capital to specific strategies).

Porfolio performance metrics and tracking.

Feature library - assemble new strategies quickly from existing features.

Trade consent via Telegram (or write your own messaging client). Accept, veto or tweak trade setups before they are actioned.

## WIP features

Account multicasting - trade as many accounts on as many platforms as desired

UI - web dashboard for portfolio stats and individual trade metrics 

Integration with Backtrader

Blockchain-based strategy auditing - publish trade signals to IPFS and Ethereum/BSC to empirically prove win rate over time

Accounting and compliance reporting

## Venue support

Venue |  Integration status   | Instrument types
---------|-----------|------------
[<img src="https://user-images.githubusercontent.com/1294454/27766319-f653c6e6-5ed4-11e7-933d-f0bc3699ae8f.jpg">](https://www.bitmex.com/register/hhGBvP) | Complete | Crypto derivatives
[<img src="https://user-images.githubusercontent.com/1294454/67149189-df896480-f2b0-11e9-8816-41593e17f9ec.jpg">](https://ftx.com/#a=1778494) | In progress | Crypto spot, options & derivatives
[<img src="https://user-images.githubusercontent.com/1294454/29604020-d5483cdc-87ee-11e7-94c7-d1a8d9169293.jpg">](https://www.binance.com/en/register?ref=39168428) | Planned | Crypto spot & derivatives
IG Markets | Planned | FX, equity, commodity & index CFD's
Interactive Brokers | Planned | FX, equity, commodity & index CFD's
Deribit | Planned | Crypto derivatives & options

## Market data
1 minute resolution OHLCV bars for all watched instruments are stored with MongoDB (or write your own DB wrapper). 

Software works with 1 minute and above resolution strategies. Tick-resolution support planned later. With this in mind, the software converts tick data to 1 min bars where live tick data is available, but doesn't store ticks locally (i.e. it handles tick data but doesnt use it yet).
 
## Strategy modellling
Strategy implementations are not included. A simple moving average cross model is included as an example only. 
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
