from typing import List

import astral
import numpy as np
import pandas as pd

from quantities.date_time import Time, Date, DateTime, TimeDelta
from quantities.geometry import Angle
from nummath import interpolation, graphing
from sun.horizon import HorizonProfile


class Location:
    def __init__(self, name: str, region: str, latitude: float, longitude: float, altitude: float,
                 timezone: str = 'UTC'):
        self.name = name
        self.region = region
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone  # see Wikipedia: list of tz database time zones
        self.altitude = altitude
        self.astral_location = astral.Location((
            self.name,
            self.region,
            self.latitude,
            self.longitude,
            self.timezone,
            self.altitude
        ))


class SunPosition:
    def __init__(self, azimuth, elevation):
        self.azimuth = Angle(azimuth, 'deg')
        self.elevation = Angle(elevation, 'deg')
        self.zenith = Angle(90.0 - elevation, 'deg')

    def __str__(self):
        return f"(azimuth {self.azimuth('deg'):.1f}°, " \
               f"elevation {self.elevation('deg'):.1f}°, " \
               f"zenith {self.zenith('deg'):.1f}°)"

    @property
    def coordinate(self):
        return self.azimuth, self.elevation, self.zenith


class SunPositionCalculator:
    @staticmethod
    def calculate_position(location: Location, date: Date, time: Time):
        loc = location.astral_location
        py_datetime = DateTime(date=date, time=time).py_datetime
        return SunPosition(
            azimuth=loc.solar_azimuth(py_datetime),
            elevation=loc.solar_elevation(py_datetime)
        )

    @staticmethod
    def sunrise(location: Location, date: Date) -> Time:
        loc = location.astral_location
        sunrise = loc.sunrise(date.py_date)
        return Time(sunrise.hour, sunrise.minute, sunrise.second)

    @staticmethod
    def sunset(location: Location, date: Date) -> Time:
        loc = location.astral_location
        sunset = loc.sunset(date.py_date)
        return Time(sunset.hour, sunset.minute, sunset.second)

    @staticmethod
    def solar_noon(location: Location, date: Date) -> Time:
        loc = location.astral_location
        solar_noon = loc.solar_noon(date.py_date)
        return Time(solar_noon.hour, solar_noon.minute, solar_noon.second)

    @staticmethod
    def daylight_time(location: Location, date: Date) -> TimeDelta:
        loc = location.astral_location
        start_time, end_time = loc.daylight(date.py_date)
        return TimeDelta(DateTime.from_py_datetime(start_time), DateTime.from_py_datetime(end_time))


class SunPath:
    def __init__(self, location: Location, date: Date):
        self.label = date.py_date.strftime('%b %d')  # date format string example: 'Jun 21'
        self.t_ax = [Time(h, 0, 0) for h in range(24)]
        sun_positions = [SunPositionCalculator.calculate_position(location, date, t) for t in self.t_ax]
        self.azi_ax = [sp.azimuth('deg') for sp in sun_positions]
        self.elev_ax = [sp.elevation('deg') for sp in sun_positions]
        self.spi = interpolation.CubicSplineInterPol(x_data=self.azi_ax, y_data=self.elev_ax)
        data = np.array([[elem[0], elem[1], elem[2]] for elem in zip(self.t_ax, self.azi_ax, self.elev_ax)])
        cols = ['time', 'azimuth(°)', 'elevation(°)']
        self.dataframe = pd.DataFrame(data=data, columns=cols)

    def get_elevation(self, azimuth):
        return self.spi.solve(azimuth)

    def get_axes(self):
        return self.azi_ax, self.elev_ax

    def print_table(self):
        with pd.option_context('display.max_rows', None, 'display.max_columns', None):
            print(self.dataframe)


def plot_sun_path_diagram(sun_paths: List[SunPath], horizon_profile: HorizonProfile = None, size=None, dpi=None):
    graph = graphing.Graph(fig_size=size, dpi=dpi)
    for sp in sun_paths:
        graph.add_data_set(
            name=sp.label,
            x=sp.azi_ax,
            y=sp.elev_ax,
            marker='o'
        )
    if horizon_profile:
        graph.add_data_set(
            name='horizon',
            x=horizon_profile.azimuth_ax,
            y=horizon_profile.elevation_ax,
            fill={'color': 'black'}
        )
    graph.add_legend()
    graph.set_axis_titles(x_title='sun azimuth angle', y_title='sun altitude angle')
    graph.scale_x_axis(lim_min=0, lim_max=360, tick_step=20)
    graph.scale_y_axis(lim_min=0, lim_max=90, tick_step=5)
    graph.turn_grid_on()
    graph.draw_graph()
    return graph
