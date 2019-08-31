import csv
import math

from quantities.date_time import DateTime, ANY_YEAR


class _CSVDataFetcher:
    """Base class for reading and preparing data from .csv-files."""
    def __init__(self, file_path, datetime_fmt='%d/%m/%Y %H:%M:%S', tz_str='UTC'):
        self.datetime_fmt = datetime_fmt
        self.tz_str = tz_str
        self._read_table(file_path)
        self._remove_header()
        self._format_table()
        self._split_table()
        self._transform_datasets()

    def _read_table(self, file_path):
        self.table = []
        with open(file_path, newline='') as csv_file:
            reader = csv.reader(csv_file, quotechar='"')
            for row in reader:
                self.table.append(row)

    def _remove_header(self):
        # remove first row from the table (= table header)
        self.table.pop(0)

    def _format_table(self):
        for row in self.table:
            # replace date-time string with DateTime object and change year to DateTime.ANY_YEAR
            row[0] = DateTime.from_datetime_str(row[0], self.datetime_fmt)
            row[0].year = ANY_YEAR
            # convert to local time if needed
            if self.tz_str != 'UTC':
                row[0] = row[0].convert_to_lt(self.tz_str)
            # convert the values in the next cells to float
            for col_index in range(1, len(row)):
                try:
                    row[col_index] = float(row[col_index])
                except ValueError:
                    row[col_index] = math.nan

    def _split_table(self):
        # rows with the same date are put into separate datasets; so each dataset covers one day
        self.daily_dataset_list = []
        search_date = self.table[0][0].date
        dataset = []
        for row in self.table:
            if row[0].date == search_date:
                dataset.append(row)
            else:
                self.daily_dataset_list.append(dataset)
                dataset = []
                search_date = row[0].date
                dataset.append(row)
        self.daily_dataset_list.append(dataset)

    @staticmethod
    def _transform_dataset(data_set):
        pass

    def _transform_datasets(self):
        self.daily_dataset_list = [self._transform_dataset(data_set) for data_set in self.daily_dataset_list]

    def get_daily_datasets(self):
        return self.daily_dataset_list


class TMYDataFetcher(_CSVDataFetcher):
    """Class for reading and preparing the meteo data."""
    @staticmethod
    def _transform_dataset(dataset):
        row = dataset[0]
        time_list = []
        temperature_list = []
        irradiance_list = []
        for row in dataset:
            time_list.append(row[0].time)
            temperature_list.append(row[1])
            irradiance_list.append(row[2])
        return {
            'date': row[0].date,
            'time': time_list,
            'temperature': temperature_list,
            'irradiance': irradiance_list
        }


class CLPDataFetcher(_CSVDataFetcher):
    """Class for reading and preparing the consumer load profile data."""
    @staticmethod
    def _transform_dataset(dataset):
        row = dataset[0]
        time_list = []
        CLP_list = []
        for row in dataset:
            time_list.append(row[0].time)
            CLP_list.append(row[1])
        return {
            'date': row[0].date,
            'time': time_list,
            'CLP': CLP_list,
        }
