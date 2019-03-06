""" Ticker API endpoint
	Example: 
		https://api-pub.bitimeframeinex.com/v2/tickers?symbols=tBTCUSD
	Args:
		symbol
	Returns:
		JSON: [[SYMBOL, BID, BID_SIZE, ASK, ASK_SIZE, DAILY_CHANGE, 
		DAILY_CHANGE_PERC, LAST_PRICE, VOLUME, HIGH, LOW],]
"""

"""Candle API endpoint
	Example: 
		https://api-pub.bitimeframeinex.com/v2/candles/trade:1m:tBTCUSD
		/hist?limit=100&start=1549086300000&end=1549174500000
	Args: 
		timeframe, symbol, limit, start, end
	Returns:
		JSON: [[MTS, OPEN, CLOSE, HIGH, LOW, VOLUME],] 
"""

import time 
import requests
import pandas as pd
import traceback

url = 'https://api-pub.bitfinex.com/v2/' 

name = "Bitfinex"

native_timeframes = ( # Bitfinex native OHLCV timeframes.
	"1m", 
	"5m", 
	"15m", 
	"30m", 
	"1h", 
	"3h", 
	"6h", 
	"12h", 
	"1D", 
	"7D",
	"1M"
	) 

non_native_timeframes = ( # timeframes to be transformed from source data
	"2h", 
	"4h", 
	"8h", 
	"2D", 
	"3D"
	)

ohlcv_dict = { # for resampling of data, show
	'Open': 'first',
	'Close': 'last',
	'High': 'max', 
	'Low': 'min', 
	'Vol': 'sum'
	}

timeframe_targettime = { # timeframe : seconds per timeframe unit
	"1m": 60,
	"5m": 300,
	"15m": 900,
	"30m": 1800,
	"1h": 3600,
	"2h": 7200,
	"3h": 10800,
	"4h": 14400,
	"6h": 21600,
	"8h": 28800,
	"12h": 43200,
	"1D": 86400,
	"2D": 172800,
	"3D": 259200,
	"1W": 604800,
	"7D": 604800,
	"1M": 2629746
	}

usd_pairs = (
	"BTCUSD",
	"ETHUSD",
	"LTCUSD",
	"EOSUSD",
	"XRPUSD",
	"NEOUSD",
	"USDtUSD",
	"BABUSD",
	"IOTUSD",
	"ETCUSD",
	"DSHUSD",
	"OMGUSD",
	"XMRUSD",
	"ZECUSD",
	"BABUSD",
	"BSVUSD",
	"BTGUSD",
	"ZRXUSD",
	)

btc_pairs = (
	"ETHBTC",
	"EOSBTC",
	"XRPBTC",
	"LTCBTC",
	"BABBTC",
	"NEOBTC",
	"ETCBTC",
	"OMGBTC",
	"XMRBTC",
	"IOTBTC",
	"DSHBTC",
	"ZECUSD",
	"BSVBTC",
	)

eth_pairs = (
	"EOSETH",
	)

class Bitfinex:
	""" Bitfinex exchange model. 
		Poll Bitfinex API to fetch candle, orderbook, wallet and other data.
	"""

	def __init__(self):
		pass

	def get_all_candles(self, symbol, timeframe):		
		""" Returns dataframe of all candle data of a given asset.
			Use this when creating new datastore.
		"""
		
		# first candle timestamp of given asset
		start = self.get_genesis_timestamp(symbol, timeframe) 

		# one timeframe unit prior to current time.
		targettime = self.timeframe_to_targettime(timeframe) 

		# set requested candle block size according to timeframe		
		limit = 0
		if timeframe_targettime.get(timeframe) <= 43200: 
			limit = 5000 # intradaily candle block size
		if timeframe_targettime.get(timeframe) > 43200 and timeframe_targettime.get(timeframe) <= 60480:
			limit = 500 # intraweekly candle block size
		if timeframe_targettime.get(timeframe) > 60480 and timeframe_targettime.get(timeframe) <= 262976:
			limit = 24 # intramonthly candle block size
		
		count = 1 
		frames = [] # temporary storage for API responses 
		time.sleep(3) #

		print("Fetching historical " + timeframe + " data for " + symbol + "_Bitfinex.")
		
		while start < targettime:
			try: # poll API
				response = requests.get(url +"candles/trade:" + 
					timeframe + ':t' + symbol + '/hist?limit=' + 
					str(limit) + '&start=' + str(start) + '&sort=1').json()
				# save request url as string for debug
				API_url = (url +"candles/trade:" + timeframe + ':t' +
					symbol + '/hist?limit=' + str(limit) + '&start=' + 
					str(start) + '&sort=1')					 
				frames.extend(response) 
				start = frames[-1][0] # first item of last list in frames[]
				print(str(count) +": " + (str(start)))
				count += 1
				time.sleep(5)
			except Exception as e:
			    print(e) 
			    traceback.print_exc(limit=None, file=None, chain=True)
			    print(API_url)
			    print(response)
			    print(start)
			    print(frames)
			    exit()
		df = pd.DataFrame(frames)
		df.columns = ["Time", "Open", "Close", "High", "Low", "Volume"]
		df.set_index(['Time'], inplace=True) 
		return df

	def get_new_candles(self, symbol, timeframe, start):
		""" Returns dataframe of candle data from start timestamp to 
			current time. Use to update existing datastore.
		"""

		# one timeframe unit prior to current time.
		targettime = self.timeframe_to_targettime(timeframe)
		
		# set requested candle block size according to timeframe		
		limit = 0
		if timeframe_targettime.get(timeframe) <= 43200: 
			limit = 5000 # intradaily candle block size
		if timeframe_targettime.get(timeframe) > 43200 and timeframe_targettime.get(timeframe) <= 60480:
			limit = 500 # intraweekly candle block size
		if timeframe_targettime.get(timeframe) > 60480 and timeframe_targettime.get(timeframe) <= 262976:
			limit = 24 # intramonthly candle block size
		
		count = 1
		frames = []
		error_count = 0
		print('Start update '+ symbol + '_' + timeframe + ".")
		time.sleep(3)
		while start < targettime:
			try: 
				# TODO: Add capability to resume from rate limit/error
				time.sleep(3)
				response = requests.get(url +"candles/trade:" + timeframe +
				 ':t' +	symbol + '/hist?limit=' + str(limit) + '&start=' +
				  str(start) + '&sort=1').json()
				# url string for debug
				API_url = (url + "candles/trade:" + timeframe +
				 ':t' +	symbol + '/hist?limit=' + str(limit) + '&start=' +
				  str(start) + '&sort=1')
				frames.extend(response)
				start = frames[-1][0] # first element of last list 
				count += 1
			except Exception as e:
			    print(e)
			    print("Last timestamp: " + str(start))
			    error_count += 1
			    if error_count > 3:
			    	break
			    # TODO: Add capability to save "start" and e to file
		try:
			df = pd.DataFrame(frames)
			df.columns = ["Time", "Open", "Close", "High", "Low", "Volume"]
			df.set_index(['Time'], inplace=True) 
			return df
		except ValueError as e:
			# print(e)
			print(symbol + ' data is up to date')


	def get_ticker_values(self, symbol):
		""" Returns dataframe of ticker values of given asset.
			TODO: create variant that takes a list of all ticker codes.
		"""

		response = requests.get(url + "tickers?symbols=t" + symbol).json()
		df = pd.DataFrame(response)
	
		df.columns = [
			"Ticker", "Bid", "Bid_size", "Ask", 
			"Ask_size", "Daily_change", "Daily_change_%", 
			"Last_price", "Vol", "High", "Low"
			]
	
		cols = [ # reorder columns
		"Ticker", "Last_price", "Daily_change",
		"High", "Low", "Daily_change_%", "Bid", 
		"Bid_size", "Ask", "Ask_size", "Vol"
			]
		df = df[cols] 	

		# set ticker code manually to avoid "t" prefix
		df.at[0, "Ticker"] = symbol 

		# change column data type
		df.Daily_change = df.Daily_change.astype(str) 
		
		# append '%' to existing cell value	
		df.at[0, "Daily_change"] = str(df.at[0, "Daily_change"]) + '%' # append % to existing cell value
		
		df.set_index("Ticker", inplace=True) 
		return df

	def get_genesis_candle(self, symbol, timeframe):
		""" Returns dataframe containing first available 
			1 min candle of given asset.
		"""
		
		response = requests.get(url + "candles/trade:1m:t" + symbol +
			'/hist?limit=1&sort=1').json()
		df = pd.DataFrame(response)
		df.columns = ["Time", "Open", "Close", "High", "Low", "Vol"]
		df.set_index("Time", inplace=True) 
		return df

	def get_genesis_timestamp(self, symbol, timeframe):
		""" Returns string timestamp of first available 
			1 min candle of a given asset
		"""

		timestamp = int()
		debug = str()
		
		try:
			response = requests.get(url + "candles/trade:1m:t" + symbol + '/hist?limit=1&sort=1').json()
			timestamp = response[0][0] # first element of first list
			return timestamp
		except Exception as e:
			print(response)
			print(timestamp)
			print(e) 
			traceback.print_exc(limit=None, file=None, chain=True)

	def timeframe_to_targettime(self, timeframe):
		""" Returns unix timestamp one unit before current time based on given timeframe
		"""

		targettime = int()
		try:
			targettime = (time.time() - int(timeframe_targettime.get(timeframe)) ) * 1000
			return targettime
		except Exception as e:
			print(targettime)
			print(e)
			exit()

	def get_native_timeframes(self):
		""" Returns tuple of local-to-exchange timeframes
		"""
		return native_timeframes

	def get_non_native_timeframes(self):
		""" Returns tuple of non-native timeframes
		"""
		return non_native_timeframes

	def get_usd_pairs(self):
		""" Returns tuple of usd margin pairs
		"""
		return usd_margin_pairs

	def get_btc_pairs(self):
		""" Returns tuple of btc margin pairs
		"""
		return btc_margin_pairs
	
	def get_eth_pairs(self):
		""" Returns tuple of eth margin pairs
		"""
		return eth_margin_pairs

	def get_all_pairs(self):
		""" Returns all pairs.
		"""

		all_pairs = usd_pairs + btc_pairs + eth_pairs
		return all_pairs

	def get_name(self):
		""" Return name
		"""

		return name
"""
TODO
get list of all margin pairs
get all ticker values
"""
