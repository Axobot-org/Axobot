import re
import time
from datetime import UTC, datetime, timedelta
from typing import Literal

from babel import dates, numbers
from dateutil.relativedelta import relativedelta


def get_locale(lang: str):
    "Get a i18n locale from a given bot language"
    if lang in {"en", "lolcat"}:
        return "en_US"
    if lang == "fr2":
        return "fr_FR"
    return lang+"_"+lang.capitalize()

# pylint: disable=too-few-public-methods, invalid-name
class TIMEDELTA_UNITS:
    "used to get number of seconds in each time unit"
    year = 86400 * 365
    month = 86400 * (365/12)
    week = 86400 * 7
    day = 86400
    hour = 3600
    minute = 60
    second = 1


class FormatUtils:
    """This class handles all language-specific formatting of date, time, time interval, numbers and other"""


    @staticmethod
    async def time_delta(date1: datetime | int, date2: datetime = None,
                         lang: str = "en", year: bool = False, hour: bool = True, seconds: bool = True,
                         form: Literal["short", "developed"]="developed"):
        """Translates a two time interval datetime into a readable character string

        form can be 'short' (3d 6h) or 'developed' (3 jours 6 heures)
        """
        if date2 is None:
            delta = relativedelta(seconds=date1)
        else:
            delta = relativedelta(date2, date1)

        kwargs = {
            "threshold": 100000,
            "locale": get_locale(lang),
            "format": "narrow" if form=="short" else "long"
        }

        result = ""
        if year and delta.years > 0 :
            # add formatted years
            result += dates.format_timedelta(timedelta(days=365*delta.years), granularity="year", **kwargs) + " "
            # we remove years
            delta -= relativedelta(years=delta.years)
        if year and delta.months > 0 :
            # add formatted months
            result += dates.format_timedelta(timedelta(days=31*delta.months), granularity="month", **kwargs) + " "
            # we remove years
            delta -= relativedelta(months=delta.months)
        if delta.days > 0:
            # add formatted days
            result += dates.format_timedelta(timedelta(days=delta.days), granularity="day", **kwargs) + " "
            # we remove years
            delta -= relativedelta(days=delta.days)

        if hour:
            if delta.hours > 0:
                # add formatted hours
                result += dates.format_timedelta(timedelta(hours=delta.hours), granularity="hour", **kwargs) + " "
                # we remove hours
                delta -= relativedelta(hours=delta.hours)
            if delta.minutes > 0:
                # add formatted minutes
                result += dates.format_timedelta(timedelta(minutes=delta.minutes), granularity="minute", **kwargs) + " "
                # we remove minutes
                delta -= relativedelta(minutes=delta.minutes)
            if seconds and delta.seconds > 0:
                # add formatted seconds
                result += dates.format_timedelta(timedelta(seconds=delta.seconds), granularity="second", **kwargs) + " "
            elif not seconds and len(result.strip()) == 0 and delta.seconds > 0:
                result += "<" + dates.format_timedelta(timedelta(minutes=1), granularity="minute", **kwargs)

        return result.strip()

    @staticmethod
    async def date(date: datetime | time.struct_time, lang: str = "en",
                   year: bool = False, weekday: bool = False, hour: bool = True, seconds: bool = True, digital: bool = False
                   ) -> str:
        """Translates a datetime object into a readable string"""
        if isinstance(date, time.struct_time):
            date = datetime(*date[:6])
        locale = get_locale(lang)

        if digital:
            if hour and year: # 1/14/2022 6:10:23 PM
                result = dates.format_skeleton("yMd", date, locale=locale) + " " + dates.format_time(date, locale=locale)
            elif hour and not year: # 1/14 6:10:23 PM
                result = dates.format_skeleton("Md", date, locale=locale) + " " + dates.format_time(date, locale=locale)
            elif not hour and year: # 1/14/22
                result = dates.format_skeleton("yMd", date, locale=locale)
            else: # 1/14
                result = dates.format_skeleton("Md", date, locale=locale)
        else:
            def get_day():
                if year and weekday:
                    return dates.format_skeleton("yMMMdEEEE, MMMMd", date, locale=locale)
                if year and not weekday:
                    return dates.format_skeleton("yMMMMd", date, locale=locale)
                if weekday and not year:
                    return dates.format_skeleton("MMMMdE, MMMMd", date, locale=locale)
                # else: no year and no weekday
                return dates.format_skeleton("MMMMd", date, locale=locale)
            def get_hour():
                if seconds:
                    return dates.format_time(date, locale=locale)
                return dates.format_skeleton("Hm", date, locale=locale)

            if hour: # January 14, 2022, 6:10:23 PM
                result = get_day() + ", " + get_hour()
            else: # January 14
                result = get_day()

        return result

    @staticmethod
    async def format_nbr(number: int | float, lang: str) -> str:
        "Format any number in the given language"
        locale = get_locale(lang)
        return numbers.format_decimal(number, locale=locale)

    @staticmethod
    async def parse_duration(duration: str) -> int:
        """Parses a string duration into a number of seconds"""
        duration = duration.lower().strip()
        try:
            return await _Duration.convert(duration)
        except ValueError:
            return sum([
                await _Duration.convert(word)
                for word in duration.split()
            ])


class _Duration(float):
    "Argument converter for durations input"

    @classmethod
    async def convert(cls, argument: str) -> int:
        "Converts a string to a duration in seconds."
        duration: int = 0
        found = False
        for symbol, coef in [('w', 604800), ('d', 86400), ('h', 3600), ('m', 60), ('min', 60)]:
            r = re.search(r"^(\d+)"+symbol+'$', argument)
            if r is not None:
                duration += int(r.group(1))*coef
                found = True
        r = re.search(r"^(\d+)h(\d+)m?$", argument)
        if r is not None:
            duration += int(r.group(1))*3600 + int(r.group(2))*60
            found = True
        r = re.search(r"^(\d+) ?mo(?:nths?)?$", argument)
        if r is not None:
            now = then = datetime.now(UTC)
            then += relativedelta(months=int(r.group(1)))
            duration += (then - now).total_seconds()
            found = True
        r = re.search(r"^(\d+) ?y(?:ears?)?$", argument)
        if r is not None:
            now = then = datetime.now(UTC)
            then += relativedelta(years=int(r.group(1)))
            duration += (then - now).total_seconds()
            found = True
        if not found:
            raise ValueError("Invalid duration")
        return duration
