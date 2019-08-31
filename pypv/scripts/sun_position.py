from sun.geometry import Location, SunPositionCalculator
from date_time import Date, Time, ANY_YEAR

loc = Location(
    name='Ghent',
    region='Belgium',
    latitude=51.07,
    longitude=3.69,
    timezone='Europe/Brussels',
    altitude=9.0
)

date = Date(year=ANY_YEAR, month=7, day=29)
time = Time(hour=12, minute=0, second=0)
sp = SunPositionCalculator.calculate_position(location=loc, date=date, time=time)
sunrise = SunPositionCalculator.sunrise(location=loc, date=date)
solar_noon = SunPositionCalculator.solar_noon(location=loc, date=date)
sunset = SunPositionCalculator.sunset(location=loc, date=date)
print(f"sun position on {date} at {time} = {sp}")
print(f"sunrise is at {sunrise}")
print(f"solar noon is at {solar_noon}")
print(f"sunset is at {sunset}")
