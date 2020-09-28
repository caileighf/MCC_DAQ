import geopandas
import numpy as np
import pandas as pd
from shapely.geometry import Point

import missingno as msn

import seaborn as sns
import matplotlib.pyplot as plt

country = geopandas.read_file("data/gz_2010_us_040_00_5m.json")
# county = geopandas.read_file("data/gz_2010_us_050_00_5m.json")
ais_data = geopandas.read_file("data/AIS_geoJSON.json")

print(country.head())
print(ais_data.head())

# Plotting to see the AIS data overlay the US map:
fig, ax = plt.subplots(1, figsize=(30,20))
base = country[country['NAME'].isin(['Massachusetts']) == True].plot(ax=ax, color='#3B3C6E')

# plotting the AIS data on top with red color to stand out:
ais_data.plot(ax=base, color='darkred', marker="*", markersize=10);

# # dropping all unused features:
# florence = florence.drop(['AdvisoryNumber', 'Forecaster', 'Received'], axis=1)

# # Statistical information
# print(ais_data.describe())
# # # Notice you can always adjust the color of the visualization
# msn.bar(ais_data, color='darkolivegreen');

plt.show()