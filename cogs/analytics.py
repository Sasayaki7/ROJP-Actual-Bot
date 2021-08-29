import discord
from discord.ext import commands
from collections import Counter
import datetime
import math
import os
import seaborn as sns
import matplotlib
import matplotlib.pyplot as plt
import re
import typing
import asyncio
import json


from util.DataHandler import AnalyticsHandler, VoiceAnalyticsHandler, AnalyticLogs



class Analytics(commands.Cog):

    __slots__=["bot", "data_handler", "voicedata_handler", "voice_array", "ana_log", "ready_guilds", "check_start", "time_check", "disconnect", "lastcleanup", "send_to"]

    def __init__(self, bot):
        self.disconnect=False
        self.lastcleanup = None
        self.bot = bot
        self.data_handler = AnalyticsHandler()
        self.voicedata_handler = VoiceAnalyticsHandler()
        self.voice_array={}
        self.ana_log=AnalyticLogs()
        self.ready_guilds = []
        self.check_start = self.get_timelog()
        self.time_check = datetime.datetime.utcnow()
        self.send_to = {}
        

    def closest_date(self, dtime, time_interval_sec=24*3600):
        if time_interval_sec==24*3600:
            newdt = dtime.replace(hour=0, minute=0, second=0, microsecond=0)
            return newdt
        elif time_interval_sec==7*24*3600:
            weekday = dtime.weekday()
            newdt = dtime.replace(hour=0, minute=0, second=0, microsecond=0)-datetime.timedelta(weekday)
            return newdt
        elif time_interval_sec==15*24*3600:
            newdt = dtime.replace(day=1 if dtime.day < 15 else 15,  hour=0, minute=0, second=0, microsecond=0)
            return newdt
        elif time_interval_sec >= 30*24*3600:
            newdt = dtime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return newdt

    def closest_time(self, dtime, time_interval_sec=30*60):
        time_interval_min=time_interval_sec//60
        tempmin = dtime.hour*60+dtime.minute
        closest_min = tempmin//time_interval_min*time_interval_min
        newdt = dtime.replace(hour=closest_min//60, minute=closest_min%60, second=0, microsecond=0)
        return newdt

    def bin_by_time(self, list):
        authors= Counter(item["author_id"] for item in list)
        times = Counter(str(item["datetime"]) for item in list)
        return times, authors


    def get_timelog(self):
        with open("timelog.txt", "r") as f:
            return datetime.datetime.strptime(f.readline(), '%d/%m/%Y %H%M%S')


    def save_graph(self, ctx, x, y, title=None, x_axis=None, y_axis=None):
        pic_name = f"pic_{len(y)}.png"
        fig = plt.figure()
        sns.set(style="whitegrid")
        plt.plot(x, y, figure=fig)
        fig.suptitle(title)

        plt.ylim(bottom=0)
        plt.gcf().autofmt_xdate()
        plt.savefig(pic_name)
        plt.close(fig)
        return pic_name


    def get_time_interval(self, total_time):
        if total_time >= 270*3600*24:
            return 30*3600*24
        elif total_time >= 90*3600*24:
            return 15*3600*24
        elif total_time >= 45*3600*24:
            return 7*3600*24
        elif total_time >= 14*3600*24:
            return 24*3600
        elif total_time >= 2*3600*24:
            return 3600*3
        elif total_time >= 3600*15:
            return 3600
        elif total_time >= 3600*6:
            return 30*60
        elif total_time >= 3600:
            return 15*60
        elif total_time >= 1500:
            return 5*60
        else:
            return 60

    def to_lower(str):
        return str.lower()

    def identify_length(self, args: to_lower):
        days = ["days", "day", "d", "日"]
        weeks = ["week", "weeks", "w", "週", "週間"]
        months = ["m", "months", "month", "か月", "ヶ月", "か月間", "ヶ月間"]
        years = ["y", "years", "year", "年", "年間"]
        hours = ["hours", "hrs", "hr", "h", "時間", "hour"]
        minutes = ["min", "minute", "minutes", "分"]
        seconds = ["sec", "seconds", "s", "秒"]
        length=re.search("\d+", args)
        if not length:
            print('length')
            raise TypeError("Integer not found in date")
        length=length.group(0)
        if int(length) <= 0:
            print('negative')
            raise TypeError("Length of time must be positive")
        timeframe = re.search("\D+", args, re.UNICODE)
        if not timeframe:
            print('timeframe')
            raise TypeError("Timelength not recognized")
        timeframe=timeframe.group(0)
        t_length=int(length)
        if timeframe in days:
            return datetime.timedelta(days=t_length), f"[JP]:{t_length}日[EN]:{t_length} days"
        elif timeframe in weeks:
            return datetime.timedelta(weeks=t_length), f"[JP]:{t_length} 週間[EN]:{t_length} weeks"
        elif timeframe in months:
            return datetime.timedelta(days=t_length*30), f"[JP]:{t_length}か月[EN]:{t_length} months"
        elif timeframe in years:
            return datetime.timedelta(days=t_length*365), f"[JP]:{t_length}年[EN]:{t_length} years"
        elif timeframe in minutes:
            return datetime.timedelta(minutes=t_length), f"[JP]:{t_length}分[EN]:{t_length} minutes"
        elif timeframe in hours:
            return datetime.timedelta(hours=t_length), f"[JP]:{t_length}時間[EN]:{t_length} hours"
        elif timeframe in seconds:
            return datetime.timedelta(seconds=t_length), f"[JP]:{t_length}秒[EN]:{t_length} seconds"
        else:
            return #todo: raise exception

    async def prep_guild(self, guild):
        start = guild.created_at
        check_time = start+datetime.timedelta(seconds=(self.time_check-start).total_seconds()/2)
        start_time = self.check_start if await self.ana_log.data_exists(guild.id, check_time) else guild.created_at
        message_c =await self.get_messages_from_api(guild, start_time, self.time_check)
        await self.log_message_count(guild, message_c)
        self.ready_guilds.append(guild.id)
        if guild.id in self.send_to:
            for channel in self.send_to[guild.id]:
                await guild.get_channel(channel).send("準備できたよ!")

    def read_from_cleanup_file(self):
        with open("lastcleanup.txt") as f:
            self.lastcleanup = datetime.datetime.strptime(f.read(), '%d/%m/%Y %H%M%S')

    async def startup(self):
        if not self.disconnect:
            await self.update_vc()
            for guild in self.bot.guilds:
                await self.prep_guild(guild)

    async def update_vc(self):
        try:
            with open('vclog.txt') as f:
                old_logs=json.load(f)
            for item in old_logs:
                await voicedata_handler.add_entry(old_logs[item][1], int(item), 0, old_logs[item][0], int((self.check_start-old_logs[item][0]).total_seconds()))
        except json.JSONDecodeError:
            pass
        finally:
            for guild in self.bot.guilds:
                for voice_channels in guild.voice_channels:
                    for member in voice_channels.members:
                        self.voice_array[member.id]=(datetime.datetime.utcnow(), guild.id)



    def get_keys_by_month(self, start, end, interval):
        month = start.month
        year = start.year
        empty_array = [start]
        if interval == 24*15*3600 and start.day == 1:
            empty_array.append(start.replace(year=year, month=month, day=15))
        while end.year >= year:
            while month < 12 and not (month==end.month and year == end.year):
                month += 1
                empty_array.append(start.replace(year=year, month=month, day=1))
                if interval == 24*15*3600:
                    empty_array.append(start.replace(year=year, month=month, day=15))
            month=0
            year+=1
        if end.day == 15:
            empty_array.append(end.replace(day=1))
        return empty_array


    async def get_earliest(self, guild, begin, end):
        '''Gets the earliest timestamp within specified time range
             -- returns datetime
        '''
        return await self.ana_log.get_earliest_date(guild, begin)["stamp"]



    async def get_latest(self, begin, end):
        '''Gets the latest timestamp within specified time range
            -- returns datetime
        '''
        return await self.ana_log.get_latest_date(guild, end)["stamp"]

    def encode(self, message):
        tst = message.created_at
        time_interval=self.get_time_interval((datetime.datetime.utcnow()-tst).total_seconds())
        new_dt = self.closest_date(tst) if time_interval >=24*3600 else self.closest_time(tst, time_interval)

        code = f"{message.channel.id}+{message.author.id}+{new_dt.strftime('%d/%m/%Y %H%M')}"
        return code


    async def cleanup(self):
        savetime = datetime.datetime.utcnow()
        with open("lastcleanup.txt", "w") as f:
            f.write(savetime.strftime('%d/%m/%Y %H%M%S'))
        def convert(oldtime):
            time_int = self.get_time_interval((savetime-oldtime).total_seconds())
            if time_int >= 24*3600:
                return self.closest_date(oldtime)
            else:
                return self.closest_time(oldtime, time_int)
        await self.ana_log.cleanup(savetime-datetime.timedelta(days=14), convert)


    def decode(self, encodedkey):
        items = encodedkey.split('+')
        return int(items[0]), int(items[1]), datetime.datetime.strptime(items[2], '%d/%m/%Y %H%M')


    async def get_messages_from_log(self, ctx, search_start, author=None):
        if author:
            return await self.ana_log.fetch_all_after_for_user(ctx.guild.id, search_start, author)
        else:
            return await self.ana_log.fetch_all_after(ctx.guild.id, search_start)


    async def get_messages_from_api(self, guild, beginning, end):
        new_recorder = Counter()
        for text_channels in guild.text_channels:
            if text_channels.permissions_for(guild.me).read_message_history:
                async for message in text_channels.history(limit=None, before=end, after=beginning):
                    new_recorder[self.encode(message)]+=1
        return new_recorder


    async def log_message_count(self, guild, counter):
        for entry in counter.most_common():
            decoder = self.decode(entry[0])
            await self.ana_log.save_entry(guild.id, decoder[0], decoder[1], decoder[2], entry[1])

    async def analyze(self):
        pass

    def cog_unload(self):
        for member in self.voice_array:
            self.voice_array[member]=self.voice_array[member].strftime('%d/%m/%Y %H%M%S')
        with open('vclog.txt', "w") as f:
            json.dump(self.voice_array,f)
        with open("timelog.txt", "w") as f:
            f.write(datetime.datetime.utcnow().strftime('%d/%m/%Y %H%M%S'))
        self.disconnect = False


    @commands.Cog.listener()
    async def on_ready(self):
        await self.startup()



    @commands.Cog.listener()
    async def on_disconnect(self):
        self.disconnect=True
        for member in self.voice_array.keys():
            start_time = self.voice_array[member][0]
            duration = datetime.datetime.utcnow()-start_time
            await self.voicedata_handler.add_entry(self.voice_array[member][1], author_id=member, channel=0, stamp = start_time, duration=int(duration.total_seconds()))


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild:
            await self.ana_log.save_entry(message.guild.id, author=message.author.id, channel=message.channel.id, stamp = self.closest_time(datetime.datetime.utcnow(), time_interval_sec=60), count=1)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.data_handler.add_entry(member.guild.id, type="member_join", author_id=member.id, channel=0, stamp = datetime.datetime.utcnow())

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.data_handler.add_entry(member.guild.id, type="member_remove", author_id=member.id, channel=0, stamp = datetime.datetime.utcnow())


    @commands.Cog.listener()
    async def on_member_ban(self,guild, member):
        await self.data_handler.add_entry(guild.id, type="member_ban", author_id=member.id, channel=0, stamp = datetime.datetime.utcnow())



    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if not reaction.message.guild:
            return
        if reaction.message.author != self.bot.user and reaction.message.guild:
            await self.data_handler.add_entry(reaction.message.guild.id, type="reaction_add", author_id=user.id, channel=reaction.message.channel.id, stamp = datetime.datetime.utcnow())


    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel == None and after.channel != None:
            self.voice_array[member.id]=(datetime.datetime.utcnow(), member.guild.id)
        elif before.channel != None and after.channel == None:
            start_time = self.voice_array[member.id]
            duration = datetime.datetime.utcnow()-start_time[0]
            await self.voicedata_handler.add_entry(member.guild.id, author_id=member.id, channel=before.channel.id, stamp = start_time[0], duration=int(duration.total_seconds()))
            del self.voice_array[member.id]

    @commands.guild_only()
    @commands.command(hidden=True)
    async def sstats(self, ctx):
        member_online = Counter(str(m.status) for m in ctx.guild.members)
        embed = discord.Embed(title="Server Stats", color=0x0000ff)
        embed.add_field(name="ID", value=ctx.guild.id, inline=True)
        embed.add_field(name="Owner", value=f"{ctx.guild.owner.name}#{ctx.guild.owner.discriminator}", inline=True)
        embed.add_field(name="Date Created", value=ctx.guild.created_at, inline=True)
        embed.add_field(name="Members", value=f'🟢:{member_online["online"]}   🟡:{member_online["idle"]}   🔴:{member_online["dnd"]}   ⚫:{member_online["offline"]}\n' \
              f'Total: {ctx.guild.member_count}', inline=False)
        #embed.add_field(name="Bans", value=len(await ctx.guild.bans()))
        await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.prep_guild(guild)


    @commands.guild_only()
    @commands.command(help="[JP]:join [ユーザー]でサーバー参加した日を確認できるよ！[EN]:join <member> shows when person first joined server")
    async def join(self, ctx, member: typing.Optional[discord.Member] = None):
        if not member:
            member = ctx.author
        await ctx.send(self.bot.content_to_lang(f"[JP]:{member.name}は{member.joined_at.date()}にサーバーに入りました[EN]:{member.name} joined server on {member.joined_at.date()}", ctx))

    @commands.guild_only()
    @commands.command(help="[JP]:analytics [メンバー] [過去時間]で自分の行動をデータにして見れるよ～[EN]:analyics <member> <time> shows you your recent activity")
    async def analytics(self, ctx, member: typing.Optional[discord.Member] = None, duration=None):
        if not ctx.guild.id in self.ready_guilds:
            await ctx.send(self.bot.content_to_lang("[JP]:このサーバーはまだ準備が必要。終わったら呼ぶね！[EN]:I still need to make preparations...I'll let you know when I'm done.", ctx))
            if not ctx.guild.id in self.send_to:
                self.send_to[ctx.guild.id]=[]
            if not ctx.message.channel.id in self.send_to[ctx.guild.id]:
                self.send_to[ctx.guild.id].append(ctx.message.channel.id)
            return
        msg=await ctx.send(self.bot.content_to_lang("[JP]:時間かかるので少し待ってて…[EN]:This may take a while...", ctx))
        async with ctx.typing():
            if not member:
                member = ctx.author
            id=member.id
            message_counter=Counter()
            reaction_counter = Counter()
            voice_counter=Counter()
            string=None

            time_back = datetime.timedelta(days=1)
            if duration:
                try:
                    time_back, string = self.identify_length(duration)
                    string = self.bot.content_to_lang(string, ctx.guild)
                except TypeError:
                    await ctx.send(self.bot.content_to_lang("[JP]:期間の入力方法が間違ってるよ[EN]:Invalid date format entered", ctx))
                    await msg.delete()
                    return
                if time_back.total_seconds() < 60:
                    await ctx.send(self.bot.content_to_lang("[JP]:1分以下の期間は探し出せない。[EN]:I don't support analyzing timeframes below 1 minute", ctx))
                    await msg.delete()
                    return
                elif time_back.total_seconds() > 24*365*20*3600+5*24*3600:
                    await ctx.send(self.bot.content_to_lang("[JP]:20年以上の期間は対応出来ない。[EN]:I don't support analyzing timeframes above 20 years", ctx))
                    await msg.delete()
                    return
            now = datetime.datetime.utcnow()
            check_time = now-time_back
            time_interval = self.get_time_interval(time_back.total_seconds())

            beginning = self.closest_date(check_time) if time_interval >= 24*3600 else self.closest_time(check_time, time_interval)
            for record in await self.get_messages_from_log(ctx, beginning, author=id):
                key = self.closest_date(record["stamp"], time_interval) if time_interval >= 24*3600 else self.closest_time(record["stamp"], time_interval)
                message_counter[str(key)]+=record["count"]



            begin= self.closest_date(check_time, time_interval) if time_interval >= 24*3600 else self.closest_time(check_time, time_interval)
            keys = [begin+datetime.timedelta(seconds=time_interval*i) for i in range(int(time_back.total_seconds())//time_interval+1)] if time_interval < 15*24*3600 else self.get_keys_by_month(begin, self.closest_date(now, time_interval), time_interval)
            values = [message_counter[str(key)] if str(key) in message_counter else 0 for key in keys]


            records = await self.data_handler.fetch_all_after_for_user(ctx.guild.id, check_time, id)
            for record in records:
                if record["type"]=="reaction_add":
                    reaction_counter.update((record["type"]))
            embed = discord.Embed(title=self.bot.content_to_lang(f"[JP]:{self.bot.get_user(id).name}の過去{string if string else '1日'}のデータ\
                [EN]:Past {string if string else 'day'} data for {self.bot.get_user(id).name}", ctx), color=0x00ff00)


            voicerecords = await self.voicedata_handler.fetch_all_after_for_user(ctx.guild.id, check_time, id)
            for record in voicerecords:
                voice_counter.update({"record": record["duration"], record["author_id"]: record["duration"]})

            for people in self.voice_array:
                if self.voice_array[people][1] == ctx.guild.id:
                    ts = int((datetime.datetime.utcnow()-self.voice_array[people][0]).total_seconds())
                    voice_counter.update({"record": ts, people: ts})

            embed.add_field(name=self.bot.content_to_lang("[JP]:送信したメッセージ数:[EN]:Messages sent:", ctx), value= self.bot.content_to_lang("[JP]:メッセージを送信していません。:[EN]:No messages sent", ctx) if len(message_counter.most_common(1)) == 0 else sum(message_counter.values()), inline=False)
            embed.add_field(name=self.bot.content_to_lang("[JP]:計リアクト数:[EN]:Total reacts:", ctx), value= self.bot.content_to_lang("[JP]:リアクションしていません。:[EN]:No reacts sent", ctx) if len(reaction_counter.most_common(1)) == 0 else reaction_counter.most_common(1)[0][1], inline=False)
            embed.add_field(name=self.bot.content_to_lang("[JP]:ボイスチャットにいる時間の総数:[EN]:Total time in VoiceChat:", ctx), value=self.bot.content_to_lang("[JP]:このユーザーはボイスチャットに参加した経歴ありません。[EN]:User never joined voice chat", ctx) if len(voice_counter.most_common(1)) == 0 else self.convert_to_readable_time(voice_counter.most_common(1)[0][1]), inline=False)

            pic_name=self.save_graph(ctx, keys, values, title=f"Messages from past {string if string else '1 day'}")
            f = discord.File(f"{pic_name}")
            embed.set_image(url=f"attachment://{pic_name}")
            await ctx.send(file=f, embed=embed)
            os.remove(pic_name)
            await msg.delete()


    def convert_to_readable_time(self, secs):
        return f"{secs//(3600*24)}d {secs%(3600*24)//3600}h {(secs%3600)//60}m {secs%60}s"

    @commands.command(hidden=True)
    async def clean(self, ctx):
        await self.cleanup()
        await ctx.send("Clean successful")

    @commands.guild_only()
    @commands.command(help="[JP]:sanalytics [過去時間]でサーバー過去の行動をデータにして見れるよ～[EN]:analytics <time> shows the server's recent activity")
    async def sanalytics(self, ctx, *, duration=None):
        if not ctx.guild.id in self.ready_guilds:
            await ctx.send(self.bot.content_to_lang("[JP]:このサーバーはまだ準備が必要。終わったら呼ぶね！[EN]:I still need to make preparations...I'll let you know when I'm done.", ctx))
            if not ctx.guild.id in self.send_to:
                self.send_to[ctx.guild.id]=[]
            if not ctx.message.channel.id in self.send_to[ctx.guild.id]:
                self.send_to[ctx.guild.id].append(ctx.message.channel.id)
            return
        msg=await ctx.send(self.bot.content_to_lang("[JP]:時間かかるので少し待ってて…[EN]:This may take a while...", ctx))
        string=None
        message_counter=Counter()

        async with ctx.typing():

            time_back = datetime.timedelta(days=1)
            if duration:
                try:
                    time_back, string = self.identify_length(duration)
                    string = self.bot.content_to_lang(string, ctx)
                except TypeError:
                    await ctx.send(self.bot.content_to_lang("[JP]:期間の入力方法が間違ってるよ[EN]:Invalid date format entered", ctx))
                    await msg.delete()
                    return
                if time_back.total_seconds() < 60:
                    await ctx.send(self.bot.content_to_lang("[JP]:1分以下の期間は探し出せない。[EN]:I don't support analyzing timeframes below 1 minute", ctx))
                    await msg.delete()
                    return
                elif time_back.total_seconds() > 24*365*20*3600+5*24*3600:
                    await ctx.send(self.bot.content_to_lang("[JP]:20年以上の期間は対応出来ない。[EN]:I don't support analyzing timeframes above 20 years", ctx))
                    await msg.delete()
                    return

            now = datetime.datetime.utcnow()
            check_time = now-time_back
            records = await self.data_handler.fetch_all_after(ctx.guild.id, check_time)
            voicerecords = await self.voicedata_handler.fetch_all_after(ctx.guild.id, check_time)
            time_interval = self.get_time_interval(time_back.total_seconds())

            beginning = self.closest_date(check_time) if time_interval >= 24*3600 else self.closest_time(check_time, time_interval)
            ending = self.closest_time(now, time_interval_sec=60)


            message_author=Counter()
            for record in await self.get_messages_from_log(ctx, beginning):
                key = self.closest_date(record["stamp"], time_interval) if time_interval >= 24*3600 else self.closest_time(record["stamp"], time_interval)
                message_counter[str(key)]+=record["count"]
                message_author[record["author_id"]]+=record["count"]


            begin= self.closest_date(check_time, time_interval) if time_interval >= 24*3600 else self.closest_time(check_time, time_interval)
            keys = [begin+datetime.timedelta(seconds=time_interval*i) for i in range(int(time_back.total_seconds())//time_interval+1)] if time_interval < 15*24*3600 else self.get_keys_by_month(begin, self.closest_date(now, time_interval), time_interval)
            values = [message_counter[str(key)] if str(key) in message_counter else 0 for key in keys]

            reaction_counter = Counter()
            records = await self.data_handler.fetch_all_after(ctx.guild.id, check_time)
            for record in records:
                if record["type"]=="reaction_add":
                    reaction_counter.update((record["type"], record["author_id"]))
            embed = discord.Embed(title=self.bot.content_to_lang(f"[JP]:過去{string or '1日間'}のサーバー統計[EN]:Server Stats for past {string or '1 day'}",ctx), color=0x00ff00)



            voice_counter=Counter()
            voicerecords = await self.voicedata_handler.fetch_all_after(ctx.guild.id, check_time)
            for record in voicerecords:
                voice_counter.update({"record": record["duration"], record["author_id"]: record["duration"]})

            for people in self.voice_array:
                if self.voice_array[people][1] == ctx.guild.id:
                    ts = int((datetime.datetime.utcnow()-self.voice_array[people][0]).total_seconds())
                    voice_counter.update({"record": ts, people: ts})

            def get_top(counter, x):
                iterator=counter.most_common(x+1)
                dummyStr = ""
                for i in range(1, len(iterator)):
                    dummyStr=f"{dummyStr}{i}. <@!{iterator[i][0]}>: {iterator[i][1]} \n"
                if dummyStr == "":
                    return "None yet."
                return dummyStr

            def get_top_secs(counter, x):
                iterator=counter.most_common(x+1)
                dummyStr = ""
                for i in range(1, len(iterator)):
                    dummyStr=f"{dummyStr}{i}. <@!{iterator[i][0]}>: {self.convert_to_readable_time(iterator[i][1])} \n"
                if dummyStr == "":
                    return "None yet."
                return dummyStr

            def get_results(counter):
                if len(counter)==0:
                    return 0
                else:
                    return counter.most_common(1)[0][1]
            embed.add_field(name=self.bot.content_to_lang("[JP]:最多メッセージ数[EN]:Most messages sent:",ctx), value=get_top(message_author, 3), inline=False)
            embed.add_field(name=self.bot.content_to_lang("[JP]:最多リアクション数[EN]:Most reactions made:",ctx), value=get_top(reaction_counter, 3), inline=False)
            embed.add_field(name=self.bot.content_to_lang("[JP]:ボイスチャット依存時間最長[EN]:Longest time in voice chat:",ctx), value=get_top_secs(voice_counter, 3), inline=False)
            embed.add_field(name=self.bot.content_to_lang("[JP]:累計メッセージ数[EN]:Total messages sent:",ctx), value=sum(message_author.values()), inline=True)
            embed.add_field(name=self.bot.content_to_lang("[JP]:リアクション累計[EN]:Total reactions:",ctx), value=get_results(reaction_counter), inline=True)

            pic_name=self.save_graph(ctx, keys, values, title=f"Messages from past {string if string else '1 day'}")
            f = discord.File(f"{pic_name}")
            embed.set_image(url=f"attachment://{pic_name}")
            await ctx.send(file=f, embed=embed)
            os.remove(pic_name)
            await msg.delete()

    @join.error
    @sstats.error
    @sanalytics.error
    @analytics.error
    async def analyticerror(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await self.bot.nodm(ctx, error)

    @commands.is_owner()
    @commands.command(hidden=True)
    async def gstats(self, ctx, id):
        logs = self.data_handler.fetch_and_delete(ctx.guild.id)
        fd = os.open(f"log_{guildId}.txt", os.O_CREAT | os.O_WRONLY | os.O_NONBLOCK)
        os.write(fd, "data")
        os.close(fd)

def setup(bot):
    bot.add_cog(Analytics(bot))
