from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.schemas import WeatherForecastResponse
from app.services.weather import fetch_forecast

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/forecast", response_model=WeatherForecastResponse)
def weather_forecast(session: Session = Depends(get_session)) -> dict:
    return fetch_forecast(session)
