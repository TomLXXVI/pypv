import math


class Angle:
    def __init__(self, value, unit='deg'):
        if unit == 'deg':
            self._value = math.radians(value)
        elif unit == 'rad':
            self._value = value
        else:
            raise ValueError(f'{unit} is not recognized')

    def __call__(self, unit='rad'):
        if unit == 'deg':
            return math.degrees(self._value)
        elif unit == 'rad':
            return self._value
        else:
            raise ValueError(f'{unit} is not recognized')
