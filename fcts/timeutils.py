import discord
import datetime
import time
from utils import Zbot

fr_months = ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Aout","Septembre","Octobre","Novembre","Décembre"]
en_months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
fi_months = ['tammikuu','helmikuu','maaliskuu','huhtikuu','toukokuu','kesäkuu','heinäkuu','elokuu','syyskuu','lokakuu','marraskuu','joulukuu']

class TimeUtils(discord.ext.commands.Cog):
    """This cog handles all manipulations of date, time, and time interval. So cool, and so fast"""
    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "timeutils"

    class timedelta:
        """Representation of a duration between two dates, with the value noted as years/months/days/etc."""

        def __init__(self, years=0, months=0, days=0, hours=0, minutes=0, seconds=0, total_seconds=0, precision=2):
            """Initialize the class with the needed values"""
            self.years = years
            self.months = months
            self.days = days
            self.hours = hours
            self.minutes = minutes
            self.seconds = seconds
            self.total_seconds = total_seconds
            self.precision = precision
            
        def set_from_seconds(self):
            """Set the values from a raw total seconds"""
            t = self.total_seconds
            rest = 0
            years, rest = divmod(t,86400*365)
            months, rest = divmod(rest,86400*365/12)
            days, rest = divmod(rest,86400)
            hours, rest = divmod(rest,3600)
            minutes, rest = divmod(rest,60)
            seconds = rest
            self.years = int(years)
            self.months = int(months)
            self.days = int(days)
            self.hours = int(hours)
            self.minutes = int(minutes)
            if self.precision == 0:
                self.seconds = int(seconds)
            else:
                self.seconds = round(seconds,self.precision)

    async def time_delta(self, date1, date2=None, lang='en', year=False, hour=True, form='developed', precision=2):
        """Translates a two time interval datetime.datetime into a readable character string"""
        if date2 is not None:
            if type(date2)==datetime.datetime:
                delta = abs(date2 - date1)
                t = await self.time_interval(delta,precision)
            else:
                raise ValueError
        else:
            t = self.timedelta(total_seconds=date1,precision=precision)
            t.set_from_seconds()
        if form=='digital':
            if hour:
                h = "{}:{}:{}".format(t.hours,t.minutes,t.seconds)
            else:
                h = ''
            if lang=='fr':
                text = '{}/{}{} {}'.format(t.days,t.months,"/"+str(t.years) if year else '',h)
            else:
                text = '{}/{}{} {}'.format(t.months,t.days,"/"+str(t.years) if year else '',h)
        elif form=='temp':
            text = str()
            if t.days + t.months*365/12 + t.years*365 > 0:
                d = round(t.days+t.months*365/12)
                if not year:
                    d += round(t.years*365)
                elif year and t.years > 0:
                    text += str(t.years)+'a ' if lang=='fr' else str(t.years)+'y '
                text += str(d)+'j ' if lang=='fr' else str(d)+'d '
            if hour:
                if t.hours > 0:
                    text += str(t.hours)+'h '
                if t.minutes > 0:
                    text += str(t.minutes)+'m '
                if t.seconds > 0:
                    text += str(t.seconds)+'s '
            text = text.strip()
        else:
            text = str()
            if lang == 'fr':
                lib = ['ans','an','mois','mois','jours','jour','heures','heure','minutes','minute','secondes','seconde',"il y a moins d'un jour"]
            elif lang == 'lolcat':
                lib = ['yearz','year','mons','month','dayz','day','hourz','hour','minutz','minut','secondz','secnd','less zan 1d ago']
            elif lang=='fi':
                lib = [ 'Vuotta', 'vuosi', 'kuukautta', 'kuukausi', 'päivää', 'päivä', 'tuntia', 'h', 'minuuttia', 'minute', 'sekuntia', 'toinen', 'Alle päivä sitten']
            else:
                lib = ['years','year','months','month','days','day','hours','hour','minutes','minute','seconds','second', 'less than one day ago']
            if year and t.years != 0:
                if t.years > 1:
                    text += str(t.years)+" "+lib[0]
                else:
                    text += str(t.years)+" "+lib[1]
                text+=" "
            if t.months > 1:
                text += str(t.months)+" "+lib[2]
            elif t.months==1:
                text += str(t.months)+" "+lib[3]
            text+=" "
            if t.days > 1:
                text += str(t.days)+" "+lib[4]
            elif t.days==1:
                text += str(t.days)+" "+lib[5]
            if hour:
                if t.hours > 1:
                    text += " "+str(t.hours)+" "+lib[6]
                elif t.hours==1:
                    text += " "+str(t.hours)+" "+lib[7]
                text+=" "
                if t.minutes > 1:
                    text += str(t.minutes)+" "+lib[8]
                elif t.minutes==1:
                    text += str(t.minutes)+" "+lib[9]
                text+=" "
                if t.seconds > 1:
                    text += str(t.seconds)+" "+lib[10]
                elif t.seconds==1:
                    text += str(t.seconds)+" "+lib[11]
            elif len(text.strip()) == 0:
                text = lib[12]
        return text.strip()


    async def time_interval(self, tmd, precision=2):
        """Creates a timedelta object from a datetime.timedelta object"""
        t = tmd.total_seconds()
        obj = self.timedelta(total_seconds=t,precision=precision)
        obj.set_from_seconds()
        return obj

    async def date(self, date, lang='fr', year=False, hour=True, digital=False, timezone=False) -> str:
        """Translates a datetime.datetime object into a readable string"""
        if type(date) == time.struct_time:
            date = datetime.datetime(*date[:6])
        if type(date) == datetime.datetime:
            if len(str(date.day)) == 1:
                jour="0"+str(date.day)
            else:
                jour = str(date.day)
            h=[]
            if lang == 'fr':
                month = fr_months
            elif lang == 'fi':
                month = fi_months
            else:
                month = en_months
            for i in ['hour','minute','second']:
                a = eval(str("date."+i))
                if len(str(a))==1:
                    h.append("0"+str(a))
                else:
                    h.append(str(a))
            if digital:
                if date.month < 10:
                    month = "0"+str(date.month)
                else:
                    month = str(date.month)
                separator = "/"
                if lang == 'fr':
                    df = "{d}/{m}{y}  {h}"
                elif lang == 'fi':
                    df = "{d}.{m}{y}  {h}"
                    separator = "."
                else:
                    df = "{m}/{d}{y}  {h}"
                df = df.format(d=jour,m=month,y = separator+str(date.year) if year else "",h = ":".join(h) if hour else "")
            else:
                if lang == 'fr' or lang=='fi':
                    df = "{d} {m} {y}  {h}"
                else:
                    df = "{m} {d}, {y}  {h}"
                df = df.format(d=jour,m=month[date.month-1],y=str(date.year) if year else "",h=":".join(h) if hour else "")
            df = df.strip()
            # if timezone asked and the date has a timezone
            if timezone and (date.tzinfo is not None and date.tzinfo.utcoffset(date) is not None):
                df += " " + date.tzinfo.tzname(None)
            return df.strip().replace('  ', ' ')


def setup(bot):
    bot.add_cog(TimeUtils(bot))

