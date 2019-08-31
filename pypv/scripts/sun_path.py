from sun.geometry import Location, SunPath
from date_time import Date

loc = Location(
    name='Ghent',
    region='Belgium',
    latitude=51.07,
    longitude=3.69,
    timezone='Europe/Brussels',
    altitude=9.0
)
date = Date(year=2019, month=7, day=29)
sp = SunPath(loc, date)
sp.print_table()
