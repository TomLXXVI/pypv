"""Auxiliary components of the PV-system."""

########################################################################################################################

import math
from typing import List

import numpy as np

from photovoltaic.exceptions import *
import photovoltaic.main_components as pv_main

########################################################################################################################


class CurrentProtection:
    """
    Class that models a protective device against excessive reverse current through a string or group of strings.
    Strings of a PV matrix require a current protection device if, in case a fault in a string occurs, the reverse
    fault current through the faulty string may exceed the maximum permissible value of reverse current a PV module in
    the string can withstand.
    """
    def __init__(self, I_nom_limits=(0.0, math.inf), V_nom_min=0.0):
        self._I_nom = 0.0
        self._V_nom = 0.0
        self._I_nom_min = I_nom_limits[0]
        self._I_nom_max = I_nom_limits[1]
        self._V_nom_min = V_nom_min
        self._type = 'CB'    # possible values: 'CB' = circuit breaker, 'F' = fuse
        self._I_coc = 0.0    # conventional operating current

    @property
    def device(self):
        """
        Get type of current protection device. Possible values are 'CB' in case of a circuit breaker and 'F' in case
        of a fuse.
        """
        return self._type

    @device.setter
    def device(self, type_):
        """
        Set type of current protection device. Possible values are 'CB' in case of a circuit breaker and 'F' in case
        of a fuse. Any other given type_ will raise a ProtectionError.
        """
        if type_ in ['CB', 'F']:
            self._type = type_
        else:
            raise ProtectionError(f"type {type_} is not recognized. Possible values are 'CB' or 'F'")

    @property
    def nominal_current(self):
        """
        Get the nominal current of the protection device.
        """
        return self._I_nom

    @nominal_current.setter
    def nominal_current(self, I_nom):
        """
        Set the nominal current of the protection device.
        A check is made to see if the nominal current lays between the minimum and maximum required values in order to
        adequately protect the PV modules in the string against excessive reverse current.
        """
        if self._I_nom_min <= I_nom <= self._I_nom_max:
            self._I_nom = I_nom
            self._I_coc = 1.3 * self._I_nom if self._type == 'CB' else 1.45 * self._I_nom
        elif I_nom < self._I_nom_min:
            raise ProtectionError(f'nominal current too low (minimum {self._I_nom_min:.1f} A)')
        else:
            raise ProtectionError(f'nominal current too high (maximum {self._I_nom_max:.1f} A)')

    @property
    def nominal_voltage(self):
        """
        Get the nominal voltage of the protective device.
        """
        return self._V_nom

    @nominal_voltage.setter
    def nominal_voltage(self, V_nom):
        """
        Set the nominal voltage of the protective device.
        A check is made to see if the nominal voltage is at least equal to the minimal required value of voltage the
        protective device must be able to withstand.
        """
        if V_nom >= self._V_nom_min:
            self._V_nom = V_nom
        else:
            raise ProtectionError(f'nominal voltage too low (minimum {self._V_nom_min:.1f} V')

    @property
    def conventional_operating_current(self):
        """
        Get the conventional operating current of the protective device.
        This value will be calculated when the nominal current of the protection device is set
        (see property 'nominal_current').
        """
        return self._I_coc

    @property
    def limits_nominal_current(self):
        """
        Get the lower and upper limit between which the nominal current of the protection device must lay.
        """
        return {'min': self._I_nom_min, 'max': self._I_nom_max}

    @property
    def limits_nominal_voltage(self):
        """
        Get the lower limit above which the nominal voltage of the protection device must lay.
        """
        return {'min': self._V_nom_min}

    def set_current_min_max_limit(self, I_nom_min, I_nom_max):
        """
        Set the lower and upper limit between which the nominal current of the protection device should be selected.
        This function is called by SolarPanelMatrix' method 'check_string_current_protection' (see solarpanel.py).
        """
        self._I_nom_min = I_nom_min
        self._I_nom_max = I_nom_max

    def set_voltage_min_limit(self, V_nom_min):
        """
        Set the minimal required limit above which the nominal voltage of the protection device should be selected.
        This function is called by SolarPanelMatrix' method 'check_string_current_protection' (see solarpanel.py).
        """
        self._V_nom_min = V_nom_min

########################################################################################################################


class SolarCable:
    """Class that models a solar cable."""
    def __init__(self):
        self.min_required_ampacity = 0.0
        self._rho_cu = 1.78e-2  # ohm.mm2/m
        self._rho_al = 2.94e-2  # ohm.mm2/m
        self.length = 0.0  # m
        self._cross_section = 1.0  # mm2
        self.min_cross_section = 0.0  # mm2
        self.voltage_loss = 0.0  # V
        self.power_loss = 0.0  # W
        self._conductor_material = 'Cu'  # possible values: 'Cu' = Copper, 'Al' = Aluminium

    @property
    def conductor_material(self):
        """Get conductor material of cable."""
        return self._conductor_material

    @conductor_material.setter
    def conductor_material(self, conductor_material_: str):
        """
        Set conductor material of cable. Possible values are Copper ('Cu') and Aluminium ('Al').
        If another conductor material is given, a CableError will be raised.
        """
        if conductor_material_ in ['Cu', 'Al']:
            self._conductor_material = conductor_material_
        else:
            raise CableError(f"type {conductor_material_} is not recognized. Possible values are 'Cu' or 'Al'")

    def calc_min_cross_section(self, Vmpp_stc: float, Isc_stc: float):
        """
        Calculate the minimal required cross section of the string cable in order to limit voltage drop across the cable
        at 1% of the string's mpp voltage at STC.
        """
        rho = self._rho_al if self._conductor_material == 'Al' else self._rho_cu
        self.min_cross_section = rho * 2 * self.length * Isc_stc / (0.01 * Vmpp_stc)

    @property
    def cross_section(self):
        """
        Get cross section of string cable.
        """
        return self._cross_section

    @cross_section.setter
    def cross_section(self, cross_section_: float):
        """
        Set cross section of cable.
        If its value is smaller then the minimal required cross section a CableError will be raised.
        """
        if cross_section_ >= self.min_cross_section:
            self._cross_section = cross_section_
        else:
            raise CableError(f'Cross section too small. Need at least {self.min_cross_section} mm2')

    def get_voltage_drop(self, Impp: float):
        """
        Calculate voltage drop across cable for a given string current 'I_mpp'.
        """
        rho = self._rho_al if self._conductor_material == 'Al' else self._rho_cu
        self.voltage_loss = rho * 2 * self.length / self._cross_section * Impp

    def get_power_loss(self, Impp: float):
        """
        Calculate power loss across cable for a given string current 'I_mpp'.
        """
        rho = self._rho_al if self._conductor_material == 'Al' else self._rho_cu
        self.power_loss = rho * 2 * self.length * Impp ** 2 / self._cross_section

########################################################################################################################


class StringCables(List[SolarCable]):
    """
    Class holding the string cables of a PV matrix.
    """
    def __init__(self, pv_matrix: 'pv_main.SolarPanelMatrix'):
        self._pv_matrix = pv_matrix
        super().__init__([SolarCable() for _ in range(self._pv_matrix.col_num)])

    def calc_required_ampacity(self):
        """
        Calculate required ampacity for each string cable in the PV matrix.
        """
        for cable in self:
            self._calc_required_ampacity(cable)

    def _calc_required_ampacity(self, cable: SolarCable):
        """
        Helper method of 'calc_required_current_capacity'. Calculate the minimal required ampacity 'Iz_min' of a string
        cable, passed into the method via parameter 'cable'.
        -   If the number of strings in the PV matrix is not greater than the maximum permissible number
            (calculated by the method _calc_max_allowed_number_strings of class 'PVMatrix') no string current protection
            device is required and the cable must have an ampacity that is at least equal to the maximum value of the
            reverse current that could flow into the string.
        -   If the number of strings in the PV matrix is greater than the maximum permissible number, string current
            protection devices are necessary and extra conditions will determine the required ampacity of the string
            cable based on the number of strings that are connected to one protection device and on the nominal current
            or the conventional operating current of the protection device(s).
        """
        if self._pv_matrix.col_num <= self._pv_matrix.col_max:
            Iz_min = self._pv_matrix.get_max_reverse_current()
        else:
            if self._pv_matrix.prot_str == 1:
                if self._pv_matrix.col_num < 20:
                    Iz_min = self._pv_matrix.string_protection.conventional_operating_current
                else:
                    Iz_min = self._pv_matrix.string_protection.nominal_current
            else:
                K_prot = 1 + (self._pv_matrix.prot_str - 1) / (self._pv_matrix.col_num - self._pv_matrix.prot_str)
                if self._pv_matrix.col_num / self._pv_matrix.prot_str < 20.0:
                    Iz_min = K_prot * self._pv_matrix.string_protection.conventional_operating_current
                else:
                    Iz_min = K_prot * self._pv_matrix.string_protection.nominal_current
        cable.min_required_ampacity = Iz_min

    def calc_min_cross_sections(self):
        solar_panel = self._pv_matrix.matrix[0][0]
        for cable in self:
            cable.calc_min_cross_section(
                Vmpp_stc=solar_panel.pv_char.stc.Vmpp * self._pv_matrix.row_num,
                Isc_stc=solar_panel.pv_char.stc.Isc
            )
        return [self[i].min_cross_section for i in range(len(self))]

    def get_voltage_drop(self):
        solar_panel = self._pv_matrix.matrix[0][0]
        for cable in self:
            cable.get_voltage_drop(Impp=solar_panel.pv_char.awc.Impp)
        return np.mean([cable.voltage_loss for cable in self])

    def get_power_loss(self):
        solar_panel = self._pv_matrix.matrix[0][0]
        for cable in self:
            cable.get_power_loss(Impp=solar_panel.pv_char.awc.Impp)
        return sum([cable.power_loss for cable in self])

    def set_cable_lengths(self, *string_lengths):
        if len(string_lengths) == len(self):
            for cable, length in zip(self, string_lengths):
                cable.length = length
        else:
            raise CableError('number of given string lengths is not equal to number of string cables')

    def set_cross_sections(self, *cross_sections):
        if len(cross_sections) == len(self):
            # calculate and set the required minimum cross section of each cable
            self.calc_min_cross_sections()
            # assign the given cross sections to each cable; note that 'cable.cross_section' is property that will
            # check if the given cross_section of each cable is at least equal to what's minimal required.
            for cable, cross_section in zip(self, cross_sections):
                cable.cross_section = cross_section
        else:
            raise CableError('number of given cross sections is not equal to number of string cables')

########################################################################################################################


class Battery:
    """
    Class that represents a battery. This class is used by EnergyAnalyzer for estimating self-consumption and
    self-sufficiency in case battery storage is used to store energy excesses during daylight time.
    """
    def __init__(self, battery_capacity):
        self.level_max = battery_capacity
        self.level_actual = 0.0
        self.capacity_available = self.level_max - self.level_actual

        self.P_loading = math.inf    # power that can be put into battery
        self.P_unloading = math.inf  # power that can be extracted from battery
        self.E_loading = math.inf    # energy that can be put into battery
        self.E_unloading = math.inf  # energy that can be extracted from battery
        self.dt = 0.0

    def set_loading_params(self, Idc, Vdc, eff=1.0):
        # power that can be accepted by battery
        self.P_loading = eff * Idc * Vdc

    def set_unloading_params(self, Idc, Vdc, eff=1.0):
        # power that can be extracted from battery
        self.P_unloading = eff * Idc * Vdc

    def set_time_interval(self, dt):
        self.E_loading = self.P_loading * dt
        self.E_unloading = self.P_unloading * dt

########################################################################################################################
