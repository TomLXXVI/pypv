import datetime

import pytz
import matplotlib.dates


ANY_YEAR = datetime.datetime.today().year


class DateTime:
    def __init__(self, date: 'Date' = None, time: 'Time' = None, **kwargs):
        if date and time:
            self._year = date.year
            self._month = date.month
            self._day = date.day
            self._hour = time.hour
            self._minute = time.minute
            self._second = time.second
        elif set(kwargs.keys()).issubset({'year', 'month', 'day', 'hour', 'minute', 'second'}):
            self._year = kwargs.get('year', ANY_YEAR)
            self._month = kwargs.get('month', 1)
            self._day = kwargs.get('day', 1)
            self._hour = kwargs.get('hour', 0)
            self._minute = kwargs.get('minute', 0)
            self._second = kwargs.get('second', 0)
        else:
            self._year = ANY_YEAR
            self._month = 1
            self._day = 1
            self._hour = 0
            self._minute = 0
            self._second = 0

        self._py_datetime = datetime.datetime(
            year=self._year,
            month=self._month,
            day=self._day,
            hour=self._hour,
            minute=self._minute,
            second=self._second
        )

    @property
    def year(self):
        return self._year

    @year.setter
    def year(self, year: int):
        self._year = year
        self._py_datetime = self._py_datetime.replace(year=year)

    @property
    def month(self):
        return self._month

    @month.setter
    def month(self, month: int):
        self._month = month
        self._py_datetime = self._py_datetime.replace(month=month)

    @property
    def day(self):
        return self._day

    @day.setter
    def day(self, day: int):
        self._day = day
        self._py_datetime = self._py_datetime.replace(day=day)

    @property
    def hour(self):
        return self._hour

    @hour.setter
    def hour(self, hour: int):
        self._hour = hour
        self._py_datetime = self._py_datetime.replace(hour=hour)

    @property
    def minute(self):
        return self._minute

    @minute.setter
    def minute(self, minute: int):
        self._minute = minute
        self._py_datetime = self._py_datetime.replace(minute=minute)

    @property
    def second(self):
        return self._second

    @second.setter
    def second(self, second: int):
        self._second = second
        self._py_datetime = self._py_datetime.replace(second=second)

    @property
    def py_datetime(self):
        return self._py_datetime

    def __str__(self):
        if self._year == ANY_YEAR:
            return self._py_datetime.strftime('%d/%m %H:%M:%S')
        else:
            return self._py_datetime.strftime('%d/%m/%Y %H:%M:%S')

    def convert_to_utc(self, timezone_str):
        # create pytz TimeZone object
        timezone = pytz.timezone(timezone_str)
        # assign naive datetime to local timezone to get local datetime
        loc_datetime = timezone.localize(self._py_datetime, is_dst=True)
        # convert local datetime to UTC datetime
        utc_datetime = loc_datetime.astimezone(pytz.utc)
        return self.__class__(
            year=utc_datetime.year,
            month=utc_datetime.month,
            day=utc_datetime.day,
            hour=utc_datetime.hour,
            minute=utc_datetime.minute,
            second=utc_datetime.second
        )

    def convert_to_lt(self, timezone_str):
        # create pytz TimeZone object
        timezone = pytz.timezone(timezone_str)
        # assign naive datetime to UTC, then convert UTC datetime to local datetime
        loc_datetime = pytz.utc.localize(self._py_datetime, is_dst=True).astimezone(timezone)
        return self.__class__(
            year=loc_datetime.year,
            month=loc_datetime.month,
            day=loc_datetime.day,
            hour=loc_datetime.hour,
            minute=loc_datetime.minute,
            second=loc_datetime.second
        )

    def convert_to_mpl_datetime(self):
        return matplotlib.dates.date2num(self._py_datetime)

    @classmethod
    def from_py_datetime(cls, py_datetime: datetime.datetime):
        return cls(
            year=py_datetime.year,
            month=py_datetime.month,
            day=py_datetime.day,
            hour=py_datetime.hour,
            minute=py_datetime.minute,
            second=py_datetime.second
        )

    @classmethod
    def from_datetime_str(cls, datetime_str, datetime_fmt_str='%d/%m/%Y %H:%M:%S'):
        py_datetime = datetime.datetime.strptime(datetime_str, datetime_fmt_str)
        return cls.from_py_datetime(py_datetime)

    @property
    def time(self):
        return Time(self._hour, self._minute, self._second)

    @property
    def date(self):
        return Date(self._year, self._month, self._day)

    def __eq__(self, other):
        if isinstance(other, DateTime):
            return self._py_datetime == other._py_datetime
        return NotImplemented


class Date(DateTime):
    def __init__(self, year, month, day):
        super().__init__(year=year, month=month, day=day)
        self._py_date = self._py_datetime.date()

    def __str__(self):
        if self._year == ANY_YEAR:
            return self._py_date.strftime('%d/%m')
        else:
            return self._py_date.strftime('%d/%m/%Y')

    @property
    def py_date(self):
        return self._py_datetime.date()

    @property
    def day_number(self):
        dt = self._py_date - datetime.date(self._py_date.year, month=1, day=1)
        return dt.days + 1

    @classmethod
    def from_py_datetime(cls, py_datetime: datetime.datetime):
        return cls(py_datetime.year, py_datetime.month, py_datetime.day)

    @classmethod
    def from_datetime_str(cls, datetime_str, datetime_fmt_str='%d/%m/%Y %H:%M:%S'):
        py_datetime = datetime.datetime.strptime(datetime_str, datetime_fmt_str)
        return cls(py_datetime.year, py_datetime.month, py_datetime.day)

    def __eq__(self, other):
        if isinstance(other, Date):
            return self._py_date == other._py_date
        return NotImplemented


class Time(DateTime):
    def __init__(self, hour, minute, second):
        super().__init__(hour=hour, minute=minute, second=second)
        self._py_time = self._py_datetime.time()

    def __str__(self):
        return self._py_time.strftime('%H:%M:%S')

    @property
    def py_time(self):
        return self._py_datetime.time()

    @property
    def as_decimal_hour(self):
        return self._hour + self._minute / 60.0 + self._second / 3600.0

    @classmethod
    def from_decimal_hour(cls, decimal_hour):
        seconds = decimal_hour * 3600
        hour = int(seconds // 3600)
        seconds = seconds % 3600
        minute = int(seconds // 60)
        second = int(seconds % 60)
        return cls(hour, minute, second)

    @classmethod
    def from_py_datetime(cls, py_datetime: datetime.datetime):
        return cls(py_datetime.hour, py_datetime.minute, py_datetime.second)

    @classmethod
    def from_datetime_str(cls, datetime_str, datetime_fmt_str='%d/%m/%Y %H:%M:%S'):
        py_datetime = datetime.datetime.strptime(datetime_str, datetime_fmt_str)
        return cls(py_datetime.hour, py_datetime.minute, py_datetime.second)

    def __eq__(self, other):
        if isinstance(other, Time):
            return self._py_time == other._py_time
        return NotImplemented


class TimeDelta:
    def __init__(self, start_time: DateTime, end_time: DateTime):
        self.py_timedelta = start_time.py_datetime - end_time.py_datetime
        self.seconds = self.py_timedelta.seconds
        self.minutes = self.seconds / 60.0
        self.hours = self.seconds / 3600.0

        hours = int(self.seconds // 3600)
        seconds = self.seconds % 3600
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        self.tuple = (hours, minutes, seconds)
