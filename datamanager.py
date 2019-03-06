"""
"""

import datetime
import fileinput
import os
import csv
import pandas as pd

# dictionary for resampling 
ohlcv_dict = {
	'Open': 'first',
	'Close': 'last',
	'High': 'max', 
	'Low': 'min', 
	'Vol': 'sum'
	}

# dictionary for timeframe transforms. 'target': 'source'
transform_dict = {
	'2h': '1h',
	'4h': '1h',
	'8h': '1h',
	'2D': '1D',
	'3D': '1D'
}

class Datamanager:
	""" Provides update, interpolation, storage, retrieval
		and transformation capability for locally stored asset data.
	"""

	def __init__(self):
		pass
		
	
	def get_last_stored_timestamp(self, symbol, source, timeframe):  
		""" Return last stored 1m candle timestamp from local datastore.
		"""
		
		if self.check_datastore_exists(symbol, source, timeframe):
			with open('./data/'+ source + '/'+ symbol + 
					'_' + source + '_' +timeframe +'.csv') as f:
				datastore = csv.reader(f) # read file
				datastore = list(datastore) # as list
				text = datastore[-1][0] # first element of last list
				date = datetime.datetime.utcfromtimestamp(
					int(text)/1000.0).strftime('%H:%M:%S %d-%m-%Y')
				print(source + "_" + symbol + "_" + timeframe + 
					" last update: UTC " + str(date))
				return text
		else:
			print("No datastore exists for " + symbol + '_' + source + ".")
	
	def create_new_datastore(self, symbol, source, timeframe, df):
		""" Save given dataframe to new CSV. 
			Param 'df': dataframe of all x timeframe candles of an asset.
		"""

		if self.check_datastore_exists(symbol, source, timeframe):
			print("Datastore already exists for " + symbol + "_" + source)
		else:
			df.to_csv('./data/'+ source + '/'+ symbol + '_' + source + 
				'_' + timeframe +'.csv')
			self.remove_duplicate_entries(symbol, source, timeframe)
			print("Created new datastore for " + symbol + "_" + source + 
				'_' + timeframe +".")
	
	def update_existing_datastore(self, symbol, source, timeframe, df):
		""" Append new dataframe to existing CSV.
			Param 'df': dataframe of new candles from last stored timestamp	
		"""

		if self.check_datastore_exists(symbol, source, timeframe):
			# 'a' for open in append mode
			if isinstance(df, pd.DataFrame):
				with open('./data/'+ source + '/'+ symbol + '_' + source + 
					'_' +timeframe +'.csv', 'a', newline='') as f: 
					print("Storing new data.")
					df.to_csv(f, header=False)
				print(symbol + "_" + source + "_" + 
					timeframe + " update complete."
					)
		else:
			print("Update failed for " + symbol + '_' + source + ".")

	def check_datastore_exists(self, symbol, source, timeframe):
		""" Checks if local datastore exists for given market.
			Return true if exists, false if not.
		"""

		if os.path.isfile('./data/'+ source + '/'+ symbol + '_' + source + 
			'_' + timeframe +'.csv'):
			return True
		else:
			return False

	def print_current_time(self):
		""" Print detailed time
		"""

		time = datetime.datetime.now().strftime('%H:%M:%S %d-%m-%Y')
		timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
		print('Local system time: '+ time + ' ' + str(timezone))
		return time
	
	def remove_duplicate_entries(self, symbol, source, timeframe):
		""" Remove duplicate data and blank rows from CSV datastore. 
		"""

		duplicates = set()		# load csv into a set (faster than pandas)
		for row in fileinput.FileInput('./data/'+ source + '/'+ symbol + '_' + source + '_' +timeframe +'.csv', inplace=1):
			if row in duplicates: continue
			duplicates.add(row)
			print(row, end='')  

	# TODO
	# Complete below functions.


	def resample_data(self, symbol, source, target_tf):
		""" Resample existing candles to target timeframe candles.
			Save dataframe of resampled candles.
		"""

		origin_data = transform_dict.get(target_tf)
		print(origin_data)
		df = pd.read_csv('./data/'+ source + '/'+ symbol + 
			'_' + source + '_' + origin_data +'.csv')
		df["Time"] = pd.to_datetime(df["Time"], unit='ms')
		if source == "Bitfinex": # adjust for irregular OCHLV format
			df.columns = ["Time", "Open", "Close", "High", "Low", "Vol"]
		else: # otherwise use standard OHLCV format
			df.columns = ["Time", "Open", "High", "Low", "Close", "Vol"]
		df.set_index("Time", inplace=True) 
		df = df.round(2)

		try: # upsample origin data to target timeframe
			df = df.resample(target_tf).agg(ohlcv_dict).dropna(how='any')
			# df.to_csv('./data/'+ source + '/'+ symbol + '_' + source + 
				# '_' + target_tf +'.csv')
			# self.remove_duplicate_entries(symbol, source, timeframe)
			# print("Created new datastore for " + symbol + "_" + source + 
				# '_' + target_tf +".")
		except Exception as e:
			print(e)
		return df

	def print_all_datastores(self):
		""" Show list of all local datastores.
		"""
		pass

