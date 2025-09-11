from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ValidationError
import os


class RaceRecord(BaseModel):
    number_of_trials: int
    time_to_finish: float
    split_times: List[float] = Field(default_factory=list)
    

class RaceRecords(BaseModel):
    records: Dict[int, RaceRecord]
    
    def set_record(self, race_record: RaceRecord):
        self.records[race_record.number_of_trials] = race_record

    def get_previous_record(self, number_of_trials: int) -> Optional[float]:
        if number_of_trials not in self.records:
            return None
        return self.records[number_of_trials].time_to_finish

def _get_records_base_path():
    appdata_path = os.path.expandvars("%APPDATA%")
    if not os.path.exists(os.path.join(appdata_path, "RLBot", "Dojo")):
        os.makedirs(os.path.join(appdata_path, "RLBot", "Dojo"))
    return os.path.join(appdata_path, "RLBot", "Dojo")

def _get_race_records_path():
    return os.path.join(_get_records_base_path(), "race_records.json")

def get_race_records() -> RaceRecords:
    if not os.path.exists(_get_race_records_path()):
        return RaceRecords(records={})
    with open(_get_race_records_path(), "r") as f:
        try:
            return RaceRecords.model_validate_json(f.read())
        except ValidationError:
            return RaceRecords(records={})

def store_race_records(records: RaceRecords):
    with open(_get_race_records_path(), "w") as f:
        f.write(records.model_dump_json())
