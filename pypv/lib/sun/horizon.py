import math
from typing import List

from quantities.geometry import Angle
from nummath import interpolation


class HorizonPoint:
    def __init__(self, label: str, azimuth: float, elevation: float, planar_distance: float):
        self.label = label
        self.azimuth = Angle(azimuth, 'deg')
        self.elevation = Angle(elevation, 'deg')
        self.planar_distance = planar_distance

    def move_viewpoint(self, vp_south_coord, vp_east_coord, vp_height):
        # rectangular coordinates of obstacle point as seen from original viewpoint
        s, e, h = self._rectangular_coordinates(self.azimuth, self.elevation, self.planar_distance)
        # new rectangular coordinates of obstacle point as seen from moved viewpoint
        s -= vp_south_coord
        e -= vp_east_coord
        h -= vp_height
        # polar coordinates of obstacle point as seen from moved view point
        self.azimuth, self.elevation, self.planar_distance = self._polar_coordinates(s, e, h)

    @staticmethod
    def _rectangular_coordinates(azimuth: Angle, elevation: Angle, planar_distance: float):
        azi = math.pi - azimuth('rad')
        elev = elevation('rad')
        south_coord = planar_distance * math.cos(azi)
        east_coord = planar_distance * math.sin(azi)
        height = planar_distance * math.tan(elev)
        return south_coord, east_coord, height

    @staticmethod
    def _polar_coordinates(south_coord, east_coord, height):
        pd = math.sqrt(south_coord ** 2 + east_coord ** 2)
        elev = math.atan(height / pd)
        cos_azi = abs(south_coord) / pd
        if south_coord >= 0.0 and east_coord >= 0.0:  # quadrant SE
            azi_offset = math.pi
            sign = -1
        elif south_coord >= 0.0 and east_coord < 0.0:  # quadrant SW
            azi_offset = math.pi
            sign = 1
        elif south_coord < 0.0 and east_coord >= 0.0:  # quadrant NE
            azi_offset = 0.0
            sign = 1
        else:  # quadrant NW
            azi_offset = 2 * math.pi
            sign = -1
        azi = azi_offset + sign * math.acos(cos_azi)
        return Angle(azi, 'rad'), Angle(elev, 'rad'), pd


class _Segment:
    def __init__(self, start_point, end_point):
        self.start_point = start_point
        self.end_point = end_point
        self.line = None


class HorizonProfile:
    def __init__(self, id_: str, points: List[HorizonPoint]):
        self.id = id_
        self._points = points
        self._points.sort(key=lambda pnt: pnt.azimuth('deg'))
        self._create_segments()

    def _create_segments(self):
        self._segments = []
        for i in range(len(self._points[:-1])):
            s = _Segment(start_point=self._points[i], end_point=self._points[i + 1])
            s.line = interpolation.PolyInterPol(
                x_data=[self._points[i].azimuth('deg'), self._points[i+1].azimuth('deg')],
                y_data=[self._points[i].elevation('deg'), self._points[i+1].elevation('deg')]
            )
            self._segments.append(s)

    def elevation(self, azimuth: float):
        for s in self._segments:
            if s.start_point.azimuth('deg') <= azimuth <= s.end_point.azimuth('deg'):
                return s.line.solve(azimuth)
        else:
            return 0.0

    @property
    def azimuth_ax(self):
        return [pnt.azimuth('deg') for pnt in self._points]

    @property
    def elevation_ax(self):
        return [pnt.elevation('deg') for pnt in self._points]
