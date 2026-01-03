from datetime import date, datetime
from zoneinfo import ZoneInfo
import pandas as pd
import pandas_market_calendars as mcal

# 上交所交易日历
_sse = mcal.get_calendar('SSE')

def today_cn() -> date:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()

def is_trading_day(dt: date = None) -> bool:
    if dt is None:
        dt = today_cn()

    schedule = _sse.schedule(
        start_date=dt.strftime("%Y-%m-%d"),
        end_date=dt.strftime("%Y-%m-%d")
    )
    return not schedule.empty
