import discord
from discord.utils import get
from discord.ext import commands
from discord.utils import find
from util.DataHandler import LinkHandler
from util.pageMenu import PageMenu
from discord.ext.commands.cooldowns import BucketType
from fuzzywuzzy import process, fuzz
import asyncio
import re


class LinkCog(commands.Cog):

    __slots__ = ["bot", "data_handler"]

    def __init__(self, bot):
        self.bot = bot
        self.data_handler = LinkHandler()

    async def update_link(self, entry):  #updates starboardJson and returns the number of reactions that changed
        await self.data_handler.update_entry(entry)



    async def link_exists(self, guildId, id): #checks if link database already contains the given message. returns a boolean
        return await self.data_handler.entry_exists(guildId, id=id)



    async def get_link(self, guildId, id):
        if (await self.link_exists(guildId, id)):
            record= await self.data_handler.get_entry(guildId, id)
            link = Link(guild_id=guildId, id=id, tag=record["tag"], owner=record["owner"])
            return link
        else:
            return None

    async def fuzzysearch(self, tag, guildId):
        list = await self.data_handler.get_all_data(guildId)
        choices = [x["id"] for x in list]
        candidates= process.extractBests(tag, choices, scorer=fuzz.partial_ratio, score_cutoff=85)
        return candidates


    async def get_link_owner(self, guildId, id):
        link = await self.get_link(guildId, id)
        if link:
            return link.owner
        else:
            return None

    def getOneLineEmbed(self, embedTitle, embedText, guild):
        embedTitle=self.bot.content_to_lang(embedTitle, guild)
        embedText=self.bot.content_to_lang(embedText, guild)
        embed=discord.Embed(title=embedTitle, description=embedText, color=0x15ee00)
        return embed

    async def set_link(self, guildId, link):
        await self.data_handler.add_entry(guildId, link)


    async def remove_link(self, guildId, link):
        await self.data_handler.remove_entry(guildId, link)



    async def get_all_links(self, guildId):
        list = await self.data_handler.get_all_data(guildId)
        sortedList = sorted(list, key=lambda x: x["id"].lower())
        return sortedList

    def has_permissions(self, ctx):
        if ctx.author.id == self.bot.owner_id:
            return True
        elif ctx.author.guild_permissions.manage_guild:
            return True
        elif ctx.author.guild_permissions.administrator:
            return True
        elif ctx.author.guild_permissions.manage_roles:
            return True
        else:
            return False

    async def get_link_list(self, guildId, tagToStart=None):
        sortedList = await self.get_all_links(guildId)
        if tagToStart == None:
            return sortedList
        else:
            newList = [x for x in sortedList if x["id"].lower()[:len(tagToStart)] == tagToStart.lower() ]
            return newList

    async def process_link(self, message, args, command=True):
        prefix = await self.bot.get_prefix(message)
        localLink = await self.link_exists(message.guild.id, args)
        if localLink:
            tag =await self.get_link(message.guild.id, args)
            await message.channel.send(tag.tag)
            return
        fuzzyResults = await self.fuzzysearch(args, message.guild.id)
        if len(fuzzyResults) == 1:
            closeTag = await self.get_link(message.guild.id, fuzzyResults[0][0])
            msg = await message.channel.send(self.bot.content_to_lang(f"[JP]:``{args}``は見当たらなかったけど…``{fuzzyResults[0][0]}`` なら見つかったよ。これかな？\
				[EN]:I couldn't find a tag matching ``{args}`` but… I found ``{fuzzyResults[0][0]}``. Is this it?", message.guild))
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            reaction = ""
            def check(r, u):
                return r.message.id == msg.id and u == message.author and (str(r.emoji)=="❌" or str(r.emoji)=="✅")
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout = 15)
            except asyncio.TimeoutError:
                await msg.edit(content=self.bot.content_to_lang(f"[JP]:{message.author.mention}に聞いてるのに答えてくれない...\U0001f62d[EN]:I'm asking {message.author.mention} but they won't answer...\U0001f62d", message.guild))
                await msg.clear_reactions()
            else:
                if str(reaction.emoji) == "✅":
                    await msg.delete()
                    await message.channel.send(closeTag.tag)
                else:
                    await msg.edit(content=self.bot.content_to_lang("[JP]:違ったのね...[EN]:Oh... never mind..", message.guild))
                    await msg.clear_reactions()

        elif len(fuzzyResults) > 1:
            string = ""
            for i in fuzzyResults:
                string = f"{string}{i[0]}\n"
            embed = discord.Embed(description=string)
            await message.channel.send(self.bot.content_to_lang(f"[JP]:惜しいのがいくつもあったよ…もしかしてこれのどれか？[EN]:I found several similar ones.... is it any of these?", message.guild), embed=embed)

        elif command:
            await message.channel.send(self.bot.content_to_lang(f"[JP]:ごめんなさい、``{args}``のタグ見つれられなかった…　\nタグを登録したかったら {prefix}setlink {args} [内容]で登録できるよ!\
                [EN]:Sorry, I couldn't find link ``{args}``…　\nIf you want to use this link, please use {prefix}setlink {args} <content>", message.guild))


    @commands.Cog.listener()
    async def on_guild_join(self, guild):  #When the bot joins a server, we initalize certain parameters to avoid KeyError later on.
        await self.data_handler.create_table(guild.id)  #If the Server id is not registered in the JSON, we initailize it.


    @commands.Cog.listener()
    async def on_message(self, message):
        prefix = await self.bot.get_prefix(message)
        if message.content and message.content[:len(prefix)] == prefix and message.content != prefix:
            for role in message.author.roles:
                if role.name == '鎮静(ミュート)':
                    return
            if not get(self.bot.commands, name=re.search("\S+",message.content[len(prefix):]).group(0)):
                await self.process_link(message, message.content[len(prefix):], command=False)



    @commands.guild_only()
    @commands.group(help="""[JP]:link [タグ] で以前保存したタグを私が引っ張ってきて提示します! [EN]:link <tag> gets the word/sentence/phrase/link/image/whatever stored in <tag>.""", brief="保存されてるタグを引っ張ってきます。", invoke_without_command=True)
    async def link(self, ctx, *, args):
        await self.process_link(ctx.message, args)

    @link.error
    async def linkerror(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(self.bot.content_to_lang(f"[JP]:コマンドの長さが足りないよ！コマンドは ``{ctx.prefix}link [タグ]`` だよ!\
				[EN]:Command missing argument. Correct format is ``{ctx.prefix}link <tag>``", ctx))





    @commands.guild_only()
    @commands.command(help="[JP]:setlink　[タグ] [内容]で使われてないタグに内容を保存することができます。迷惑行為を防ぐ為にメンション付のメッセージは保存できません。[EN]:setlink <tag> <content> stores content. You can call the content by using the link command. To prevent abuse, you cannot store mentions.")
    async def setlink(self, ctx, arg1, *, arg2):
        guildId = ctx.guild.id
        tagString = ""
        link=None
        link = Link(guild_id=guildId, id=arg1, tag=arg2, owner=ctx.author.id)

        if await self.link_exists(guildId, arg1):
            await ctx.send(self.bot.content_to_lang(f"[JP]:ごめんなさい、``{arg1}``のタグは既に登録されてます…　別のタグを使って見て登録してご覧!\
				[EN]:Link ``{arg1}`` is already taken. Please try a different tag", ctx))
        elif len(ctx.message.mentions) > 0 or len(ctx.message.role_mentions) > 0 or (ctx.message.mention_everyone==True):
            await ctx.send(self.bot.content_to_lang(f"[JP]:ごめんなさい、メンションのあるメッセージは迷惑だから登録出来ないの。メンションを消してもう一回登録してみて![EN]:Sorry, you cannot use mentions in tags", ctx))
        elif await self.data_handler.tag_exists(guildId, arg2):
            tag = await self.data_handler.get_id_of_tag(guildId, arg2)
            await ctx.send(self.bot.content_to_lang(f"[JP]:``{arg2}``は既に``{tag[0]['id']}``のタグに登録されてるから、そっちを使うかタグを消してもらおう。\
				[EN]:``{arg2}`` is already under the link ``{tag[0]['id']}``. Use that instead. or have the link deleted.", ctx))
        else:
            await self.set_link(guildId, link)
            await ctx.send(embed =self.getOneLineEmbed("[JP]:タグ登録成功しました![EN]:Tag successfully stored",
                f"[JP]:``{arg1}``のタグ登録に成功しました！[EN]:``{arg1}`` has been registered!", ctx))

    @setlink.error
    async def setlinkerror(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name=="arg1":
                await ctx.send(self.bot.content_to_lang(f"[JP]:コマンドの長さが足りないよ！コマンドは ``{ctx.prefix}setlink [タグ] [内容]`` だよ!\
                    [EN]:Command missing argument. Correct format is ``{ctx.prefix}setlink <tag> <content>``", ctx))
            else:
                await ctx.send(self.bot.content_to_lang(f"[JP]:コマンドの長さが足りないよ！コマンドは ``{ctx.prefix}setlink {ctx.args[2]} [内容]`` だよ!\
                    [EN]:Command missing argument. Correct format is ``{ctx.prefix}setlink {ctx.args[2]} <content>``", ctx))



    @commands.guild_only()
    @link.command(help="[JP]:link remove [タグ]で自分が以前作ったタグ、あるいは権限を持ってる方がタグを消すことができます。[EN]:link remove <tag> removes the tag for other people to use.")
    @commands.cooldown(rate=1, per=3, type = BucketType.user)
    async def remove(self, ctx, *, args):
        guildId = ctx.guild.id
        tag = await self.get_link(guildId, args)
        if tag and (tag.owner==ctx.message.author.id or self.has_permissions(ctx)):
            await self.remove_link(guildId, tag)
            await ctx.send(embed =self.getOneLineEmbed("[JP]:タグを削除しました![EN]:Tag deleted!", f"[JP]:{args}　のタグは消しておきました！[EN]:Tag {args}　has been successfully deleted!", ctx))
        elif not tag:
            await ctx.send(self.bot.content_to_lang("[JP]:このタグ最初から存在しなかったので、一応消えてるよ![EN]:This tag didn't exist anyways.", ctx))

        else:
            await ctx.send(self.bot.content_to_lang(f"[JP]:ごめんなさい、このタグは別の方が持っています。タグを削除したかったら<@!{tag.owner}>かサーバーの管理人さんに聞いてね!\
                [EN]:This tag is owned by someone else. If you want this tag gone, please ask <@!{tag.owner}> or a server mod.", ctx))

    @remove.error
    async def removeerror(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(self.bot.content_to_lang(f"[JP]:コマンドの長さが足りないよ！コマンドは ``{ctx.prefix}link remove [タグ]`` だよ!\
                [EN]:Insufficient command length! Command should be ``{ctx.prefix}link remove <tag>``", ctx))



    @commands.guild_only()
    @commands.command(help="[JP]:linklist で今登録されてるタグ一覧を教えてあげる。linklist [文字]すれば[文字]から始まるタグ一覧を引っ張ってくるよ！[EN]:linklist shows the list of tags. linklist <string> shows all the links that start with <string>")
    async def linklist(self, ctx, *, args=None):
        if not args:
            tagString = ctx.message.content[len(ctx.prefix)+9:]
            sortedListOfRecords = await self.get_link_list(ctx.guild.id, tagString)
        else:
            sortedListOfRecords = await self.get_link_list(ctx.guild.id)
        sortedListOfLinks = [records["id"] for records in sortedListOfRecords]
        if len(sortedListOfLinks) == None:
            await ctx.send(self.bot.content_to_lang(f"[JP]:このサーバーにはタグがまだ無いみたいよ！ {ctx.prefix}setlink [タグ] [内容]でタグ作ってみようよ！\
                [EN]:This server has no tags. Create the first by using ``{ctx.prefix}setlink <tag> <content>", ctx))
            return
        elif len(sortedListOfLinks) == 0:
            await ctx.send(self.bot.content_to_lang(f"[JP]:この条件に当てはまるタグは見当たらなかったな…[EN]:Could not find tags meeting specified condition", ctx))
            return
        link_menu = PageMenu(ctx=ctx, title=self.bot.content_to_lang("[JP]:タグ一覧[EN]:Tag List", ctx), lists = [sortedListOfLinks],
            subheaders = self.bot.content_to_lang("[JP]:タグ[EN]:Tags", ctx))
        await link_menu.activate()





class Link():

    __slots__=["id", "tag", "owner", "guild_id"]


    def __init__(self, guild_id, id, tag, owner):
        self.id = id
        self.tag = tag
        self.owner = owner
        self.guild_id = guild_id


    def to_dict(self):
        temp_dict = {"id": self.id, "owner": self.owner, "tag": self.tag}
        return temp_dict


    def get_id(self):
        return self.id


    def get_owner_id(self):
        return self.owner


    def get_owner_mention(self):
        return f"<@!{self.owner}>"

    def get_tag(self):
        return self.tag

def setup(bot):
    bot.add_cog(LinkCog(bot))
