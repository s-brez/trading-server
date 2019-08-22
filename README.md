# trading-server
Event-driven trade execution and backtesting platform for all markets, with a focus on digital asset (cryptocurrency) derivatives.

Use this software at your own risk. No responsibility will be taken for any losses incurred.
Be fully aware of the risks and pitfalls of trading before investing any capital.

## Exchange/broker support
Exchange | Status
-------|---------
BitMEX | Complete
IC Markets | WIP
FTX | WIP
Binance | WIP
Bitfinex | WIP
SimpleFX | WIP

## Market data storage
trading-server parses realtime tick data to 1 minute OHLCV bars, then stores bars in a mongodb instance. 1 minute resolution OHLCV data collections are maintained for all watched instruments. Tick data processing is available if desired, but 1 minute bars are the default storage format. 

## Strategy modelling
trading-server is not intended to include strategy model implementations, it is available only as an execution and testing framework. A template (empty) model class is included as a guide.

To dicuss custom model implementations, or for any other business enquiries, contact @s_brez on telegram. 

## Acknowledgements
Born from the designs described at QuantStart.com, and the writings of E. Chan and M. Lopez de Prado. Thank you to all.

## License
This project is licensed under the MIT License.
