# PART 1
# USER:         CONFIGURING THE PV MATRIX
# -> PROGRAM:   CALCULATING PV MATRIX PERFORMANCE AT STC
# -> PROGRAM:   CALCULATING MINIMUM REQUIRED CROSS SECTION OF STRING CABLES
# -> PROGRAM:   CALCULATING THE INVERTER'S WORKING RANGE REQUIREMENTS

import sun
import photovoltaic as pv
from datafiles.horizon_profiles import hp_01, hp_02

# **********************************************************************************************************************
# STEP 1: SPECIFY THE LOCATION

loc = sun.Location(
    name='Ghent',
    region='Belgium',
    latitude=51.07,
    longitude=3.69,
    altitude=9.0
)

# **********************************************************************************************************************
# STEP 2: SET UP SOLAR PANEL MATRIX

# Define the photovoltaic characteristics of the solar panels
# -----------------------------------------------------------

pv_char = pv.PhotoVoltaicCharacteristics(
    pv.STC(Isc=9.97, Voc=39.4, Impp=9.63, Vmpp=31.2),
    pv.TemperatureCoefficients(cIsc=0.05, cVoc=-0.29, cPmpp=-0.4),
    noct=48.0
)

# Define the different types of solar panels
# ------------------------------------------

# In a PV system all solar panels will usually have the same photovoltaic characteristics and dimensions (they will be
# from the same brand and model), but their orientation and irradiation conditions (depending on the horizon profile)
# may differ.

# solar panel oriented to the East and under horizon profile 'hp_01'
solar_panel_east_hp01 = pv.SolarPanel(
    loc=loc,
    orient=pv.Orientation(azimuth=78.0, tilt=20.0),
    dim=pv.Dimensions(width=0.99, height=1.66),
    pv_char=pv_char,
    hz_profile=hp_01
)

# solar panel oriented to the East and under horizon profile 'hp_02'
solar_panel_east_hp02 = pv.SolarPanel(
    loc=loc,
    orient=pv.Orientation(azimuth=78.0, tilt=20.0),
    dim=pv.Dimensions(width=0.99, height=1.66),
    pv_char=pv_char,
    hz_profile=hp_02
)

# solar panel oriented to the West and under horizon profile 'hp_01'
solar_panel_west_hp01 = pv.SolarPanel(
    loc=loc,
    orient=pv.Orientation(azimuth=258.0, tilt=20.0),
    dim=pv.Dimensions(width=0.99, height=1.66),
    pv_char=pv_char,
    hz_profile=hp_01
)

# solar panel oriented to the West and under horizon profile 'hp_02'
solar_panel_west_hp02 = pv.SolarPanel(
    loc=loc,
    orient=pv.Orientation(azimuth=258.0, tilt=20.0),
    dim=pv.Dimensions(width=0.99, height=1.66),
    pv_char=pv_char,
    hz_profile=hp_02
)

# Construct the PV matrix
# -----------------------

row_num = 9  # number of solar panels in one string
col_num = 1  # number of parallel strings

solar_panels = [[solar_panel_east_hp01, solar_panel_east_hp02], [solar_panel_west_hp01, solar_panel_west_hp02]]
matrix_names = ('PVM_EAST', 'PVM_WEST')
matrices = []
for i, matrix_name in enumerate(matrix_names):
    matrix = pv.SolarPanelMatrix(matrix_name, row_num=row_num, col_num=col_num)
    matrices.append(matrix)
    for r in range(row_num):
        for c in range(col_num):
            if 0 <= r < 5:
                matrix.add_solar_panel(solar_panels[i][0], r, c)
            if 5 <= r < 9:
                matrix.add_solar_panel(solar_panels[i][1], r, c)


# Enter the length of the string cables that will run to the inverter
# -------------------------------------------------------------------
for matrix in matrices:
    matrix.string_cables.set_cable_lengths(25)

# **********************************************************************************************************************
# STEP 3: SET UP PV INVERTER

# Create inverter and add solar panel matrix
# ------------------------------------------
inverter = pv.Inverter('INVERTER')
for matrix in matrices:
    inverter.add_pv_matrix(matrix)

# ======================================================================================================================

if __name__ == '__main__':

    # Get the performance characteristics under STC
    # ---------------------------------------------
    for matrix in matrices:
        matrix.set_operating_conditions(Gsurf=1000.0, Tcell=25.0)
        print(f'PV matrix {matrix.id} specifications @ STC')
        print('-------------------------------------------')
        print(f'- peak power = {matrix.get_mpp_power() / 1000.0:.1f} kWp')
        print(f'- MPP current = {matrix.get_mpp_current():.1f} A')
        print(f'- MPP voltage = {matrix.get_mpp_voltage():.1f} V')
        print(f'- short circuit current = {matrix.get_sc_current():.1f} A')
        print(f'- open circuit voltage = {matrix.get_oc_voltage():.1f} V')
        print()
    print()

    # Get the minimum required cross sections of the string cables
    # ------------------------------------------------------------
    for matrix in matrices:
        cs_min = matrix.string_cables.calc_min_cross_sections()
        print(f'- minimum required string cable cross section for {matrix.id} = {cs_min[0]:.1f} mm²')
    print()

    # Get inverter's working range requirements
    # -----------------------------------------
    req = inverter.get_requirements()
    print('PV inverter requirements')
    print('------------------------')
    print(
        f"- minimum allowable value of nominal AC power: {req['Pac_min'][0] / 1000.0:.3f} kW\n"
        f"- maximum allowable value of nominal AC power: {req['Pac_max'][0] / 1000.0:.3f} kW\n"
        f"- minimum allowable value of maximum DC voltage: {req['Vdc_max'][0]:.3f} V\n"
        f"- maximum allowable value of minimum MPP voltage: {req['Vmpp_min'][0]:.3f} V\n"
        f"- minimum allowable value of maximum DC current: {req['Idc_max'][0]:.3f} A\n"
        f"- minimum allowable value of maximum DC power: {req['Pdc_max'][0] / 1000.0:.3f} kW."
    )

# **********************************************************************************************************************
