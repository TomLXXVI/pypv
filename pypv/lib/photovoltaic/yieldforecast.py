import numpy as np
import pandas as pd

from sun.geometry import SunPositionCalculator
from photovoltaic.datafetch import TMYDataFetcher, CLPDataFetcher
from photovoltaic.auxiliary_components import Battery
from nummath import interpolation, integration, graphing
from quantities.date_time import DateTime, Date, Time, ANY_YEAR


class DailyYield:
    """Class for performing PV yield analysis on daily basis."""

    def __init__(self, dataset, pv_inverters):
        self.date = dataset['date']
        self.t_ax = dataset['time']
        self.T_ax = dataset['temperature']
        self.Gglh_ax = dataset['irradiance']
        self.inverters = pv_inverters
        self.pv_matrices = [pv_matrix for inverter in self.inverters for pv_matrix in inverter.pv_matrices]
        self.loc = self.pv_matrices[0].matrix[0][0].loc
        self.pvm_container = {}
        self.inv_container = {}

    def analyze(self):
        """Perform energy analysis on daily basis."""
        self._setup_datastructs()
        self._calculate_powers()
        self._calculate_interpolants()
        self._calculate_energies()

    def get_energies(self):
        """Return list with daily solar energy, MPP energy, DC energy input and AC energy output."""
        Erd = 0.0; Empp = 0.0; Ein = 0.0; Eout = 0.0
        for pvm_box in self.pvm_container.values():
            Erd += pvm_box['Erd']
            Empp += pvm_box['Empp']
        for inv_box in self.inv_container.values():
            Ein += inv_box['Ein']
            Eout += inv_box['Eout']
        return [Erd, Empp, Ein, Eout]

    def get_ac_power(self, t: Time):
        """Return interpolated AC power from PV inverter(s) at time t."""
        t = t.as_decimal_hour
        Pout = 0.0
        for inv_box in self.inv_container.values():
            Pout_ip = inv_box['Pout_ip']
            Pout += Pout_ip.solve(t)
        return Pout

    def ac_power_coords(self):
        """Generator that returns (t, Pout) for every t in self.t_ax with Pout the output power from inverter(s)."""
        for inv_box in self.inv_container.values():
            Pout_ax = inv_box['Pout_ax']
            for t, Pout in zip(self.t_ax, Pout_ax):
                yield t, Pout

    def _setup_datastructs(self):
        for pv_matrix in self.pv_matrices:
            pvm_box = {
                'id': pv_matrix.id,
                'Prd_ax': [],
                'Pmpp_ax': [],
                'Pout_ax': [],
                'Prd_ip': None,
                'Pmpp_ip': None,
                'Pout_ip': None,
                'Erd': 0.0,
                'Empp': 0.0,
                'Eout': 0.0
            }
            self.pvm_container[pv_matrix.id] = pvm_box

        for inverter in self.inverters:
            inv_box = {
                'id': inverter.id,
                'Pin_ax': [],
                'Pout_ax': [],
                'Pin_ip': None,
                'Pout_ip': None,
                'Ein': 0.0,
                'Eout': 0.0
            }
            self.inv_container[inverter.id] = inv_box

    def _calculate_powers(self):
        for t, Gglh, T in zip(self.t_ax, self.Gglh_ax, self.T_ax):
            for inverter in self.inverters:
                Pin = 0.0; Vdc = []
                for pv_matrix in inverter.pv_matrices:
                    pv_matrix.set_operating_conditions(date=self.date, time=t, Gglh=Gglh, Tambient=T)
                    Prd = pv_matrix.get_solar_power()
                    self.pvm_container[pv_matrix.id]['Prd_ax'].append(Prd)
                    Pmpp = pv_matrix.get_mpp_power()
                    self.pvm_container[pv_matrix.id]['Pmpp_ax'].append(Pmpp)
                    Vmpp = pv_matrix.get_mpp_voltage()
                    Plo = pv_matrix.string_cables.get_power_loss()
                    Vlo = pv_matrix.string_cables.get_voltage_drop()
                    Pout = Pmpp - Plo  # output from matrix
                    self.pvm_container[pv_matrix.id]['Pout_ax'].append(Pout)
                    Pin += Pout  # total input at inverter
                    Vdc.append(Vmpp - Vlo)
                Vdc_avg = sum(Vdc) / len(Vdc)  # average Vdc across inverter inputs
                Pout = inverter.get_ac_power(Pin, Vdc_avg)  # total output at inverter
                self.inv_container[inverter.id]['Pin_ax'].append(Pin)
                self.inv_container[inverter.id]['Pout_ax'].append(Pout)

    def _calculate_interpolants(self):
        for pvm_box in self.pvm_container.values():
            pvm_box['Prd_ip'] = self._interpolant(pvm_box['Prd_ax'])
            pvm_box['Pmpp_ip'] = self._interpolant(pvm_box['Pmpp_ax'])
            pvm_box['Pout_ip'] = self._interpolant(pvm_box['Pout_ax'])

        for inv_box in self.inv_container.values():
            inv_box['Pin_ip'] = self._interpolant(inv_box['Pin_ax'])
            inv_box['Pout_ip'] = self._interpolant(inv_box['Pout_ax'])

    def _calculate_energies(self):
        for pvm_box in self.pvm_container.values():
            pvm_box['Erd'] = self._integrate(pvm_box['Prd_ip'])
            pvm_box['Empp'] = self._integrate(pvm_box['Pmpp_ip'])
            pvm_box['Eout'] = self._integrate(pvm_box['Pout_ip'])

        for inv_box in self.inv_container.values():
            inv_box['Ein'] = self._integrate(inv_box['Pin_ip'])
            inv_box['Eout'] = self._integrate(inv_box['Pout_ip'])

    def _interpolant(self, y_data):
        return interpolation.CubicSplineInterPol(
            x_data=[t.as_decimal_hour for t in self.t_ax],
            y_data=y_data
        )

    def _integrate(self, interpolant):
        def integrand(t_):
            return interpolant.solve(t_)

        sunrise = SunPositionCalculator.sunrise(self.loc, self.date)
        sunset = SunPositionCalculator.sunset(self.loc, self.date)

        integrator = integration.SingleIntegration(
            integrand,
            sunrise.as_decimal_hour,
            sunset.as_decimal_hour
        )
        return integrator.solve()[0] / 1000.0  # kWh


class AnnualYield:
    """Class for performing PV yield analysis between a start and end date (end date included)."""

    def __init__(self, TMY_file, location, pv_inverters):
        # get daily TMY datasets
        tmy = TMYDataFetcher(TMY_file, tz_str=location.timezone)
        tmy_data = tmy.get_daily_datasets()

        # create DailyYield-objects and store them in a dict container
        self.dyo_container = {
            str(dataset['date']): DailyYield(dataset, pv_inverters)
            for dataset in tmy_data
        }

        self.df = None

    def get_daily_yields(self, start_date, end_date=None):
        """Return DailyYield objects between start date and end date (included)."""
        if not end_date:
            return self.dyo_container[str(start_date)]
        else:
            all_dates = list(self.dyo_container.keys())
            i_start = all_dates.index(str(start_date))
            i_end = all_dates.index(str(end_date))
            selected_dates = all_dates[i_start:i_end+1]
            return (self.dyo_container[date] for date in selected_dates)

    def analyze(self, start_date: Date, end_date: Date):
        """
        Calculate daily amount of energies for every day between start and end date included.
        These energies are:
            - incident solar energy
            - generated photovoltaic energy
            - DC energy delivered to inverter(s)
            - AC energy produced by inverters.
        The results of every day are stored in a pandas DataFrame 'self.df'.
        The function returns:
            - the summed energy amounts for the specified period (pandas Series object)
            - the minimum energy amounts within the specified period
            - the average energy amounts
            - the maximum energy amounts
        """

        dyo_list = list(self.get_daily_yields(start_date, end_date))

        for dyo in dyo_list:
            dyo.analyze()

        # put all daily energies in a DataFrame
        #   - Erd = total solar energy between start and end date
        #   - Empp = total photovoltaic energy produced by solar panels
        #   - Ein = total DC energy input at inverters
        #   - Eout = total AC energy output of inverters
        columns = ['Erd', 'Empp', 'Ein', 'Eout']
        data = [dyo.get_energies() for dyo in dyo_list]
        index = [str(dyo.date) for dyo in dyo_list]
        self.df = pd.DataFrame(data=data, index=index, columns=columns)
        # get the sum of each column, the minimum and maximum value in each column and the average of each column
        sum_ = self.df.sum(axis=0)
        min_ = self.df.min(axis=0)
        avg_ = self.df.mean(axis=0)
        max_ = self.df.max(axis=0)
        return {'tot': sum_, 'min': min_, 'avg': avg_, 'max': max_}


class DailyLoad:
    """Class for performing load analysis on daily basis."""

    def __init__(self, dataset, location, Ean=1.0):
        self.date = dataset['date']
        self.t_ax = dataset['time']
        self.loc = location

        self.E15_ax = [clv * Ean for clv in dataset['CLP']]  # energy consumption for every 15 minutes of the day [kWh]
        self.P15_ax = [4.0 * E15 for E15 in self.E15_ax]  # average power consumption in every 15 min. interval [kW]
        self.P15_ip = interpolation.CubicSplineInterPol(
            x_data=[t.as_decimal_hour for t in self.t_ax],
            y_data=self.P15_ax
        )
        self.Etot = 0.0
        self.Edt = 0.0
        self.Ent = 0.0

    def analyze(self):
        """Perform load analysis on daily basis."""
        self.Etot = sum(self.E15_ax)  # daily energy consumption [kWh]
        self.Edt = self._calculate_daytime_load()  # energy consumption during daytime
        self.Ent = self.Etot - self.Edt  # energy consumption during nighttime

    def get_energies(self):
        """Return list with daily total energy consumption, consumption during daytime and during nighttime."""
        return [self.Etot, self.Edt, self.Ent]

    def get_power(self, t: Time):
        """Return power consumed by load at time t."""
        t = t.as_decimal_hour
        return self.P15_ip.solve(t)  # unit: kW

    def power_coords(self):
        """Generator that returns (t, Pl) for every t in self.t_ax with Pl the load power."""
        for t, Pl in zip(self.t_ax, self.P15_ax):
            yield t, Pl

    def _calculate_daytime_load(self):
        def integrand(t_):
            return self.P15_ip.solve(t_)

        sunrise = SunPositionCalculator.sunrise(self.loc, self.date)
        sunset = SunPositionCalculator.sunset(self.loc, self.date)

        integrator = integration.SingleIntegration(
            integrand,
            sunrise.as_decimal_hour,
            sunset.as_decimal_hour
        )
        return integrator.solve()[0]  # kWh


class AnnualLoad:
    """Class for performing load analysis between a start and end date (end date included)."""

    def __init__(self, CLP_file, location, Ean=1.0):
        self.loc = location
        self.Ean = Ean  # annual energy consumption (if > 1.0, CLP-file contains synthetic load profile)
        clp = CLPDataFetcher(CLP_file, tz_str=self.loc.timezone)
        CLP_data = clp.get_daily_datasets()

        # create DailyLoad-objects and store them in a dict container
        self.dlo_container = {
            str(dataset['date']): DailyLoad(dataset, self.loc, Ean)
            for dataset in CLP_data
        }

        self.df = None

    def get_daily_loads(self, start_date, end_date=None):
        """Return DailyLoad objects between start date and end date (included)."""
        if not end_date:
            return self.dlo_container[str(start_date)]
        else:
            all_dates = list(self.dlo_container.keys())
            i_start = all_dates.index(str(start_date))
            i_end = all_dates.index(str(end_date))
            selected_dates = all_dates[i_start:i_end + 1]
            return (self.dlo_container[date] for date in selected_dates)

    def analyze(self, start_date, end_date):
        """
        Calculate daily amount of energy consumed by load for every day between start and end date included. 
        Besides total daily energy consumption, consumption during daytime and nighttime is also looked at. 
        The results of every day are stored in a pandas DataFrame 'self.df'.
        The function returns:
            - the summed energy amounts for the specified period (pandas Series object).
            - the minimum energy amounts within the specified period
            - the average energy amounts
            - the maximum energy amounts
        """
        dlo_list = list(self.get_daily_loads(start_date, end_date))

        # analyze DailyLoad-objects between start and end date (included)
        for dlo in dlo_list:
            dlo.analyze()

        # put all daily energies in a DataFrame
        #   - Etot = total energy consumption
        #   - Edt = daytime energy consumption
        #   - Ent = nighttime energy consumption
        columns = ['Etot', 'Edt', 'Ent']
        data = [dlo.get_energies() for dlo in dlo_list]
        index = [str(dlo.date) for dlo in dlo_list]
        self.df = pd.DataFrame(data=data, index=index, columns=columns)
        # get the sum of each column, the minimum and maximum in each column and the average of each column
        sum_ = self.df.sum(axis=0)
        min_ = self.df.min(axis=0)
        avg_ = self.df.mean(axis=0)
        max_ = self.df.max(axis=0)
        return {'tot': sum_, 'min': min_, 'avg': avg_, 'max': max_}


class EnergyAnalyzer:
    """Class for performing PV yield and load analysis."""

    def __init__(self, TMY_file, CLP_file, location, pv_inverters, Ean=1.0):
        self.ay = AnnualYield(TMY_file, location, pv_inverters)
        self.al = AnnualLoad(CLP_file, location, Ean)  # Ean = annual energy consumption
        self._location = location
        self.battery = None
        
        # daily energy flows
        self._Egtl_daily = 0.0  # energy from grid to load
        self._Eptl_daily = 0.0  # energy from PV system to load
        self._Eptg_daily = 0.0  # energy from PV system to grid
        self._Eptb_daily = 0.0  # energy from PV system to battery
        self._Ebtl_daily = 0.0  # energy from battery to load

        # DataFrame with daily energy flows
        self.columns = ['month', 'day', 'Egtl', 'Eptg', 'Eptl', 'Eptb', 'Ebtl']
        self.E_ddf = None

        # tuples of pandas Series with energy analysis results
        self.Eyield_stats = None  # yield stats: sum, min, avg and max of Erd, Empp, Ein and Eout
        self.Eload_stats = None  # load stats: sum, min, avg and max of Etot, Edt, Ent
        self.Eflow_stats = None  # energy flow stats: sum, min, avg and max of EgtL, Eptg, Eptl, Eptb and Ebtl

    def analyze(self, start_date=None, end_date=None):
        """Perform energy analysis: PV yield analysis, load consumption analysis and energy flow analysis."""
        if not start_date or not end_date:
            start_date = Date(ANY_YEAR, 1, 1)
            end_date = Date(ANY_YEAR, 12, 31)

        # 1. analyze AnnualYield: self.Eyield_stats contains:
        # self.Ey_stats['tot'][<'Erd' | 'Empp' | 'Ein' | 'Eout'>] = total between start and end date
        # self.Ey_stats['min'][<'Erd' | 'Empp' | 'Ein' | 'Eout'>] = minimum
        # self.Ey_stats['avg'][<'Erd' | 'Empp' | 'Ein' | 'Eout'>] = average
        # self.Ey_stats['max'][<'Erd' | 'Empp' | 'Ein' | 'Eout'>] = maximum
        self.Eyield_stats = self.ay.analyze(start_date, end_date)

        # 2. analyze AnnualLoad: self.Eload_stats contains:
        # self.El_stats['tot'][<'Etot' | 'Edt' | 'Ent'>] = total Etot, Edt or Ent between start and end date
        # self.El_stats['min'][<'Etot' | 'Edt' | 'Ent'>] = minimum
        # self.El_stats['avg'][<'Etot' | 'Edt' | 'Ent'>] = average
        # self.El_stats['max'][<'Etot' | 'Edt' | 'Ent'>] = maximum
        self.Eload_stats = self.al.analyze(start_date, end_date)

        # 3. analyze daily energy flows between PV system, load, grid and battery: self.Eflow_stats contains:
        # self.Ef_stats['tot'][<'Egtl' | 'Eptg' | 'Eptl' | 'Eptb' | 'Ebtl'>] = total between start and end date
        # self.Ef_stats['min'][<'Egtl' | 'Eptg' | 'Eptl' | 'Eptb' | 'Ebtl'>] = minimum
        # self.Ef_stats['avg'][<'Egtl' | 'Eptg' | 'Eptl' | 'Eptb' | 'Ebtl'>] = average
        # self.Ef_stats['max'][<'Egtl' | 'Eptg' | 'Eptl' | 'Eptb' | 'Ebtl'>] = maximum
        self.Eflow_stats = self.analyze_energy_flows(start_date, end_date)

    def analyze_energy_flows(self, start_date=None, end_date=None):
        """Perform energy flow analysis."""
        if not start_date or not end_date:
            start_date = Date(ANY_YEAR, 1, 1)
            end_date = Date(ANY_YEAR, 12, 31)

        dyo_gen = self.ay.get_daily_yields(start_date, end_date)
        dlo_gen = self.al.get_daily_loads(start_date, end_date)

        # analyze and collect daily energy flows
        data = []
        for dyo, dlo in zip(dyo_gen, dlo_gen):
            row = self._analyze(dyo, dlo)
            data.append(row)

        # create DataFrame with daily energy flows
        self.E_ddf = pd.DataFrame(data=np.array(data), columns=self.columns)

        # for every column in self.E_ddf calculate sum, minimum, average and maximum
        sum_ = self.E_ddf.sum(axis=0)
        min_ = self.E_ddf.min(axis=0)
        avg_ = self.E_ddf.mean(axis=0)
        max_ = self.E_ddf.max(axis=0)
        return {'tot': sum_, 'min': min_, 'avg': avg_, 'max': max_}

    def _analyze(self, dyo: DailyYield, dlo: DailyLoad):
        # reset energy flows
        self._Egtl_daily = 0.0  # energy from grid to load
        self._Eptl_daily = 0.0  # energy from PV system to load
        self._Eptg_daily = 0.0  # energy from PV system to grid
        self._Eptb_daily = 0.0  # energy from PV system to battery
        self._Ebtl_daily = 0.0  # energy from battery to load
        
        self._analyze_daytime(dyo, dlo)
        self._analyze_nighttime(dlo)
        
        return [
            dyo.date.month,
            dyo.date.day,
            self._Egtl_daily,
            self._Eptg_daily,
            self._Eptl_daily,
            self._Eptb_daily,
            self._Ebtl_daily
        ]
    
    def _analyze_daytime(self, dyo: DailyYield, dlo: DailyLoad):
        sunrise = SunPositionCalculator.sunrise(self._location, dyo.date)
        sunset = SunPositionCalculator.sunset(self._location, dyo.date)
        t_ax = np.linspace(sunrise.as_decimal_hour, sunset.as_decimal_hour, endpoint=True).tolist()
        t_ax = [Time.from_decimal_hour(t) for t in t_ax]
        t_ax1 = t_ax[:-1]
        t_ax2 = t_ax[1:]
        for t1, t2 in zip(t_ax1, t_ax2):
            Py1 = dyo.get_ac_power(t1) / 1000.0  # set to kW
            Py2 = dyo.get_ac_power(t2) / 1000.0
            Pl1 = dlo.get_power(t1)  # already kW
            Pl2 = dlo.get_power(t2)
            Py_avg = (Py1 + Py2) / 2.0
            Pl_avg = (Pl1 + Pl2) / 2.0
            dt = t2.as_decimal_hour - t1.as_decimal_hour
            if self.battery: self.battery.set_time_interval(dt)
            Ey = Py_avg * dt
            El = Pl_avg * dt
            # Possibility 1 : pv energy surplus => battery storage and/or grid injection
            if Ey > El:
                self._handle_energy_surplus(Ey, El)
            # Possibility 2: pv energy deficit => supply from battery and/or supply from grid
            elif Ey < El:
                self._handle_energy_deficit(Ey, El)
            # Possibility 3: pv energy matches load => directly to load
            else:
                self._handle_energy_match(El)
                
    def _handle_energy_surplus(self, Ey, El):
        Esur = Ey - El
        # PV system with battery
        if isinstance(self.battery, Battery):
            self._handle_energy_surplus_with_battery(Esur)
        # PV system without battery => grid injection
        else:
            self._Eptg_daily += Esur
        self._Eptl_daily += El
    
    def _handle_energy_surplus_with_battery(self, Esur):
        # battery has loading capacity available (not full)
        if self.battery.capacity_available > 0.0:
            # if surplus is greater than what can be accepted by the battery system -> limit Esur
            if Esur > self.battery.E_loading:
                self._Eptg_daily += (Esur - self.battery.E_loading)
                Esur = self.battery.E_loading
            # battery has enough capacity available
            if Esur <= self.battery.capacity_available:
                self.battery.level_actual += Esur
                self._Eptb_daily += Esur
            # battery has not enough capacity available => surplus: grid injection
            else:
                self._Eptb_daily += self.battery.capacity_available
                self._Eptg_daily += (Esur - self.battery.capacity_available)
                self.battery.level_actual = self.battery.level_max
            self.battery.capacity_available = self.battery.level_max - self.battery.level_actual
        # battery has no loading capacity available (full) => grid injection
        else:
            self._Eptg_daily += Esur
    
    def _handle_energy_deficit(self, Ey, El):
        Edef = El - Ey
        # PV system with battery
        if isinstance(self.battery, Battery):
            self._handle_energy_deficit_with_battery(Edef)
        # PV system without battery => grid supply
        else:
            self._Egtl_daily += Edef
        self._Eptl_daily += Ey
    
    def _handle_energy_deficit_with_battery(self, Edef):
        # battery has unloading capacity available (not empty)
        if self.battery.level_actual > 0.0:
            # deficit is smallest
            if Edef == min(Edef, self.battery.E_unloading, self.battery.level_actual):
                self._Ebtl_daily += Edef
                self.battery.level_actual -= Edef
            # unloading capacity of battery system is smallest
            elif self.battery.E_unloading == min(Edef, self.battery.E_unloading, self.battery.level_actual):
                self._Ebtl_daily += self.battery.E_unloading
                self._Egtl_daily += (Edef - self.battery.E_unloading)
                self.battery.level_actual -= self.battery.E_unloading
            # battery level is smallest
            elif self.battery.level_actual == min(Edef, self.battery.E_unloading, self.battery.level_actual):
                self._Ebtl_daily += self.battery.level_actual
                self._Egtl_daily += (Edef - self.battery.level_actual)
                self.battery.level_actual = 0.0
            self.battery.capacity_available = self.battery.level_max - self.battery.level_actual
        # battery has no unloading capacity available (empty) => grid supply
        else:
            self._Egtl_daily += Edef

    def _handle_energy_match(self, Ey):
        # PV-system with battery: battery is not used when load matches yield
        self._Eptl_daily += Ey

    def _analyze_nighttime(self, dlo: DailyLoad):
        # PV-system does not generate any yield
        sunrise = SunPositionCalculator.sunrise(self._location, dlo.date)
        sunset = SunPositionCalculator.sunset(self._location, dlo.date)
        t_ax = np.linspace(0, Time(23, 59, 59).as_decimal_hour).tolist()
        t_ax = [Time.from_decimal_hour(t) for t in t_ax]
        t_ax1 = t_ax[:-1]
        t_ax2 = t_ax[1:]
        for t1, t2 in zip(t_ax1, t_ax2):
            if t1.as_decimal_hour < sunrise.as_decimal_hour or t1.as_decimal_hour > sunset.as_decimal_hour:
                Pl1 = dlo.get_power(t1)  # already kW
                Pl2 = dlo.get_power(t2)
                Pl_avg = (Pl1 + Pl2) / 2.0
                dt = t2.as_decimal_hour - t1.as_decimal_hour
                if self.battery: self.battery.set_time_interval(dt)
                El = Pl_avg * dt
                Ey = 0
                self._handle_energy_deficit(Ey, El)

    def get_nighttime_load_stats(self):
        return {
            'sum': self.Eload_stats['tot']['Ent'],
            'min': self.Eload_stats['min']['Ent'],
            'avg': self.Eload_stats['avg']['Ent'],
            'max': self.Eload_stats['max']['Ent']
        }

    # -----------------------------------------------------------------------------------------------------------------
    # Following methods are intended to be used when performing a full year analysis.

    def get_monthly_energyflows(self, m_index):
        """
        Return for each energy flow its total for the given month (pandas Series object).
        """
        # in dataframe E_ddf select all rows whose field in columns[0] (month index) matches the given index
        E_mdf = self.E_ddf.loc[self.E_ddf.loc[:, self.columns[0]] == m_index, :]
        # take the sum of all columns in the selected dataframe; these are the total energy flows for the given month
        mef = E_mdf.loc[:, self.columns[2]:self.columns[-1]].sum()
        return mef

    def get_monthly_overview(self):
        """
        Return a pandas DataFrame with the total monthly energy flows and the total annual energy flows.
        """
        # put the monthly energy flows in a list
        mef_list = [self.get_monthly_energyflows(m) for m in range(1, 13)]
        # create a DataFrame with the monthly results
        df = pd.DataFrame(data=mef_list, index=[m for m in range(1, 13)])
        # summing the columns also adds the annual energy flows at the end of the DataFrame
        df.loc['totals'] = df.sum()
        return df

    def print_monthly_overview(self):
        df = self.get_monthly_overview()
        with pd.option_context('display.max_rows', None, 'display.max_columns', None):
            print(df)

    def plot_monthly_overview(self, fig_size=None, dpi=None):
        PtL = []  # PV yield to load and battery
        PtG = []  # PV yield injected into grid
        LfG = []  # load energy taken from grid
        LfP = []  # load energy taken from PV system
        for m_index in range(1, 13):
            mef = self.get_monthly_energyflows(m_index)
            PtL.append(mef['Eptl'] + mef['Eptb'])
            PtG.append(mef['Eptg'])
            LfG.append(mef['Egtl'])
            LfP.append(mef['Eptl'] + mef['Ebtl'])

        graph = graphing.Graph(fig_size=fig_size, dpi=dpi)
        w = 0.4
        graph.add_data_set(
            name='pv energy to load',
            x=np.array([m for m in range(1, 13)]) - w / 2,
            y=PtL,
            bar={'color': 'green', 'width': w}
        )
        graph.add_data_set(
            name='pv energy to grid',
            x=np.array([m for m in range(1, 13)]) - w / 2,
            y=PtG,
            bar={'bottom': PtL, 'color': 'palegreen', 'width': w}
        )
        graph.add_data_set(
            name='energy from pv system',
            x=np.array([m for m in range(1, 13)]) + w / 2,
            y=LfP,
            bar={'color': 'orange', 'width': w}
        )
        graph.add_data_set(
            name='energy from grid',
            x=np.array([m for m in range(1, 13)]) + w / 2,
            y=LfG,
            bar={'bottom': LfP, 'color': 'red', 'width': w}
        )
        graph.add_legend()
        graph.scale_x_axis(lim_min=0, lim_max=13, tick_step=1)
        graph.set_axis_titles(x_title='month', y_title='energy [kWh]')
        graph.turn_grid_on()
        graph.draw_graph()
        return graph

    def get_annual_energyflows(self):
        """
        Return for each energy flow its total for the whole year (pandas Series object).
        """
        return self.E_ddf.loc[:, self.columns[2]:self.columns[-1]].sum()

    def get_annual_yield(self):
        """
        Return the total yield over the whole year.
        """
        # yef = self.get_annual_energyflows()
        # return yef['PtL'] + yef['PtB'] + yef['PtG']
        return self.Eyield_stats['tot']['Eout']

    def get_annual_load(self):
        """
        Return the total load over the whole year.
        """
        # yef = self.get_annual_energyflows()
        # return yef['PtL'] + yef['GtL'] + yef['BtL']
        return self.Eload_stats['tot']['Etot']

    def get_net_consumption(self):
        # difference between energy injected into grid and energy taken from grid
        Eptg = self.get_annual_energyflows()['Eptg']  # grid injection
        Egtl = self.get_annual_energyflows()['Egtl']  # energy consumption from grid
        return Egtl - Eptg

    def get_self_sufficiency(self):
        """
        Self sufficiency is the relative amount of annual load delivered by the PV system (ratio of annual load
        delivered by PV system to total annual load).
        """
        yef = self.get_annual_energyflows()
        LfP = yef['Eptl'] + yef['Ebtl']  # annual load delivered directly by PV system or from battery
        LfG = yef['Egtl']  # annual load delivered by grid
        return LfP / (LfP + LfG) * 100.0

    def get_self_consumption(self):
        """
        Self consumption is the relative amount of annual yield consumed by the loads (ratio of annual yield consumed
        by the loads to total annual yield)
        """
        yef = self.get_annual_energyflows()
        YtL = yef['Eptl'] + yef['Eptb']  # annual yield consumed by loads and stored in battery
        YtG = yef['Eptg']  # annual yield injected into grid
        return YtL / (YtL + YtG) * 100.0

    def plot_self_sufficiency(self, fig_size=None, dpi=None):
        LfP_per = []; LfG_per = []
        for m in range(1, 13):
            mef = self.get_monthly_energyflows(m)
            LfP = mef['Eptl'] + mef['Ebtl']  # monthly load supplied by PV system
            LfG = mef['Egtl']  # monthly load supplied by grid
            Ltot = LfP + LfG
            LfP_per.append(LfP / Ltot * 100.0)
            LfG_per.append(LfG / Ltot * 100.0)

        graph = graphing.Graph(fig_size=fig_size, dpi=dpi)
        graph.add_data_set(
            name='energy from grid',
            x=[m for m in range(1, 13)],
            y=LfG_per,
            bar={'color': 'red', 'align': 'center'}
        )
        graph.add_data_set(
            name='energy from pv system',
            x=[m for m in range(1, 13)],
            y=LfP_per,
            bar={'bottom': LfG_per, 'color': 'green', 'align': 'center'}
        )
        graph.add_legend()
        graph.scale_x_axis(lim_min=0, lim_max=13, tick_step=1)
        graph.scale_y_axis(lim_min=0, lim_max=100, tick_step=10)
        graph.set_axis_titles(x_title='month', y_title='consumption [%]')
        graph.turn_grid_on()
        graph.draw_graph()
        return graph

    def plot_self_consumption(self, fig_size=None, dpi=None):
        YtL_per = []; YtG_per = []
        for m in range(1, 13):
            mef = self.get_monthly_energyflows(m)
            YtL = mef['Eptl'] + mef['Eptb']  # monthly yield consumed by loads
            YtG = mef['Eptg']  # monthly yield injected to grid
            Ytot = YtL + YtG
            YtL_per.append(YtL / Ytot * 100.0)
            YtG_per.append(YtG / Ytot * 100.0)

        graph = graphing.Graph(fig_size=fig_size, dpi=dpi)
        graph.add_data_set(
            name='pv energy to grid',
            x=[m for m in range(1, 13)],
            y=YtG_per,
            bar={'color': 'red', 'align': 'center'}
        )
        graph.add_data_set(
            name='pv energy to load',
            x=[m for m in range(1, 13)],
            y=YtL_per,
            bar={'bottom': YtG_per, 'color': 'green', 'align': 'center'}
        )
        graph.add_legend()
        graph.scale_x_axis(lim_min=0, lim_max=13, tick_step=1)
        graph.scale_y_axis(lim_min=0, lim_max=100, tick_step=10)
        graph.set_axis_titles(x_title='month', y_title='yield [%]')
        graph.turn_grid_on()
        graph.draw_graph()
        return graph

    def plot_profiles(self, start_date: Date = None, end_date: Date = None, fig_size=None, dpi=None):
        if not start_date or not end_date:
            start_date = Date(ANY_YEAR, 1, 1)
            end_date = Date(ANY_YEAR, 12, 31)

        # get time and power axis of every DailyYield-object from start to end date
        Yt_ax = []; YPac_ax = []
        for dyo in self.ay.get_daily_yields(start_date, end_date):
            d = dyo.date
            t_ax_ = []; Pac_ax_ = []
            for t, Pac in dyo.ac_power_coords():
                t_ax_.append(t)
                Pac_ax_.append(Pac / 1000.0)  # kW
            Yt_ax.extend([DateTime(d, t) for t in t_ax_])
            YPac_ax.extend(Pac_ax_)

        # get time and power axis of every DailyLoad-object from start to end date
        Lt_ax = []; LPac_ax = []
        for dlo in self.al.get_daily_loads(start_date, end_date):
            d = dlo.date
            t_ax_ = []; Pac_ax_ = []
            for t, Pac in dlo.power_coords():
                t_ax_.append(t)
                Pac_ax_.append(Pac)  # kW
            Lt_ax.extend([DateTime(d, t) for t in t_ax_])
            LPac_ax.extend(Pac_ax_)

        Yt_ax = [Yt.convert_to_mpl_datetime() for Yt in Yt_ax]
        Lt_ax = [Lt.convert_to_mpl_datetime() for Lt in Lt_ax]
        graph = graphing.Graph(fig_size=fig_size, dpi=dpi)
        graph.add_data_set(name='yield', x=Yt_ax, y=YPac_ax)
        graph.add_data_set(name='load', x=Lt_ax, y=LPac_ax)
        graph.setup_time_axis(
            date_min=start_date.convert_to_mpl_datetime(),
            date_max=end_date.convert_to_mpl_datetime()
        )
        graph.set_axis_titles(x_title='time', y_title='P [kW]')
        graph.add_legend()
        graph.turn_grid_on()
        graph.draw_graph()
        return graph
