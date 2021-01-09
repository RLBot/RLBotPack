import csv
from bisect import bisect_left
from pathlib import Path
from typing import List


class LookupTable:

    def __init__(self, file_name: str):
        self.file_name = file_name

    def get_reader(self) -> csv.DictReader:
        data_folder = Path(__file__).absolute().parent
        file = open(data_folder / self.file_name)
        return csv.DictReader(file)

    def get_column(self, name: str) -> List[float]:
        """
        Get all data in a column
        :param name: Name of the column
        :return: List of float values in the column
        """
        return [float(row[name]) for row in self.get_reader()]

    @staticmethod
    def find_index(column: List[float], value: float) -> int:
        return bisect_left(column, value, hi=len(column) - 1)
