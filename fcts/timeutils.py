from datetime import timedelta, datetime
import time
from typing import Union

import discord
from babel import dates
from libs.classes import Zbot


def get_locale(lang: str):
    "Get a i18n locale from a given bot language"
    if lang in {"en", "lolcat"}:
        return 'en_US'
    if lang == "fr2":
        return 'fr_FR'
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


class TimeUtils(discord.ext.commands.Cog):
    """This cog handles all manipulations of date, time, and time interval. So cool, and so fast"""

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "timeutils"

    async def time_delta(self, date1: Union[datetime, int], date2: datetime = None,
                         lang: str = 'en', year: bool = False, hour: bool = True, form='developed'):
        """Translates a two time interval datetime into a readable character string

        form can be 'short' (3d 6h) or 'developed' (3 jours 6 heures)
        """
        if date2 is None:
            delta = timedelta(seconds=date1)
        else:
            delta: timedelta = abs(date2 - date1)
        delta: float = delta.total_seconds()

        kwargs = {
            "threshold": 100000,
            "locale": get_locale(lang),
            "format": 'narrow' if form=='short' else 'long'
        }

        result = ""
        if year and delta >= TIMEDELTA_UNITS.year:
            # we calculate trunked value in seconds (to avoid babel rounding it)
            seconds_year = delta // TIMEDELTA_UNITS.year * TIMEDELTA_UNITS.year
            # then format
            result += dates.format_timedelta(timedelta(seconds=seconds_year), granularity="year", **kwargs) + " "
            # we remove years
            delta %= TIMEDELTA_UNITS.year
        if year and delta >= TIMEDELTA_UNITS.month:
            # we calculate trunked value in seconds (to avoid babel rounding it)
            seconds_months = delta // TIMEDELTA_UNITS.month * TIMEDELTA_UNITS.month
            # then format
            result += dates.format_timedelta(timedelta(seconds=seconds_months), granularity="month", **kwargs) + " "
        if delta >= TIMEDELTA_UNITS.day:
            if year:
                # we remove months
                delta %= TIMEDELTA_UNITS.month
            # we calculate trunked value in seconds (to avoid babel rounding it)
            seconds_days = delta // TIMEDELTA_UNITS.day * TIMEDELTA_UNITS.day
            # then format
            result += dates.format_timedelta(timedelta(seconds=seconds_days), granularity="day", **kwargs) + " "
            # we remove days
            delta %= TIMEDELTA_UNITS.day

        if hour and delta > 0:
            if delta >= TIMEDELTA_UNITS.hour:
                # we calculate trunked value in seconds (to avoid babel rounding it)
                seconds_hours = delta // TIMEDELTA_UNITS.hour * TIMEDELTA_UNITS.hour
                # then format
                result += dates.format_timedelta(timedelta(seconds=seconds_hours), granularity="hour", **kwargs) + " "
                # we remove hours
                delta %= TIMEDELTA_UNITS.hour
            if delta > TIMEDELTA_UNITS.minute:
                # we calculate trunked value in seconds (to avoid babel rounding it)
                seconds_minutes = delta // TIMEDELTA_UNITS.minute * TIMEDELTA_UNITS.minute
                # then format
                result += dates.format_timedelta(timedelta(seconds=seconds_minutes), granularity="minute", **kwargs) + " "
                # we remove minutes
                delta %= TIMEDELTA_UNITS.minute
            # then format
            result += dates.format_timedelta(timedelta(seconds=delta), granularity="second", **kwargs)

        return result.strip()


    async def date(self, date: Union[datetime, time.struct_time], lang: str = 'fr',
                   year: bool = False, hour: bool = True, digital: bool = False) -> str:
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
            if hour and year: # Jan 14, 2022, 6:10:23 PM
                result = dates.format_datetime(date, locale=locale)
            elif hour and not year: # January 14, 6:10:23 PM
                result = dates.format_skeleton("MMMMd", date, locale=locale) + ", " + dates.format_time(date, locale=locale)
            elif not hour and year: # Jan 14, 2022
                result = dates.format_date(date, locale=locale)
            else: # January 14
                result = dates.format_skeleton("MMMMd", date, locale=locale)

        return result


def setup(bot):
    bot.add_cog(TimeUtils(bot))
