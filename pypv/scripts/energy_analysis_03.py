# PART 3
# USER:
# -> PROGRAM:   ENERGY ANALYSIS

from timer import Timer
from energy_analysis_02 import *

# **********************************************************************************************************************

ea = pv.EnergyAnalyzer(
    TMY_file='../datafiles/tmy.csv',
    CLP_file='../datafiles/mlp.csv',
    location=loc,
    pv_inverters=[inverter]
)

timer = Timer()
timer.start()
ea.analyze()
timer.stop()
timer.join()

if __name__ == '__main__':

    print('ENERGY ANALYSIS')
    print('---------------')
    print(f'- Annual yield = {ea.get_annual_yield():.0f} kWh')
    print(f'- Annual load = {ea.get_annual_load():.0f} kWh')

    print('- monthly overview of energy flows [kWh]')
    ea.print_monthly_overview()

    # plot monthly overview of energy flows
    graph = ea.plot_monthly_overview()
    graph.show_graph()
