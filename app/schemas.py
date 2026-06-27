from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ErrorEnvelope(BaseModel):
    error: dict[str, str]


class Coordinates(BaseModel):
    lat: float
    lng: float


class HealthzResponse(BaseModel):
    status: str
    time: datetime


class HttpIngestRequest(BaseModel):
    tree_id: str
    raw_value: int
    fcnt: int | None = None
    moisture_percent: Decimal | None = None
    status: str | None = None
    priority: Decimal | None = None
    battery_voltage: Decimal | None = None
    battery_mv: int | None = None
    rssi: int | None = None
    created_at: datetime | None = None


class LorawanDeviceInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    devEui: str
    deviceName: str | None = None


class LorawanRxInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    rssi: int | None = None
    snr: Decimal | None = None
    gatewayId: str | None = None


class LorawanDeviceFields(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str | None = None
    moisture_percent: Decimal | None = None
    priority: Decimal | None = None


class LorawanIngestRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    deviceInfo: LorawanDeviceInfo
    fPort: int = 10
    fCnt: int | None = None
    data: str
    rxInfo: list[LorawanRxInfo] = Field(default_factory=list)
    time: datetime | None = None
    deviceFields: LorawanDeviceFields | None = None


class IngestResponse(BaseModel):
    accepted: bool
    reading_id: int | None
    moisture_pct: float
    health_state: str | None
    streak_awarded: bool
    is_outlier: bool = False


class TreeSummary(BaseModel):
    id: UUID
    external_id: int
    name: str | None
    title: str
    artdeut: str | None
    artlat: str | None
    baumart_allgemein: str
    species_app: str
    stadtteil: str
    lon: float
    lat: float
    coordinates: Coordinates
    status: str
    monitored: bool
    moisture_pct: float | None
    health_score: int | None
    health_state: str | None
    health_state_app: str | None
    last_reading_at: datetime | None
    owner_ids: list[UUID] = Field(default_factory=list)


class TreeListResponse(BaseModel):
    count: int
    trees: list[TreeSummary]


class SpeciesProfileOut(BaseModel):
    optimal_min_pct: float
    optimal_max_pct: float
    dry_critical_pct: float
    wet_critical_pct: float


class SensorOut(BaseModel):
    id: UUID | None = None
    device_eui: str
    status: str
    is_real: bool
    last_seen_at: datetime | None


class PartnerOut(BaseModel):
    user_id: UUID
    display_name: str
    role: str
    streak: int


class ReadingOut(BaseModel):
    id: int | None = None
    sensor_id: UUID | None = None
    measured_at: datetime
    moisture_pct: float
    raw: int | None = None
    is_outlier: bool = False


class TreeDetail(TreeSummary):
    species_profile: SpeciesProfileOut | None
    sensor: SensorOut | None
    partners: list[PartnerOut]
    recent_readings: list[ReadingOut]


class ReadingsResponse(BaseModel):
    tree_id: UUID
    readings: list[ReadingOut]


class AdoptRequest(BaseModel):
    tree_id: UUID


class PartnershipOut(BaseModel):
    id: UUID
    tree_id: UUID
    user_id: UUID
    role: str
    streak: int
    active_from: date | None = None
    active_to: date | None = None


class PartnershipResponse(BaseModel):
    partnership: PartnershipOut


class InviteRequest(BaseModel):
    email: str


class MyTreeOut(BaseModel):
    tree_id: UUID
    name: str
    role: str
    streak: int
    lon: float
    lat: float
    health_state: str | None
    moisture_pct: float | None


class MyTreesResponse(BaseModel):
    score: int
    longest_streak: int
    trees: list[MyTreeOut]


class CoPartnerSharedTreeOut(BaseModel):
    tree_id: UUID
    name: str
    your_role: str
    their_role: str
    moisture_pct: float | None = None
    health_state: str | None = None
    health_state_app: str | None = None


class CoPartnerAllTreeOut(BaseModel):
    tree_id: UUID
    name: str
    their_role: str
    shared: bool
    your_role: str | None = None
    moisture_pct: float | None = None
    health_state: str | None = None
    health_state_app: str | None = None


class CoPartnerOut(BaseModel):
    user_id: UUID
    display_name: str
    avatar_url: str | None = None
    shared_trees: int
    trees: list[CoPartnerSharedTreeOut]
    all_trees: list[CoPartnerAllTreeOut] | None = None


class CoPartnersResponse(BaseModel):
    count: int
    co_partners: list[CoPartnerOut]


class ProfileOut(BaseModel):
    id: UUID
    display_name: str
    name: str
    email: str | None = None
    avatar_url: str | None = None
    score: int
    notify_help_opt_in: bool
    total_trees_count: int


class ProfilePatch(BaseModel):
    display_name: str | None = None
    notify_help_opt_in: bool | None = None
    avatar_url: str | None = None


class TreeNamePatch(BaseModel):
    name: str


class AbsenceCreate(BaseModel):
    tree_id: UUID
    from_date: date
    to_date: date


class AbsenceOut(BaseModel):
    id: UUID
    status: str
    from_date: date
    to_date: date


class AbsenceResponse(BaseModel):
    absence: AbsenceOut


class CoverageItem(BaseModel):
    absence_id: UUID
    tree_id: UUID
    name: str
    lon: float
    lat: float
    from_date: date
    to_date: date
    stadtteil: str
    health_state: str | None


class CoverageOpenResponse(BaseModel):
    items: list[CoverageItem]


class CoverageCreate(BaseModel):
    absence_id: UUID


class StatsOverview(BaseModel):
    trees_total: int
    trees_monitored: int
    users_total: int
    partnerships_active: int
    health_distribution: dict[str, int]
    sensors: dict[str, int]
    city_health_score: int
    absences_active: int


class StadtteilStats(BaseModel):
    stadtteil: str
    trees: int
    monitored: int
    avg_health_score: float | None
    needs_water: int


class SensorMaintenanceOut(BaseModel):
    id: UUID
    device_eui: str
    tree_id: UUID
    status: str
    last_seen_at: datetime | None
    stadtteil: str
    lon: float
    lat: float


class NotificationOut(BaseModel):
    id: UUID
    title: str
    body: str
    received_at: datetime
    is_read: bool


class NotificationPatch(BaseModel):
    is_read: bool


class WeatherForecastResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    current: dict
    daily: list[dict]


class PredictionItem(BaseModel):
    tree_id: UUID
    stadtteil: str
    risk_score: float
    predicted_shortage_date: date
    drivers: list[str]


class StadtteilTrend(BaseModel):
    stadtteil: str
    avg_humidity_now: float | None
    avg_humidity_in_7d: float | None


class PredictionsResponse(BaseModel):
    generated_at: datetime
    horizon_days: int
    model: str
    items: list[PredictionItem]
    stadtteil_trend: list[StadtteilTrend]
