# rh-core

See source documentation here: https://tinyurl.com/y3e6cc5t

Implemented features:

v0.1
- Fetch and store price data for various timeframes.
- Fetch ticker data.
- Non-native timeframe resampling.
- REST-based data updating. 
- Visualise price data as candles on a chart.

Features to implement:

v 0.2 
- Identify uptrends and downtrends in price data.
- Identify support and resistance zones and levels.
- Calculate moving averages: SMA, EMA, WMA, TRIX, WEMA, TEMA, 
- Calculate indicators and oscillators: MACD, RSI, IFRSI, MESA, KD, MFI, BB, VPVR, OBV, ADL, ADX, ATR, CCI, FI, KST, PSAR, ROC, VWAP, W%R, 
- Visualise all of the above as artifacts on a candlestick chart.

v 0.3
- Determine relative candle sizes (lookback).
- Identify fibonacci levels.
- Differentiate between smooth and erratic price action.
- Identify price and indicator convergence/divergences
- Visualise all of the above as artifacts on a candlestick chart.

v 0.4
- Execution engine: integrate with authenticated exchange API’s.
	- Monitor exchange account balances.
	- Monitor open positions and orders.
 	- Open, close and modify positions. 
	- Dynamically apply risk management policy
 - Notification & user input system: Integrate with telegram API.
 	- Notification system for identified trade setups.
	- React to user input: confirm/veto a trade, modify parameters of  	- trade, get balances, get positions.
	- Notify when a confirmed trade has met various conditions.

v 0.5
- Identify SFP’s and liquidity areas.
	- Check for parity between different exchanges for SFPs
	- Identify order blocks
	- Identify breakers
	- Identify macro blocks (monthly and weekly)
- Visualise all the above as artifacts on a candle chart.
- Add support for more exchanges. 
- Milestone code review.

v 0.6
- Create standardised file format for serialising trade setups to a logging database.
- Establish database server, move datastores and serialised trade data to database.
- Discretise individual strategy model features, serialise and store. 
- Visualise past and present trade setups from file with the chart viewer.

v 0.7
- Tracking systems:
	- Market performance index and individual asset performance metrics: alpha, beta etc.
	- Backtesting system: track all strategy models performance on historical data: strike rate, market conditions when effective, snapshot of all indicators and other factors/data at time of trade. 
	- Account metrics: net profit, avg strike rate, largest winning trade, largest losing trade, average win per trade, average loss per trade,  max drawdown, trade expectancy.
	- Track per asset: socials general activity and keywords(twitter, steemit, reddit, telegram, linkedin, medium, email newsletter lists, forums), key personnel socials activity, google trend data, github activity, network momentum, long:short ratio, NVT ratio, upcoming key dates and events, and historical impact of all of the above on price at time of event. 
	- Economic events: international interest rates, mainstream asset prices, futures settlements dates, hard forks, other derivatives settlements (other crypto products like DXDY), EOFY dates for various countries, CBOE/CME/NASDAQ futures settlements, traditional market open and close times.

v 0.8
- Move data sourcing from API polling to websocket capture of raw tick data.
- Create limit order book model for the most liquid/relevant exchanges.
- Establish hedged market-making models on co-located AWS instances.
- Establish arbitrage models on co-located AWS instances.
- Implement a probability model to enable application of a probability score to saved and newly identified trades based on historical data analysis.

v 0.9 
- Integrate blockchain signal publishing:
	- Core contract:
		- Token generation.
		- Treasury account mechanics.
		- Publishing “fee” mechanic.
	- Publisher contract: 
		- Publish signals to the Ethereum blockchain.
		- Core strategies remain proprietary with fully transparent blockchain published output.
		- Delay mechanic - timestamp of signal available but content encrypted for a period. Tokens required to decrypt the content at time of publishing. 	
- Milestone code review & smart contract audit.

v 1.0
- Identify optimal AI/ML applications to existing business logic and identify new use cases:
	- Identify if the user or system has better judgement when vetoing setups.
	- Identify previously unutilised correlations in market and global events.
	- Genetic algorithm application to existing strategy parameters.
	- Apply machine learning techniques to limit order book order flow.
	- Apply Sentiment analysis
	- Apply natural language processing to raw tick data for predictive analysis. 
- Define AI/ML integration strategy.
- Optimise existing data pipeline and software modules for AI/ML integration.

v 1.1
- Integrate AI/ML.

v 1.2
- Refine AI/ML integration.
- General code improvements and refinement.

v 1.3
- Integrate AI/ML.

v 1.4
- Refine AI/ML integration.
- General code improvements and refinement.

v 1.5
- Define DAO governance model and product transition strategies:
	- Transition from proprietary internal-service company to DAO:
	- Broad vision for the DAO is loosely “decentralised proprietary trading firm”.
	- Implement Core, Admin & Member permissions for platform participants. Participants stake certain amount of tokens for entry to each tier, with each tier having different rights and tasks, with all members receiving payments for participatory actions in the DAO.
	- The DAO creates internal revenue from trading its own funds both initial and user submitted strategies.
	- All members face significant economic incentive to behave in a way that benefits the DAO.
- Product scope transition:
	- Analysis framework, execution systems and other systems developed as open source.
	- Strategies to be held and owned by individual users, completely segregated from main systems. Trade signal results will be transparent and blockchain published with their parent strategy model details undisclosed.
	- Participants are encouraged to submit original strategies with confidence for integration into core systems. To encourage user submission of strategies: a) users cannot run their own strategies live with the EMS unless they submit it for audit and integration, and must stake tokens to do so, and b) users are incentivised with success payments based on their strategies performance.  
	- Strategy builder: all existing discretized strategy model features can be applied together and backtested. Users can request devs add missing features for a fee in tokens.  
- Specific token mechanics: Payments, membership, staking etc.
	- Membership staking and On-profit fee.
	- Staking rewards: Staking tokens in the DAO accrues annual interest, dependant on size of stake. 

