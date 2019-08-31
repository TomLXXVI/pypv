# Define a solar panel and calculate its photovoltaic output parameters for a given irradiance and cell temperature.

import lib.sun as sun
import lib.photovoltaic as pv

# Location of the solar panel
loc = sun.Location(
    name='Ghent',
    region='Belgium',
    latitude=51.07,
    longitude=3.69,
    altitude=9.0
)

# Solar panel configuration
solar_panel = pv.SolarPanel(
    loc=loc,
    orient=pv.Orientation(azimuth=180.0, tilt=20.0),
    dim=pv.Dimensions(width=0.990, height=1.660),
    pv_char=pv.PhotoVoltaicCharacteristics(
        stc=pv.STC(Isc=9.97, Voc=39.4, Impp=9.63, Vmpp=31.2),
        tco=pv.TemperatureCoefficients(cIsc=0.05, cVoc=-0.29, cPmpp=-0.40),
        noct=48.0,
    ),
    hz_profile=None  # horizon profile
)

# Set the irradiance and cell temperature
solar_panel.set_operating_conditions(Gsurf=1000.0, Tcell=-10.0)

# Print results
print('Photovoltaic output parameters')
print('------------------------------')
print(
    f'solar power = {solar_panel.get_solar_power():.2f} W\n',
    f'MPP power = {solar_panel.get_mpp_power():.2f} W\n',
    f'MPP voltage = {solar_panel.get_mpp_voltage():.2f} V\n',
    f'MPP current = {solar_panel.get_mpp_current():.2f} A\n',
    f'OC voltage = {solar_panel.get_oc_voltage():.2f} V\n',
    f'SC current = {solar_panel.get_sc_current():.2f} A'
)

# Show V,I-characteristic of solar panel at the given conditions
diagram = solar_panel.pv_char.plot_characteristic(which='current')
diagram.show_graph()
