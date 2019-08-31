from typing import List, Optional, Tuple, Dict
import collections
import math

import numpy as np

from nummath import roots, graphing, interpolation
from sun.energy import Surface, SunEnergyCalculator
from sun.geometry import SunPositionCalculator, Location
from sun.horizon import HorizonProfile
from quantities.date_time import Date, Time
import photovoltaic.auxiliary_components as pv_aux
import photovoltaic.exceptions as pv_err


class AWC:
    def __init__(self, Isc, Voc, Impp, Vmpp, G, Tc):
        self.Isc = Isc                          # short circuit current [A]
        self.Voc = Voc                          # open circuit voltage [V]
        self.Impp = Impp                        # maximum power point current [A]
        self.Vmpp = Vmpp                        # maximum power point voltage [V]
        self.Pmpp = self.Impp * self.Vmpp       # maximum power point power [W]
        self.G = G                              # irradiance [W/m²]
        self.Tc = Tc                            # cell temperature [°C]


class STC(AWC):
    def __init__(self, Isc, Voc, Impp, Vmpp):
        super().__init__(Isc, Voc, Impp, Vmpp, G=1000.0, Tc=25.0)


class TemperatureCoefficients:
    def __init__(self, cIsc, cVoc, cImpp=None, cVmpp=None, cPmpp=None):  # all parameters must be in %/°C
        self.Isc = cIsc / 100.0
        self.Voc = cVoc / 100.0
        self.Impp = cImpp / 100.0 if cImpp else self.Isc
        self.Vmpp = cVmpp / 100.0 if cVmpp else self.Voc
        self.Pmpp = cPmpp / 100.0 if cPmpp else 0.0


class PhotoVoltaicCharacteristics:
    def __init__(self, stc: STC, tco: TemperatureCoefficients, noct: float, Irev_max=None):
        self.stc = stc
        self.tco = tco

        # default actual working conditions set at STC
        self.awc = AWC(
            Isc=self.stc.Isc,
            Voc=self.stc.Voc,
            Impp=self.stc.Impp,
            Vmpp=self.stc.Vmpp,
            G=self.stc.G,
            Tc=self.stc.Tc
        )
        self.noct = noct
        self.Irev_max = Irev_max if Irev_max else self.stc.Isc

        self.Tamb = 20.0    # ambient temperature [°C]
        self._Rpv = 0.0     # photovoltaic resistor [ohm]
        self._Vt = 0.0      # temperature voltage [V]
        self._I0 = 0.0      # reversed saturation current [A]
        self._axI = None    # current axis of V,I-characteristic
        self._axV = None    # voltage axis of V,I- or V,P-characteristic
        self._axP = None    # power axis of V,P-characteristic

        # default characteristics are under stc
        self._calculate_characteristics()

    def set_irradiance(self, val):
        self.awc.G = val
        # self._calculate_awc()
        # self._calculate_characteristics()

    def set_cell_temperature(self, val):
        self.awc.Tc = val
        # self._calculate_awc()
        # self._calculate_characteristics()

    def set_ambient_temperature(self, val):
        self.Tamb = val
        self.awc.Tc = self.Tamb + (self.noct - 20.0) / 800.0 * self.awc.G
        # self._calculate_awc()
        # self._calculate_characteristics()

    def calculate_characteristics(self):
        self._calculate_awc()
        self._calculate_characteristics()

    def _calculate_awc(self):
        d_Tc = self.stc.Tc - self.awc.Tc
        self.awc.Isc = self.stc.Isc * (self.awc.G / self.stc.G) * (1.0 - self.tco.Isc * d_Tc)
        self.awc.Voc = self.stc.Voc * (1.0 - self.tco.Voc * d_Tc)
        self.awc.Impp = self.stc.Impp * (self.awc.G / self.stc.G) * (1.0 - self.tco.Impp * d_Tc)
        self.awc.Vmpp = self.stc.Vmpp * (1.0 - self.tco.Vmpp * d_Tc)
        self.awc.Pmpp = self.awc.Impp * self.awc.Vmpp

    def _calculate_characteristics(self):
        if self.awc.Pmpp != 0.0:
            k = [-5.411, 6.450, 3.417, -4.422]
            k[0] = k[0] * (self.awc.Impp * self.awc.Vmpp) / (self.awc.Isc * self.awc.Voc)
            k[1] = k[1] * self.awc.Vmpp / self.awc.Voc
            k[2] = k[2] * self.awc.Impp / self.awc.Isc
            grad = (self.awc.Voc / self.awc.Isc) * sum(k)
            ir = self.awc.Isc / self.awc.Impp
            self._Rpv = -grad * ir + (self.awc.Vmpp / self.awc.Impp) * (1.0 - ir)
            self._Vt = -(grad + self._Rpv) * self.awc.Isc
            self._I0 = self.awc.Isc / np.exp(self.awc.Voc / self._Vt)
            self._axV = np.linspace(0.0, self.awc.Voc, endpoint=True)
            self._axI = np.array([self._calculate_current(V) for V in self._axV])
            self._axP = self._axI * self._axV
        else:
            self._axV = np.linspace(0.0, self.awc.Voc, endpoint=True)
            self._axI = np.array([0.0 for _ in self._axV])
            self._axP = self._axI * self._axV

    def _calculate_current(self, V):
        def func(I):
            return I - self.awc.Isc + self._I0 * (np.exp((V + I * self._Rpv) / self._Vt) - 1.0)

        solver = roots.FunctionRootSolver(func, [0.0, self.awc.Isc], 0.1)
        zeros = solver.solve()
        try:
            return zeros[0]
        except IndexError:
            return 0.0

    def plot_characteristic(self, which, size=None, dpi=None, title=None):
        if which in ['current', 'power']:
            if which == 'current':
                name, y_title, y_axis = 'V,I', 'I[A]', self._axI
            else:
                name, y_title, y_axis = 'V,P', 'P[W]', self._axP
            graph = graphing.Graph(fig_size=size, dpi=dpi)
            graph.add_data_set(name=name, x=self._axV, y=y_axis)
            graph.set_axis_titles(x_title='V[V]', y_title=y_title)
            if title:
                graph.set_graph_title(title)
            graph.turn_grid_on()
            graph.draw_graph()
            return graph
        return None

    def get_characteristics(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self._axV, self._axI, self._axP


Orientation = collections.namedtuple('Orientation', ['azimuth', 'tilt'])
Dimensions = collections.namedtuple('Dimensions', ['width', 'height'])


class SolarPanel(Surface):
    def __init__(
            self,
            loc: Location,
            orient: Orientation,
            dim: Dimensions,
            pv_char: PhotoVoltaicCharacteristics,
            hz_profile: HorizonProfile = None
    ):
        self.pv_char = pv_char
        self.loc = loc
        self.hz_profile = None
        self.group = None  # used in SolarPanelMatrix where solar panels are grouped according to their horizon profile
        self.orient = orient
        self.dim = dim
        super().__init__(orient.azimuth, orient.tilt, dim.width, dim.height, hz_profile)

    def set_operating_conditions(
            self,
            date: Date = None,
            time: Time = None,
            Gsurf: float = None,
            Gglh: float = None,
            Tcell: float = None,
            Tambient: float = None
    ):
        if None not in (date, time, Gglh, Tambient):
            if Gglh > 0.0:
                sp = SunPositionCalculator.calculate_position(self.loc, date, time)
                G = SunEnergyCalculator(sp, self, date.day_number).calculate_irradiance(Gglh)
                self.pv_char.set_irradiance(G)
            else:
                self.pv_char.set_irradiance(0.0)
            self.pv_char.set_ambient_temperature(Tambient)
        if None not in (Gsurf, Tambient):
            self.pv_char.set_irradiance(Gsurf)
            self.pv_char.set_ambient_temperature(Tambient)
        if None not in (Gsurf, Tcell):
            self.pv_char.set_irradiance(Gsurf)
            self.pv_char.set_cell_temperature(Tcell)
        self.pv_char.calculate_characteristics()

    def get_solar_power(self) -> float:
        return self.pv_char.awc.G * self.area

    def get_mpp_power(self) -> float:
        return self.pv_char.awc.Pmpp

    def get_mpp_voltage(self) -> float:
        return self.pv_char.awc.Vmpp

    def get_mpp_current(self) -> float:
        return self.pv_char.awc.Impp

    def get_oc_voltage(self) -> float:
        return self.pv_char.awc.Voc

    def get_sc_current(self) -> float:
        return self.pv_char.awc.Isc

    def duplicate(self) -> 'SolarPanel':
        return type(self)(
            loc=self.loc,
            orient=self.orient,
            dim=self.dim,
            pv_char=self.pv_char,
            hz_profile=self.hz_profile
        )


class SolarPanelMatrix:
    def __init__(self, id_: str, row_num: int, col_num: int):
        self.id = id_
        self.row_num = row_num  # number of solar panels in one string
        self.col_num = col_num  # number of strings
        self.matrix: List[List[Optional[SolarPanel]]] = [[None for _ in range(col_num)] for _ in range(row_num)]
        # put panels with the same horizon profile in a separate group (see group_panel(...))
        self._panel_groups = {'default': []}

        self.string_protection = pv_aux.CurrentProtection()
        self.string_cables = pv_aux.StringCables(self)
        self.col_max = 0        # max. permissible number of strings in the matrix without current protection
        self.prot_max_str = 0   # max. permissible number of strings per protective device
        self.prot_str = 0       # number of strings per protective device to be set by user

    def add_solar_panel(self, solar_panel: SolarPanel, i_row: int, i_col: int):
        if (0 <= i_row < self.row_num) and (0 <= i_col < self.col_num):
            solar_panel = solar_panel.duplicate()
            self.matrix[i_row][i_col] = solar_panel  # add solar panel to matrix
            self._group_panel(solar_panel)  # add solar panel to horizon profile group
        else:
            raise IndexError

    def set_operating_conditions(
            self,
            date: Date = None,
            time: Time = None,
            Gsurf: float = None,
            Gglh: float = None,
            Tcell: float = None,
            Tambient: float = None
    ):
        # the operating conditions are only set to the first panel in each horizon profile group
        # this is the index panel of each group
        for panel_group in self._panel_groups.values():
            try:
                solar_panel = panel_group[0]
            except IndexError:
                pass
            else:
                solar_panel.set_operating_conditions(date, time, Gsurf, Gglh, Tcell, Tambient)

    def get_solar_power(self):
        Prd = 0.0
        for panel_group in self._panel_groups.values():
            try:
                solar_panel = panel_group[0]
            except IndexError:
                pass
            else:
                Prd_panel = solar_panel.get_solar_power()
                Prd_group = Prd_panel * len(panel_group)
                Prd += Prd_group
        return Prd

    def get_mpp_power(self):
        Pmpp = 0.0
        for panel_group in self._panel_groups.values():
            try:
                solar_panel = panel_group[0]
            except IndexError:
                pass
            else:
                Pmpp_panel = solar_panel.get_mpp_power()
                Pmpp_group = Pmpp_panel * len(panel_group)
                Pmpp += Pmpp_group
        return Pmpp

    def get_mpp_voltage(self):
        Vmpp = 0.0
        for r in range(self.row_num):
            solar_panel = self.matrix[r][0]
            index_solar_panel = self._panel_groups[solar_panel.group][0]
            Vmpp_index_solar_panel = index_solar_panel.get_mpp_voltage()
            Vmpp += Vmpp_index_solar_panel
        return Vmpp

    def get_mpp_current(self):
        Impp = 0.0
        for c in range(self.col_num):
            solar_panel = self.matrix[0][c]
            index_solar_panel = self._panel_groups[solar_panel.group][0]
            Impp_index_solar_panel = index_solar_panel.get_mpp_current()
            Impp += Impp_index_solar_panel
        return Impp

    def get_oc_voltage(self):
        Voc = 0.0
        for r in range(self.row_num):
            solar_panel = self.matrix[r][0]
            index_solar_panel = self._panel_groups[solar_panel.group][0]
            Voc_index_solar_panel = index_solar_panel.get_oc_voltage()
            Voc += Voc_index_solar_panel
        return Voc

    def get_sc_current(self):
        Isc = 0.0
        for c in range(self.col_num):
            solar_panel = self.matrix[0][c]
            index_solar_panel = self._panel_groups[solar_panel.group][0]
            Isc_index_solar_panel = index_solar_panel.get_sc_current()
            Isc += Isc_index_solar_panel
        return Isc

    def get_characteristics(self):
        solar_panel = self.matrix[0][0]
        index_solar_panel = self._panel_groups[solar_panel.group][0]
        Vax, Iax, Pax = index_solar_panel.pv_char.get_characteristics()
        Vax = Vax * self.row_num
        Iax = Iax * self.col_num
        Pax = Vax * Iax
        return Vax, Iax, Pax

    def get_max_reverse_current(self):
        solar_panel = self.matrix[0][0]
        return (self.col_num - 1) * 1.25 * solar_panel.pv_char.stc.Isc

    def check_string_current_protection(self, Np: int = 1):
        """
        Check if over-current protection of strings is required.
        Parameter 'Np' is the number of strings that one wants to be connected to the same protection device.
        As a general rule each string will have its own protection device, so the default value of Np is equal to 1.
        The function returns False if no protection is required.
        Otherwise it will return True and it will:
        (1) calculate the min. and max. limit for the nominal current of the string current protection device,
        (2) calculate the min. voltage withstand limit of the protection device.
        The user must then set:
        (1) the type of the selected protection device (see class 'CurrentProtection', property 'device' in
            auxiliary.py).
        (2) the nominal current of the selected protection device (see class 'CurrentProtection',
            property 'nominal_current' in auxiliary.py).
        (3) the nominal voltage of the selected protection device (see class 'CurrentProtection',
            property 'nominal_voltage' in auxiliary.py).
        """
        solar_panel = self.matrix[0][0]
        if not self._check_current_protection_requirement(): return False
        if Np > self.prot_max_str:
            raise pv_err.ProtectionError('number of strings per protective device too high')
        if Np <= self.prot_max_str:
            self.prot_str = Np
            if Np == 1:
                self.string_protection.set_current_min_max_limit(
                    1.4 * solar_panel.pv_char.stc.Isc,
                    solar_panel.pv_char.Irev_max
                )
            elif Np > 1:
                self.string_protection.set_current_min_max_limit(
                    Np * 1.4 * solar_panel.pv_char.stc.Isc,
                    solar_panel.pv_char.Irev_max - (Np - 1) * solar_panel.pv_char.stc.Isc
                )
            self.string_protection.set_voltage_min_limit(V_nom_min=1.2 * solar_panel.pv_char.stc.Voc * self.col_num)
        return True

    def _check_current_protection_requirement(self):
        """
        Helper method of 'check_string_protection'.
        Checks if a current protection device is needed in order to protect strings against excessive reverse current.
        """
        self._calc_max_allowed_number_strings()
        if self.col_num > self.col_max:
            return True  # current protection is required
        return False

    def _calc_max_allowed_number_strings(self):
        """
        Helper method of '_check_current_protection_requirement'.
        It calculates the maximum allowed number of strings in a matrix considering the maximum reverse current that
        PV modules in the matrix can withstand.
        It also calculates the maximum number of strings that can be grouped and connected to one protective device.
        (Note: as a general rule each string will have its own protective device.)
        """
        solar_panel = self.matrix[0][0]
        # if the sustainable max. reverse current of a string or module is known, the max. number of parallel strings
        # without a protective device:
        self.col_max = int(1 + solar_panel.pv_char.Irev_max // solar_panel.pv_char.stc.Isc)
        # if protective devices will be grouped, the maximum number of strings per protective device is determined from:
        self.prot_max_str = int((1 + solar_panel.pv_char.Irev_max // solar_panel.pv_char.stc.Isc) / 2.4)

    def _group_panel(self, solar_panel: SolarPanel):
        # put solar panels that have the same horizon profile in separate groups
        if solar_panel.hz_profile:
            if solar_panel.hz_profile.id not in self._panel_groups.keys():
                # create new group
                new_group = [solar_panel]
                self._panel_groups[solar_panel.hz_profile.id] = new_group
            else:
                # add solar panel to existing group
                self._panel_groups[solar_panel.hz_profile.id].append(solar_panel)
            # each solar panel knows to which group it belongs
            solar_panel.group = solar_panel.hz_profile.id
        else:
            # if solar panel has no horizon profile (None), put it in 'default' group
            self._panel_groups['default'].append(solar_panel)
            solar_panel.group = 'default'


class Inverter:
    ERR_P_AC_NOM = "inverter nominal AC power out of limits"
    ERR_V_DC_MAX = "inverter maximum DC voltage too low"
    ERR_V_MPP_MIN = "inverter minimum MPP voltage too high"
    ERR_I_DC_MAX = "inverter maximum DC current too low"
    ERR_P_DC_MAX = "inverter maximum DC power too low"

    def __init__(self, id_):
        self.id = id_
        self.Pac_nom = 0.0
        self.Vdc_nom = 0.0
        self.Vdc_max = 0.0
        self.Vmpp_min = 0.0
        self.Vmpp_max = 0.0
        self.Idc_max = 0.0
        self.Pdc_max = 0.0
        self.Pdc_nom = 0.0

        self.eff_max = 0.0
        self.eff_avg = 0.0
        self.eff_at_Vmpp_min = {}  # part load efficiencies at V_mpp_min
        self.eff_at_Vdc_nom = {}   # part load efficiencies at V_dc_nom
        self.eff_at_Vmpp_max = {}  # part load efficiencies at V_mpp_max
        self._eff_interpolants = []

        self.Tc_min = -10.0
        self.Tc_max = 70.0
        self.Tc_Glow = 30.0
        self.Glow = 100.0
        self.Tc_pl = 10.0

        self.pv_matrices: List[SolarPanelMatrix] = []

    def setup(self, **kwargs):
        self.Pac_nom = kwargs.get('Pac_nom', 0.0)
        self.Pdc_nom = self.Pac_nom
        self.Vdc_nom = kwargs.get('Vdc_nom', 0.0)
        self.Vdc_max = kwargs.get('Vdc_max', 0.0)
        self.Vmpp_min = kwargs.get('Vmpp_min', 0.0)
        self.Vmpp_max = kwargs.get('Vmpp_max', 0.0)
        self.Idc_max = kwargs.get('Idc_max', 0.0)
        self.Pdc_max = kwargs.get('Pdc_max', 0.0)
        self.eff_avg = kwargs.get('eff_avg', 0.0)
        self.eff_max = kwargs.get('eff_max', 0.0)

    def get_maximum_string_size(self, pv_module: SolarPanel):
        """Get maximum allowable number of solar panels in one string."""
        pv_module.pv_char.set_irradiance(pv_module.pv_char.stc.G)
        pv_module.pv_char.set_cell_temperature(self.Tc_min)
        return int(self.Vdc_max / pv_module.pv_char.awc.Voc)

    def get_minimum_string_size(self, pv_module: SolarPanel):
        """Get minimum allowable number of solar panels in one string."""
        pv_module.pv_char.set_irradiance(pv_module.pv_char.stc.G)
        pv_module.pv_char.set_cell_temperature(self.Tc_max)
        return int(self.Vmpp_min / pv_module.pv_char.awc.Voc)

    def get_maximum_number_of_strings(self, pv_module: SolarPanel):
        """
        Get maximum allowable number of parallel strings that can be
        connected to one MPPT-input of the given inverter.
        """
        return int(self.Idc_max / (1.25 * pv_module.pv_char.stc.Impp))

    def add_pv_matrix(self, pv_matrix: SolarPanelMatrix):
        self.pv_matrices.append(pv_matrix)

    def check(self):
        """Check if working range of specified inverter respects requirements."""
        warnings = []
        if not self._check_ac_power():
            warnings.append(Inverter.ERR_P_AC_NOM)
        if not self._check_max_input_voltage():
            warnings.append(Inverter.ERR_V_DC_MAX)
        if not self._check_min_mpp_voltage():
            warnings.append(Inverter.ERR_V_MPP_MIN)
        if not self._check_dc_current_limit():
            warnings.append(Inverter.ERR_I_DC_MAX)
        if not self._check_dc_power_limit():
            warnings.append(Inverter.ERR_P_DC_MAX)
        return warnings

    def _check_ac_power(self):
        Pac_min, Pac_max = self._required_ac_power_range()
        if Pac_min <= self.Pac_nom <= Pac_max:
            return True
        else:
            return False

    def _required_ac_power_range(self):
        Ppv_peak = 0.0
        for pv_matrix in self.pv_matrices:
            pv_matrix.set_operating_conditions(Tcell=25.0, Gsurf=1000.0)
            Ppv_peak += pv_matrix.get_mpp_power()
        return 0.8 * Ppv_peak, 1.2 * Ppv_peak

    def _check_max_input_voltage(self):
        req_Vdc_max = self._required_max_input_voltage()
        if self.Vdc_max > req_Vdc_max:
            return True
        else:
            return False

    def _required_max_input_voltage(self):
        # G = 1000.0, Tc = self.Tc_min
        req_Vdc_max = 0.0
        for pv_matrix in self.pv_matrices:
            pv_matrix.set_operating_conditions(Tcell=self.Tc_min, Gsurf=1000.0)
            Voc = pv_matrix.get_oc_voltage()
            if Voc > req_Vdc_max:
                req_Vdc_max = Voc
        return req_Vdc_max

    def _check_min_mpp_voltage(self):
        req_Vmpp_min = self._required_min_mpp_voltage()
        if self.Vmpp_min < req_Vmpp_min:
            return True
        else:
            return False

    def _required_min_mpp_voltage(self):
        # G = 1000.0, Tc = self.Tc_max
        # G = self.Glow, Tc = self.Tc_Glow
        req_Vmpp_min = math.inf
        for pv_matrix in self.pv_matrices:
            pv_matrix.set_operating_conditions(Tcell=self.Tc_max, Gsurf=1000.0)
            Vmpp_Tmax = pv_matrix.get_mpp_voltage()
            pv_matrix.set_operating_conditions(Tcell=self.Tc_Glow, Gsurf=self.Glow)
            Vmpp_Tlg = pv_matrix.get_mpp_voltage()
            Vmpp_min = min(Vmpp_Tmax, Vmpp_Tlg)
            if Vmpp_min < req_Vmpp_min:
                req_Vmpp_min = Vmpp_min
        return req_Vmpp_min

    def _check_dc_current_limit(self):
        req_Idc_max = self._required_dc_current_limit()
        if self.Idc_max > req_Idc_max:
            return True
        else:
            return False

    def _required_dc_current_limit(self):
        req_Idc_max = 0.0
        for pv_matrix in self.pv_matrices:
            pv_matrix.set_operating_conditions(Tcell=25.0, Gsurf=1000.0)
            Idc_max = 1.25 * pv_matrix.get_mpp_current()
            if Idc_max > req_Idc_max:
                req_Idc_max = Idc_max
        return req_Idc_max

    def _check_dc_power_limit(self):
        req_Pdc_max = self._required_dc_power_limit()
        if self.Pdc_max > req_Pdc_max:
            return True
        else:
            return False

    def _required_dc_power_limit(self):
        req_Pdc_max = 0.0
        for pv_matrix in self.pv_matrices:
            pv_matrix.set_operating_conditions(Tcell=self.Tc_pl, Gsurf=1000.0)
            req_Pdc_max += pv_matrix.get_mpp_power()
        return req_Pdc_max

    def get_requirements(self) -> Dict[str, Tuple[float, str]]:
        """Get the required specs of the inverter's working range for the given PV matrices."""
        Pac_min, Pac_max = self._required_ac_power_range()
        return {
            'Pac_min': (Pac_min, 'W'),
            'Pac_max': (Pac_max, 'W'),
            'Vdc_max': (self._required_max_input_voltage(), 'V'),
            'Vmpp_min': (self._required_min_mpp_voltage(), 'V'),
            'Idc_max': (self._required_dc_current_limit(), 'A'),
            'Pdc_max': (self._required_dc_power_limit(), 'W')
        }

    def set_part_load_efficiencies(
            self,
            eff_at_Vmpp_min: Dict[int, float],
            eff_at_Vdc_nom: Dict[int, float],
            eff_at_Vmpp_max: Dict[int, float]
    ):
        self.eff_at_Vmpp_min = eff_at_Vmpp_min
        self.eff_at_Vdc_nom = eff_at_Vdc_nom
        self.eff_at_Vmpp_max = eff_at_Vmpp_max
        self._interpolate_efficiency()

    def _interpolate_efficiency(self):
        self._eff_interpolants = []
        for dict_ in (self.eff_at_Vmpp_min, self.eff_at_Vdc_nom, self.eff_at_Vmpp_max):
            P_ax = [(percent / 100.0) * self.Pdc_nom for percent in dict_.keys()]
            eff_ax = [eff / 100.0 for eff in dict_.values()]
            self._eff_interpolants.append(interpolation.CubicSplineInterPol(P_ax, eff_ax))

    def get_inverter_efficiency(self, Pdc, Vdc):
        if self._eff_interpolants:
            # efficiencies at power Pdc and at Vmpp_min, Vdc_nom and Vmpp_max of inverter
            eff = [ip.solve(Pdc) for ip in self._eff_interpolants]
            # interpolate efficiency = f(Vdc, Pdc=cst.) to find efficiency at Vdc
            V = [self.Vmpp_min, self.Vdc_nom, self.Vmpp_max]
            ip = interpolation.PolyInterPol(V, eff, method='neville')
            eff = ip.solve(Vdc)
        else:
            eff = self.eff_avg / 100.0
        return eff

    def plot_efficiency_curves(self, fig_size=None, dpi=None):
        P_ax = np.linspace(0.05 * self.Pdc_nom, self.Pdc_nom, endpoint=True)
        eff_ax_at_Vmpp_min = np.array([self._eff_interpolants[0].solve(P) for P in P_ax]) * 100.0
        eff_ax_at_Vdc_nom = np.array([self._eff_interpolants[1].solve(P) for P in P_ax]) * 100.0
        eff_ax_at_Vmpp_max = np.array([self._eff_interpolants[2].solve(P) for P in P_ax]) * 100.0
        graph = graphing.Graph(fig_size=fig_size, dpi=dpi)
        graph.add_data_set(f'eff @ Vmpp_min = {self.Vmpp_min} V', P_ax, eff_ax_at_Vmpp_min)
        graph.add_data_set(f'eff @ Vdc_nom = {self.Vdc_nom} V', P_ax, eff_ax_at_Vdc_nom)
        graph.add_data_set(f'eff @ Vmpp_max = {self.Vmpp_max} V', P_ax, eff_ax_at_Vmpp_max)
        graph.set_axis_titles(x_title='DC input power (W)', y_title='efficiency (%)')
        graph.add_legend()
        graph.turn_grid_on()
        graph.draw_graph()
        return graph

    def get_ac_power(self, Pdc: float, Vdc: float) -> float:
        eff = self.get_inverter_efficiency(Pdc, Vdc)
        Pac = eff * Pdc
        return Pac if Pac < self.Pac_nom else self.Pac_nom

    def plot_working_range(self, required_range=False, pv_matrix_id=None, fig_size=None, dpi=None):
        # minimum voltage limit
        Vmpp_min = self.Vmpp_min if not required_range else self._required_min_mpp_voltage()
        Idc_max = self.Idc_max if not required_range else self._required_dc_current_limit()
        Vmin = ([Vmpp_min, Vmpp_min], [0.0, Idc_max])

        # maximum voltage limit
        Vdc_max = self.Vdc_max if not required_range else self._required_max_input_voltage()
        Vmax = ([Vdc_max, Vdc_max], [0.0, Idc_max])

        # maximum current limit
        Imax = ([Vmpp_min, Vdc_max], [Idc_max, Idc_max])

        # maximum power limit
        Pdc_max = self.Pdc_max if not required_range else self._required_dc_power_limit()
        Pdc_max = Pdc_max / len(self.pv_matrices)
        Vax = np.linspace(Vmpp_min, Vdc_max, endpoint=True)
        Iax = Pdc_max / Vax
        Pmax = (Vax, Iax)

        graph = graphing.Graph(fig_size=fig_size, dpi=dpi)
        graph.add_data_set(name='min. voltage limit', x=Vmin[0], y=Vmin[1])
        graph.add_data_set(name='max. voltage limit', x=Vmax[0], y=Vmax[1])
        graph.add_data_set(name='current limit', x=Imax[0], y=Imax[1])
        graph.add_data_set(name='power limit', x=Pmax[0], y=Pmax[1])

        # add PV matrix characteristics to plot that determine the required working range of the inverter
        if pv_matrix_id is None:
            pv_matrix = self.pv_matrices[0]
        else:
            for i, pv_matrix in enumerate(self.pv_matrices):
                if pv_matrix.id == pv_matrix_id:
                    pv_matrix = self.pv_matrices[i]
                    break
            else:
                raise ValueError(f'PV matrix with {pv_matrix_id} not found')

        opcl = [
            (self.Tc_min, 1000.0, f'G=1000.0 | Tc={self.Tc_min}'),
            (self.Tc_max, 1000.0, f'G=1000.0 | Tc={self.Tc_max}'),
            (self.Tc_pl, 1000.0, f'G=1000.0 | Tc={self.Tc_pl}'),
            (self.Tc_Glow, self.Glow, f'G={self.Glow} | Tc={self.Tc_Glow}')
        ]
        for opc in opcl:
            pv_matrix.set_operating_conditions(Tcell=opc[0], Gsurf=opc[1])
            Vax, Iax, Pax = pv_matrix.get_characteristics()
            graph.add_data_set(name=opc[2], x=Vax, y=Iax)

        graph.add_legend()
        graph.set_axis_titles('V [V]', 'I [A]')
        graph.turn_grid_on()
        graph.draw_graph()
        return graph
