import numpy as np

from sun.geometry import Location, SunPath, plot_sun_path_diagram, SunPositionCalculator
from datafiles.horizon_profiles import hp_01
from date_time import Date, ANY_YEAR


loc = Location(
    name='Ghent',
    region='Belgium',
    latitude=51.07,
    longitude=3.69,
    timezone='Europe/Brussels',
    altitude=9.0
)

# sun path for every 21st of the month
spl = [SunPath(loc, Date(2019, m, 21)) for m in range(1, 13)]


# sun path diagram with horizon profile
p = plot_sun_path_diagram(spl, hp_01, size=(14, 8), dpi=96)
p.show_graph()


test_date = Date(ANY_YEAR, 3, 21)
sunrise = SunPositionCalculator.sunrise(loc, test_date)
sunset = SunPositionCalculator.sunset(loc, test_date)
sun_pos_at_sunrise = SunPositionCalculator.calculate_position(loc, test_date, sunrise)
sun_pos_at_sunset = SunPositionCalculator.calculate_position(loc, test_date, sunset)
sun_azi_at_sunrise = sun_pos_at_sunrise.azimuth('deg')
sun_azi_at_sunset = sun_pos_at_sunset.azimuth('deg')
sun_azi_list = np.linspace(sun_azi_at_sunrise, sun_azi_at_sunset)
for sun_azi in sun_azi_list:
    hp_elev = hp_01.elevation(sun_azi)
    sun_azi = str(f'{sun_azi:.1f}°')
    print(f'{sun_azi:<10} : {hp_elev:.1f}°')
