__author__ = 'kiruba'
"""
Calculate daily evapotranspiration from weather data.
This file is for calculating the potential ET by Penman method for
aralumallige watershed.
"""
import evaplib
import meteolib as met
import scipy as sp
import pandas as pd
# import gdal, ogr, osr, numpy, sys   # uncomment it if you want to use zonalstats
import math
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np


base_file = '/media/kiruba/New Volume/ACCUWA_Data/weather_station/smgollahalli/smgoll_1_5_11_8_14.csv'
# dateparse = lambda x: pd.datetime.strptime(x, '%d/%m/%y %H:%M:S')
df_base = pd.read_csv(base_file, header=0, sep=',')
format = '%d/%m/%y %H:%M:%S'
df_base['Date_Time'] = pd.to_datetime(df_base['Date'] + ' ' + df_base['Time'], format=format)
df_base.set_index(df_base['Date_Time'], inplace=True)
# df_base = df_base.drop(['Date', 'Time'], axis=1)
# df_base.insert(0, 'Date_Time', df_base['Date_Time'])
# df_base['Date'] = pd.to_datetime(df_base['Date'], format='%d/%m/%y')

# df_base = df_base.sort(['Date'])
df_base.sort_index(inplace=True)
cols = df_base.columns.tolist()
cols = cols[-1:] + cols[:-1]  # bring last column to first
df_base = df_base[cols]

## change column names that has degree symbols to avoid non-ascii error
df_base.columns.values[7] = 'Air Temperature (C)'
df_base.columns.values[8] = 'Min Air Temperature (C)'
df_base.columns.values[9] = 'Max Air Temperature (C)'
df_base.columns.values[16] = 'Canopy Temperature (C)'
# print df_base.head()
# print df_base.columns.values[16]
# rain_df = pd.DataFrame(df_base['Rain Collection (mm)'], columns='Rain (mm)', index=df_base['Date_Time'])
# print rain_df.head()
# df_base[['Rain Collection (mm)', 'Humidity (%)']].plot()

# plt.plot_date(x=df_base['Date_Time'], y=df_base['Wind Speed (kmph)'])
# plt.show()


"""
Aggregate half hourly to daily
"""

## separate out rain daily sum
rain_df = df_base[['Date_Time', 'Rain Collection (mm)']]
## separate out weather data(except rain)

weather_df = df_base.drop(['Date',
                           'Time',
                           'Rain Collection (mm)',
                           'Barometric Pressure (KPa)',
                           'Soil Moisture',
                           'Leaf Wetness',
                           'Canopy Temperature (C)',
                           'Evapotranspiration',
                           'Charging status',
                           'Solar panel voltage',
                           'Network strength',
                           'Battery strength'], axis=1)

# print weather_df.head()
#  Aggregate sum to get daily rainfall
# http://stackoverflow.com/questions/17001389/pandas-resample-documentation
rain_df = rain_df.resample('D', how=np.sum)   # D for day

# Aggregate average to get daily weather parameters
weather_daily_df = weather_df.resample('D', how=np.mean)

# print weather_daily_df.head()
#plot for daily rainfall
fig = plt.figure()
plt.plot_date(rain_df.index, rain_df['Rain Collection (mm)'], 'b-')
fig.autofmt_xdate()
plt.rc('text', usetex=True)
plt.rc('font', family='serif')
# plt.xlabel(r'\textbf{Area} ($m^2$)')
plt.ylabel(r'\textbf{Rain} (mm)')
plt.title(r'Rainfall - Aralumallige Watershed')

plt.show()

# print rain_df.head()
"""
Separate out dry and rainy days
"""
dry_days = rain_df[rain_df['Rain Collection (mm)'] == 0]
rain_days = rain_df[rain_df["Rain Collection (mm)"] > 0]
dry_dates = dry_days.index
rain_dates = rain_days.index
no_dry_days = len(dry_days)
no_rain_days = len(rain_days)
# rain = rain_df[]
# print rain['Rain Collection (mm)']
# print(no_dry_days,no_rain_days)
# print dry_dates
# print rain_dates
# fig = plt.figure(figsize=(11.69, 8.27))
# plt.subplot(1,1,1)
# plt.plot_date(dry_days.index, dry_days[[0]], color='red', linestyle='--')
# plt.plot_date(rain_days.index, rain_days[[0]], color='green', linestyle='--')
# plt.show()
"""
Merge weather data and rain data based on dry/rain day
"""
rain_weather = weather_daily_df.join(rain_days, how='right')  # right = use the index of rain days
# print rain_weather.head()
dry_weather = weather_daily_df.join(dry_days, how='right')
# print dry_weather.head()
# print df_base['2014-05-20']['Rain Collection (mm)']

"""
Evaporation from open water
Equation according to J.D. Valiantzas (2006). Simplified versions
for the Penman evaporation equation using routine weather data.
J. Hydrology 331: 690-702. Following Penman (1948,1956). Albedo set
at 0.06 for open water.
Input (measured at 2 m height):
        - airtemp: (array of) daily average air temperatures [Celsius]
        - rh: (array of) daily average relative humidity [%]
        - airpress: (array of) daily average air pressure data [Pa]
        - Rs: (array of) daily incoming solar radiation [J/m2/day]
        - N: (array of) maximum daily sunshine hours [h]
        - Rext: (array of) daily extraterrestrial radiation [J/m2/day]
        - u: (array of) daily average wind speed at 2 m [m/s]
        - Z: (array of) site elevation [m a.s.l.], default is zero...

    Output:
        - E0: (array of) Penman open water evaporation values [mm/day]

"""


"""
 air pressure (Pa) = 101325(1-2.25577 10^-5 h)^5.25588
h = altitude above sea level (m)
http://www.engineeringtoolbox.com/air-altitude-pressure-d_462.html
mean elevation over watershed = 803.441589 m
Elevation at the check dam = 799 m
"""
z = 799
p = (1-(2.25577*(10**-5)*z))
air_p_pa = 101325*(p**5.25588)
  # give air pressure value
dry_weather['AirPr(Pa)'] = air_p_pa
# print(dry_weather.head())


"""
Sunshine hours calculation
591 calculation - lat = 13.260196, long = 77.5120849
floor division(//): http://www.tutorialspoint.com/python/python_basic_operators.htm
"""
#select radiation data separately
sunshine_df = weather_df[['Date_Time', 'Solar Radiation (W/mm2)']]
# give value 1 if there is radiation and rest 0
sunshine_df['sunshine hours (h)'] = (sunshine_df['Solar Radiation (W/mm2)'] != 0).astype(int)  # gives 1 for true and 0 for false
# print sunshine_df.head()
#aggregate the values to daily and divide it by 2 to get sunshine hourly values
sunshine_daily_df = sunshine_df.resample('D', how=np.sum) // 2  # // floor division
sunshine_daily_df = sunshine_daily_df.drop(sunshine_daily_df.columns.values[0], 1)
# Join with rainy day and dry day weather based on date
# rain_weather = rain_weather.join(sunshine_daily_df, how='left')
dry_weather = dry_weather.join(sunshine_daily_df, how='left')


"""
Daily Extraterrestrial Radiation Calculation(J/m2/day)
"""


def rext_calc(df, lat=float):
    """
    Function to calculate extraterrestrial radiation output in J/m2/day
    Ref:http://www.fao.org/docrep/x0490e/x0490e07.htm

    :param df: dataframe with datetime index
    :param lat: latitude (negative for Southern hemisphere)
    :return: Rext (J/m2)
    """
    # set solar constant [MJ m^-2 min^-1]
    s = 0.0820
    #convert latitude [degrees] to radians
    latrad = lat*math.pi / 180.0
    #have to add in function for calculating single value here
    # extract date, month, year from index
    date = pd.DatetimeIndex(df.index).day
    month = pd.DatetimeIndex(df.index).month
    year = pd.DatetimeIndex(df.index).year
    doy = met.date2doy(dd=date, mm=month, yyyy=year)  # create day of year(1-366) acc to date
    print doy
    l = sp.size(doy)
    if l < 2:
        dt = 0.409 * math.sin(2 * math.pi / 365 * doy - 1.39)
        ws = sp.arccos(-math.tan(latrad) * math.tan(dt))
        j = 2 * math.pi / 365.25 * doy
        dr = 1.0 + 0.03344 * math.cos(j - 0.048869)
        rext = s * 86400 / math.pi * dr * (ws * math.sin(latrad) * math.sin(dt) + math.sin(ws) * math.cos(latrad) * math.cos(dt))
    #Create dummy output arrays sp refers to scipy
    else:
        rext = sp.zeros(l)
        dt = sp.zeros(l)
        ws = sp.zeros(l)
        j = sp.zeros(l)
        dr = sp.zeros(l)
        #calculate Rext
        for i in range(0, l):
            #Calculate solar decimation dt(d in FAO) [rad]
            dt[i] = 0.409 * math.sin(2 * math.pi / 365 * doy[i] - 1.39)
            #calculate sunset hour angle [rad]
            ws[i] = sp.arccos(-math.tan(latrad) * math.tan(dt[i]))
            # calculate day angle j [radians]
            j[i] = 2 * math.pi / 365.25 * doy[i]
            # calculate relative distance to sun
            dr[i] = 1.0 + 0.03344 * math.cos(j[i] - 0.048869)
            #calculate Rext dt = d(FAO) and latrad = j(FAO)
            rext[i] = (s * 86400.0 / math.pi) * dr[i] * (ws[i] * math.sin(latrad) * math.sin(dt[i]) + math.sin(ws[i])* math.cos(latrad) * math.cos(dt[i]))

    rext = sp.array(rext) * 1000000
    return rext

dry_weather['Rext (J/m2)'] = rext_calc(dry_weather, lat=13.260196)
# print dry_weather

# fig = plt.figure()
# plt.plot_date(dry_weather.index, dry_weather['Rext (J/m2)'], 'b*')
# fig.autofmt_xdate()
# plt.show()

"""
wind speed from km/h to m/s
1 kmph = 0.277778 m/s
"""
dry_weather['Wind Speed (mps)'] = dry_weather['Wind Speed (kmph)'] * 0.277778
# print rain_weather

"""
Radiation unit conversion
"""

dry_weather['Solar Radiation (J/m2/day)'] = dry_weather['Solar Radiation (W/mm2)'] * 86400

"""
Dry weather Evaporation calculation
"""
airtemp = dry_weather['Air Temperature (C)']
hum = dry_weather['Humidity (%)']
airpress = dry_weather['AirPr(Pa)']
rs = dry_weather['Solar Radiation (J/m2/day)']
sun_hr = dry_weather['sunshine hours (h)']
rext = dry_weather['Rext (J/m2)']
wind_speed = dry_weather['Wind Speed (mps)']


eo = evaplib.E0(airtemp=airtemp, rh=hum, airpress=airpress, Rs=rs, N=sun_hr, Rext=rext, u=wind_speed, Z=z )
dry_weather['Evaporation (mm/day)'] = eo

fig = plt.figure()
plt.plot_date(dry_weather.index, dry_weather['Evaporation (mm/day)'], 'b*')
fig.autofmt_xdate()
plt.show()

"""
Wet weather Evaporation calculation
"""

## windspeed unit conversion
rain_weather['Wind Speed (mps)'] = rain_weather['Wind Speed (kmph)'] * 0.277778
# air pressure
rain_weather['AirPr(Pa)'] = air_p_pa
# sunshine hours
rain_weather = rain_weather.join(sunshine_daily_df, how='left')
#extraterrestrial radiation
dry_weather['Rext (J/m2)'] = rext_calc(dry_weather, lat=13.260196)