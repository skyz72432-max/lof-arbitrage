from datetime import date
import pandas as pd
import pandas_market_calendars as mcal

# 上交所交易日历
_sse = mcal.get_calendar('SSE')

def is_trading_day(dt: date = None) -> bool:
    if dt is None:
        dt = date.today()

    schedule = _sse.schedule(
        start_date=dt.strftime("%Y-%m-%d"),
        end_date=dt.strftime("%Y-%m-%d")
    )
    print(schedule)
    return not schedule.empty