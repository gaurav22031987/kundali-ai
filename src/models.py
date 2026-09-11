"""Typed data structures for validated birth details and calculated charts."""

from dataclasses import dataclass
from datetime import date, datetime, time


@dataclass(frozen=True)
class BirthDetails:
    name: str
    date_of_birth: date
    time_of_birth: time
    gender: str
    place_of_birth: str


@dataclass(frozen=True)
class Location:
    display_name: str
    latitude: float
    longitude: float
    timezone_name: str


@dataclass(frozen=True)
class PlanetPosition:
    name: str
    longitude: float
    sign: str
    degree_in_sign: float
    house: int
    nakshatra: str
    pada: int


@dataclass(frozen=True)
class House:
    number: int
    sign: str
    cusp_longitude: float


@dataclass(frozen=True)
class DashaPeriod:
    lord: str
    start: datetime
    end: datetime
    antardashas: tuple["DashaPeriod", ...] = ()


@dataclass(frozen=True)
class DivisionalPosition:
    """A planet's deterministic placement in a divisional chart."""

    name: str
    d1_sign: str
    d1_degree: float
    d9_sign: str
    d9_house: int
    vargottama: bool

    @property
    def sign(self) -> str:
        """Generic divisional-chart sign alias (D9 or D10)."""
        return self.d9_sign

    @property
    def house(self) -> int:
        """Generic divisional-chart house alias (D9 or D10)."""
        return self.d9_house


@dataclass(frozen=True)
class NavamsaChart:
    lagna_sign: str
    houses: tuple[House, ...]
    positions: tuple[DivisionalPosition, ...]


@dataclass(frozen=True)
class DashamsaChart:
    lagna_sign: str
    houses: tuple[House, ...]
    positions: tuple[DivisionalPosition, ...]


@dataclass(frozen=True)
class KundaliChart:
    birth_utc: datetime
    location: Location
    ascendant_longitude: float
    ascendant_sign: str
    moon_sign: str
    sun_sign: str
    planets: tuple[PlanetPosition, ...]
    houses: tuple[House, ...]
    mahadashas: tuple[DashaPeriod, ...]
    current_mahadasha: DashaPeriod
    current_antardasha: DashaPeriod
    navamsa: NavamsaChart | None = None
    dashamsa: DashamsaChart | None = None
