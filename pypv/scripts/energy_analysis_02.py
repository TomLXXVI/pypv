# PART 2
# USER:         SIZING STRING CABLES
# USER:         ENTER WORKING RANGE PARAMETERS OF SELECTED INVERTER
# -> PROGRAM:   CHECK INVERTER'S WORKING RANGE

from energy_analysis_01 import *

# **********************************************************************************************************************
# STEP 1: SIZING STRING CABLES

for matrix in matrices:
    matrix.string_cables.set_cross_sections(4.0)

# **********************************************************************************************************************
# STEP 2: ENTER WORKING RANGE PARAMETERS AND PART LOAD EFFICIENCIES OF SELECTED INVERTER

inverter.setup(
    Pac_nom=5000.0,
    Vdc_nom=365.0,
    Vdc_max=600.0,
    Vmpp_min=175.0,
    Vmpp_max=500.0,
    Idc_max=15.0,
    Pdc_max=7500.0,
    eff_max=97.0,
)

inverter.set_part_load_efficiencies(
    eff_at_Vmpp_min={5: 91.2, 10: 93.8, 20: 95.3, 25: 95.5, 30: 95.6, 50: 95.6, 75: 95.2, 100: 94.6},
    eff_at_Vdc_nom={5: 92.5, 10: 95.2, 20: 96.6, 25: 96.8, 30: 97.0, 50: 97.0, 75: 96.7, 100: 96.2},
    eff_at_Vmpp_max={5: 90.7, 10: 94.4, 20: 96.2, 25: 96.5, 30: 96.6, 50: 96.8, 75: 96.5, 100: 96.1}
)

# ======================================================================================================================

if __name__ == '__main__':

    # Check inverter's working range
    # ------------------------------

    results = inverter.check()
    msg = ''
    if results:
        for result in results:
            msg += result + '\n'
    else:
        msg = 'All inverter requirements OK!'
    print(msg)

# **********************************************************************************************************************
