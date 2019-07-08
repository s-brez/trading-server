import io
import pandas as pd
from math import pi
from bokeh.plotting import figure, show, output_file
import bokeh

class Chart:

	def __init__(self):
		pass

	source = "Bitfinex"
	symbol = "ETHUSD"
	timeframe = "1D"

	# get most recent 50 rows
	df = pd.read_csv('./data/'+ source + '/'+ symbol + '_' + source + 
		'_' + timeframe +'.csv')[-50:]
	# df.set_index(['Time'], inplace=True) 

	df["Time"] = pd.to_datetime(df["Time"], unit='ms')
	df = df.round(2)
	print(df)


	inc = df.Close > df.Open
	dec = df.Open > df.Close

	# need to match candle tf
	w = 24*60*60*1000

	TOOLS = "pan,wheel_zoom,box_zoom,reset,save"

	p = figure(x_axis_type="datetime", tools=TOOLS, plot_width=800, title
		= "Candlestick")

	p.xaxis.major_label_orientation = pi/4
	p.grid.grid_line_alpha=0.0


	""" NOTE
		finex uses OCHLV, as opposed to OHLCV
		bokeh expects OHLCV
	""" 

	# wick
	p.segment(df.Time, df.High, df.Time, df.Low, color="black")
	# buy candle
	p.vbar(df.Time[inc], w, df.Open[inc], df.Close[inc], 
		fill_color="black", line_color="black")
	# sell candle
	p.vbar(df.Time[dec], w, df.Open[dec], df.Close[dec], 
		fill_color="white", line_color="black")

	show(p)

	output_file("candlestick.html", title="candlestick example")