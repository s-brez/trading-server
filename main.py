"""
"""

from bitfinex import Bitfinex
from datamanager import Datamanager
import pandas as pd

""" Timeframes required for analysis, 
	not all timeframes listed are native-to-source
	and will require transformation
"""
required_timeframes = (
	"1m", "5m", "15m", "30m", "1h", 
	"2h", "3h", "4h" "6h","8h", "12h", 
	"1D", "2D", "3D", "7D", "1M" 
	)

# initialise objects
DM = Datamanager()
BFX = Bitfinex()
sources = []
sources.append(Bitfinex())
df = pd.DataFrame()

# sources = [
# 	"Bitfinex",	"BitMEX", "Binance", "Kucoin", 
# 	"Cryptopia", "Bittrex",	"Deribit", "OKex", "Poloniex"
# 	]

def build_all_native_timeframe_datastores():
	""" Build all datastores. Fetches all historical data. 
		Required to run only once.
		Caution - takes hours to run.
	"""

	for source in sources: # iterate through all exchanges
		timeframes = source.get_native_timeframes()
		for tf in timeframes: # ... all local timeframes
			pairs = source.get_all_pairs()
			for pair in pairs: # ... all pairs
				DM.create_new_datastore(
					pair, 
					source.get_name(), 
					tf, 
					source.get_all_candles(pair,tf)
					)
		 
def build_all_non_native_timeframe_datastores():
	""" Creates missing timeframe data from stored data where 
		timeframes not available natively.
	"""

	for source in sources: 
		timeframes = source.get_non_native_timeframes()
		for target_tf in timeframes: 
			pairs = source.get_all_pairs()
			for pair in pairs:
				# create new datastore
				DM.create_new_datastore(
					pair,
					source.get_name(),
					target_tf, 
					DM.resample_data(
						pair, 
						source.get_name(), 
						target_tf
						)
					)

def update_all_datastores():
	""" Intended to be run manually intermittently
		during development.	To be superceded by smarter 
		updating (live tick data > candles)
	"""

	# update native timeframes
	for source in sources: # iterate through all exchanges
		native_timeframes = source.get_native_timeframes()
		for tf in native_timeframes: # & all local timeframes
			pairs = source.get_all_pairs()
			for pair in pairs: # & all pairs
				DM.update_existing_datastore(
					pair, 
					source.get_name(), 
					tf, 
					source.get_new_candles(
						pair, 
						tf, 
						int(DM.get_last_stored_timestamp(
								pair, 
								source.get_name(),
								tf
								)
							)
						)
					)
				DM.remove_duplicate_entries(
					pair, 
					source.get_name(),
					tf
					)
				
	# update non-native timeframes
	for source in sources: 
		non_native_timeframes = source.get_non_native_timeframes()
		print(non_native_timeframes)
		for tf in non_native_timeframes: 
			pairs = source.get_all_pairs()
			print(pairs)
			for pair in pairs:
				# resample from the native data just updated
				print("origin data for " + tf)
				df = DM.resample_data(
					pair, 
					source.get_name(), 
					tf
					)
				# overwrite existing non_native CSV's
				df.to_csv('./data/'+ source.get_name() + '/'+ pair + 
					'_' + source.get_name() + '_' + tf +'.csv')

				DM.remove_duplicate_entries(
					pair, 
					source.get_name(),
					tf
					)

build_all_native_timeframe_datastores() # run once

build_all_non_native_timeframe_datastores() # run once

update_all_datastores() # run as needed
