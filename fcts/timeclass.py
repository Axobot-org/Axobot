import discord, datetime, time


fr_months=["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Aout","Septembre","Octobre","Novembre","Décembre"]
en_months=["January","February","March","April","May","June","July","August","September","October","November","December"]

class TimeCog:
    """This cog handles all manipulations of date, time, and time interval. So cool, and so fast"""
    def __init__(self,bot):
        self.bot = bot
        self.file = "timeclass"

    class timedelta:

        def __init__(self,years=0,months=0,days=0,hours=0,minutes=0,seconds=0,total_seconds=0,precision=2):
            self.years = years
            self.months = months
            self.days = days
            self.hours = hours
            self.minutes = minutes
            self.seconds = seconds
            self.total_seconds = total_seconds
            self.precision = precision
            
        def set_from_seconds(self):
            t = self.total_seconds
            rest = 0
            years, rest = divmod(t,3.154e+7)
            months, rest = divmod(rest,2.628e+6)
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

    async def time_delta(self,date1,date2,lang='fr',year=False,hour=True,digital=False,precision=2):
        """Traduit un intervale de deux temps datetime.datetime en chaine de caractère lisible"""
        delta = abs(date2 - date1)
        t = await self.time_interval(delta,precision)
        if digital:
            if hour:
                h = "{}:{}:{}".format(t.hours,t.minutes,t.seconds)
            else:
                h = ''
            if lang=='fr':
                text = '{}/{}{} {}'.format(t.days,t.months,"/"+str(t.years) if year else '',h)
            else:
                text = '{}/{}{} {}'.format(t.months,t.days,"/"+str(t.years) if year else '',h)
        else:
            text = str()
            if lang == 'fr':
                lib = ['ans','an','mois','mois','jours','jour','heures','heure','minutes','minute','secondes','seconde']
            elif lang == 'lolcat':
                lib = ['yearz','year','mons','month','dayz','day','hourz','hour','minutz','minut','secondz','secnd']
            else:
                lib = ['years','year','months','month','days','day','hours','hour','minutes','minute','seconds','second']
            if year and t.years != 0:
                if t.years>1:
                    text += str(t.years)+" "+lib[0]
                else:
                    text += str(t.years)+" "+lib[1]
                text+=" "
            if t.months>1:
                text += str(t.months)+" "+lib[2]
            else:
                text += str(t.months)+" "+lib[3]
            text+=" "
            if t.days>1:
                text += str(t.days)+" "+lib[4]
            else:
                text += str(t.days)+" "+lib[5]
            text+=" "
            if hour:
                text+=" "
                if t.hours>1:
                    text += " "+str(t.hours)+" "+lib[6]
                else:
                    text += " "+str(t.hours)+" "+lib[7]
                text+=" "
                if t.minutes>1:
                    text += str(t.minutes)+" "+lib[8]
                else:
                    text += str(t.minutes)+" "+lib[9]
                text+=" "
                if t.seconds>1:
                    text += str(t.seconds)+" "+lib[10]
                else:
                    text += str(t.seconds)+" "+lib[11]
        return text


    async def time_interval(self,tmd,precision=2):
        """Crée un objet de type timedelta à partir d'un objet datetime.timedelta"""
        t = tmd.total_seconds()
        obj = self.timedelta(total_seconds=t,precision=precision)
        obj.set_from_seconds()
        return obj

    async def date(self,date,lang='fr',year=False,hour=True,digital=False):
        """Traduit un objet de type datetime.datetime en chaine de caractère lisible. Renvoie un str"""
        if type(date) == time.struct_time:
            date = datetime.datetime(*date[:6])
        if type(date) == datetime.datetime:
            if len(str(date.day))==1:
                jour="0"+str(date.day)
            else:
                jour = str(date.day)
            h=[]
            if lang == 'fr':
                month = fr_months
            elif lang == 'en':
                month = en_months
            else:
                month = fr_months
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
                if lang == 'en':
                    df = "{m}/{d}{y}  {h}"
                else:
                    df = "{d}/{m}{y}  {h}"
                df = df.format(d=jour,m=month,y = "/"+str(date.year) if year else "",h = ":".join(h) if hour else "")
            else:
                if lang == 'en':
                    df = "{m} {d}, {y}  {h}"
                else:
                    df = "{d} {m} {y}  {h}"
                df = df.format(d=jour,m=month[date.month-1],y=str(date.year) if year else "",h=":".join(h) if hour else "")
            return df



def setup(bot):
    bot.add_cog(TimeCog(bot))

