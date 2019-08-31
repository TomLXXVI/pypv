import math

from sun.geometry import SunPosition
from sun.horizon import HorizonProfile
from quantities.geometry import Angle


class Surface:
    def __init__(self, azimuth: float, tilt: float, width: float, height: float, hz_profile: HorizonProfile = None):
        self.azimuth = Angle(azimuth, 'deg')
        self.tilt = Angle(tilt, 'deg')
        self.width = width
        self.height = height
        self.area = width * height
        self.hz_profile = hz_profile


class SunEnergyCalculator:
    def __init__(self, sun_position: SunPosition, surface: Surface, day_number: int):
        self.day_number = day_number
        self.surface = surface
        self.sun_pos = sun_position
        self.incidence_angle = self._incidence_angle()

    def _incidence_angle(self):
        azi_sun = self.sun_pos.azimuth('rad')
        zenith_sun = math.pi / 2.0 - self.sun_pos.elevation('rad')
        azi_surf = self.surface.azimuth('rad')
        tilt_surf = self.surface.tilt('rad')
        a = math.sin(zenith_sun) * math.sin(tilt_surf) * math.cos(azi_sun - azi_surf)
        b = math.cos(zenith_sun) * math.cos(tilt_surf)
        cos_i = a + b
        if 0.0 <= cos_i <= 1.0:
            incidence_angle = Angle(math.acos(cos_i), 'rad')
        else:
            incidence_angle = Angle(90.0, 'deg')
        return incidence_angle

    def _eccentricity_factor(self):
        return 1 + 0.033 * math.cos(2 * math.pi * self.day_number / 365.25)

    def _extraterrestrial_irradiance(self, incidence_angle: float):
        ef = self._eccentricity_factor()
        irr0 = ef * 1367.0
        return irr0 * math.cos(incidence_angle)

    def _air_mass_ratio(self):
        zenith_sun = math.pi / 2.0 - self.sun_pos.elevation('rad')
        return 1 / math.cos(zenith_sun)

    def _irradiance_diffuse(self, irr_gl_hor: float):
        irr_et = self._extraterrestrial_irradiance(0.0)
        am = self._air_mass_ratio()
        kT = irr_gl_hor / irr_et * am
        if 0.0 <= kT <= 0.22:
            r = 1.0 - 0.09 * kT
        elif 0.22 < kT <= 0.8:
            r = 0.9511 - 0.1604 * kT + 4.388 * kT ** 2 - 16.638 * kT ** 3 + 12.336 * kT ** 4
        else:
            r = 0.165
        return r * irr_gl_hor

    def _irradiance_beam(self, irr_gl_hor, irr_dif):
        zenith_sun = math.pi / 2.0 - self.sun_pos.elevation('rad')
        return (irr_gl_hor - irr_dif) / math.cos(zenith_sun)

    def _anisotropic_sky_radiation_correction(self):
        ia = self.incidence_angle('rad')
        tilt_surf = self.surface.tilt('rad')
        Y = max(0.45, 0.55 + 0.437 * math.cos(ia) + 0.313 * math.cos(ia) ** 2)
        if tilt_surf <= math.pi / 2.0:
            return Y * math.sin(tilt_surf) + math.cos(tilt_surf)
        else:
            return Y * math.sin(tilt_surf)

    def _irradiance_surf(self, irr_beam, irr_dif, irr_gl_hor, rho_grnd, model):
        tilt_surf = self.surface.tilt('rad')
        ia = self.incidence_angle('rad')
        if model == 'anisotropic':
            f_sky = self._anisotropic_sky_radiation_correction()
        else:
            f_sky = (1 + math.cos(tilt_surf)) / 2.0
        f_grnd = (1 - math.cos(tilt_surf)) / 2.0
        irr_dir = irr_beam * math.cos(ia)
        irr_dif = f_sky * irr_dif + f_grnd * rho_grnd * irr_gl_hor
        return irr_dir + irr_dif

    def _check_shadowing(self):
        if self.surface.hz_profile:
            azi_sun = self.sun_pos.azimuth('deg')
            elev_sun = self.sun_pos.elevation('deg')
            elev_hzp = self.surface.hz_profile.elevation(azi_sun)
            if elev_sun < elev_hzp:
                return True
        return False

    def calculate_irradiance(self, irr_gl_hor, rho_grnd=0.2, model='anisotropic'):
        irr_dif = self._irradiance_diffuse(irr_gl_hor)
        if self._check_shadowing():
            irr_beam = 0.0
        else:
            irr_beam = self._irradiance_beam(irr_gl_hor, irr_dif)
        return self._irradiance_surf(irr_beam, irr_dif, irr_gl_hor, rho_grnd, model)
