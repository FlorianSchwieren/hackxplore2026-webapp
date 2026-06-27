from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Column, DateTime, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Profile(SQLModel, table=True):
    __tablename__ = "profiles"

    id: UUID = Field(primary_key=True)
    display_name: str
    email: str | None = None
    avatar_url: str | None = None
    score: int = 0
    notify_help_opt_in: bool = False
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )


class SpeciesWaterProfile(SQLModel, table=True):
    __tablename__ = "species_water_profiles"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    match_kind: str
    match_value: str = Field(unique=True)
    optimal_min_pct: Decimal = Field(sa_column=Column(Numeric, nullable=False))
    optimal_max_pct: Decimal = Field(sa_column=Column(Numeric, nullable=False))
    dry_critical_pct: Decimal = Field(sa_column=Column(Numeric, nullable=False))
    wet_critical_pct: Decimal = Field(sa_column=Column(Numeric, nullable=False))
    drought_tolerance: str = "medium"
    priority: int = 0
    notes: str | None = None


class Tree(SQLModel, table=True):
    __tablename__ = "trees"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    external_id: int = Field(sa_column=Column(BigInteger, unique=True, nullable=False))
    lfdbnr: int | None = None
    artdeut: str | None = None
    artlat: str | None = None
    baumart_allgemein: str
    baumgruppe: str | None = None
    stadtteil: str
    geom: Any = Field(sa_column=Column(Geometry("POINT", srid=4326), nullable=False))
    name: str | None = None
    status: str = "available"
    species_profile_id: UUID | None = Field(default=None, foreign_key="species_water_profiles.id")
    moisture_pct: Decimal | None = Field(default=None, sa_column=Column(Numeric(5, 2)))
    health_score: int | None = None
    health_state: str | None = None
    last_reading_at: datetime | None = None
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )


class Sensor(SQLModel, table=True):
    __tablename__ = "sensors"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    device_eui: str = Field(unique=True)
    device_ref: str = Field(unique=True)
    tree_id: UUID = Field(foreign_key="trees.id", unique=True)
    status: str = "working"
    is_real: bool = False
    calibration_dry: int
    calibration_wet: int
    installed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
    last_seen_at: datetime | None = None
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )


class SensorReading(SQLModel, table=True):
    __tablename__ = "sensor_readings"

    id: int | None = Field(default=None, primary_key=True)
    sensor_id: UUID = Field(foreign_key="sensors.id")
    tree_id: UUID = Field(foreign_key="trees.id")
    raw: int
    moisture_pct: Decimal = Field(sa_column=Column(Numeric(5, 2), nullable=False))
    is_outlier: bool = False
    measured_at: datetime
    received_at: datetime | None = None
    fcnt: int | None = None
    rssi: int | None = None
    snr: Decimal | None = Field(default=None, sa_column=Column(Numeric))
    battery_mv: int | None = None
    device_status: str | None = None
    device_moisture_pct: Decimal | None = Field(default=None, sa_column=Column(Numeric))
    priority: Decimal | None = Field(default=None, sa_column=Column(Numeric))
    source: str = "lorawan"


class TreePartnership(SQLModel, table=True):
    __tablename__ = "tree_partnerships"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tree_id: UUID = Field(foreign_key="trees.id")
    user_id: UUID = Field(foreign_key="profiles.id")
    role: str
    active_from: date = Field(default_factory=date.today)
    active_to: date | None = None
    streak: int = 0
    streak_frozen: bool = False
    last_eval_date: date | None = None
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )


class Absence(SQLModel, table=True):
    __tablename__ = "absences"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="profiles.id")
    tree_id: UUID = Field(foreign_key="trees.id")
    partnership_id: UUID = Field(foreign_key="tree_partnerships.id")
    from_date: date
    to_date: date
    status: str = "open"
    covering_partnership_id: UUID | None = Field(default=None, foreign_key="tree_partnerships.id")
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )


class WeatherSnapshot(SQLModel, table=True):
    __tablename__ = "weather_snapshots"

    id: int | None = Field(default=None, primary_key=True)
    captured_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
    lat: Decimal = Field(sa_column=Column(Numeric, nullable=False))
    lon: Decimal = Field(sa_column=Column(Numeric, nullable=False))
    temp_c: Decimal | None = Field(default=None, sa_column=Column(Numeric))
    precip_mm: Decimal | None = Field(default=None, sa_column=Column(Numeric))
    humidity_pct: Decimal | None = Field(default=None, sa_column=Column(Numeric))
    forecast_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="profiles.id")
    kind: str
    title: str
    body: str
    tree_id: UUID | None = Field(default=None, foreign_key="trees.id")
    payload: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    read: bool = False
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
