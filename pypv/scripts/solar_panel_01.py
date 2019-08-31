# calculate MPP power of solar panel as function of tilt angle for 3 different orientations: azimuth 90° (east),
# azimuth 180° (south) and azimuth 270° (west) and at a given date (Jun 21) and time (solar noon) and location.

import numpy as np

import sun
import photovoltaic as pv
import quantities.date_time as date_time
from nummath import graphing

# Location of solar panel
loc = sun.Location(
    name='Ghent',
    region='Belgium',
    latitude=51.07,
    longitude=3.69,
    altitude=9.0
)


# Photovoltaic characteristics of solar panel from data sheet
pv_char = pv.PhotoVoltaicCharacteristics(
    pv.STC(Isc=9.97, Voc=39.4, Impp=9.63, Vmpp=31.2),
    pv.TemperatureCoefficients(cIsc=0.05, cVoc=-0.29, cPmpp=-0.4),
    noct=48.0
)

# Set date and time for the calculations
date = date_time.Date(date_time.ANY_YEAR, 6, 21)
solar_noon = sun.SunPositionCalculator.solar_noon(loc, date)

# Calculate sun position at given date and time
sun_pos = sun.SunPositionCalculator.calculate_position(loc, date, solar_noon)
print(solar_noon, sun_pos)

# Calculate MPP powers for three different azimuth angles of the solar panel and tilt angles between 0° and 45°
azimuths = [90.0, 180.0, 270.0]
tilts = np.linspace(0.0, 45.0)
Pmpp = [[] for _ in azimuths]
for i, azimuth in enumerate(azimuths):
    for tilt in tilts:
        solar_panel = pv.SolarPanel(
            loc=loc,
            orient=pv.Orientation(azimuth=azimuth, tilt=tilt),
            dim=pv.Dimensions(width=0.99, height=1.66),
            pv_char=pv_char,
            hz_profile=None
        )
        solar_panel.set_operating_conditions(date=date, time=solar_noon, Gglh=1000.0, Tambient=25.0)
        Pmpp[i].append(solar_panel.get_mpp_power())

# Show the results in diagram
graph = graphing.Graph()
for i in range(len(Pmpp)):
    graph.add_data_set(name=f'azimuth panel {azimuths[i]:.1f}°', x=tilts, y=np.array(Pmpp[i]))
graph.add_legend()
graph.set_graph_title(f'Sun position at {solar_noon}: {sun_pos}')
graph.turn_grid_on()
graph.set_axis_titles(x_title='tilt angle [°]', y_title='Pmpp [W]')
graph.draw_graph()
graph.show_graph()
