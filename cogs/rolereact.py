import discord
from discord.ext import commands
from util.DataHandler import ReactionRoleHandler
import asyncio

class RoleReact(commands.Cog):


    def __init__(self, bot):
        self.bot = bot
        self.data_handler = ReactionRoleHandler()
        self.manage_subcommand = {"change": "[JP]:役職の絵文字を変更します。[EN]:change a reaction needed for a role", "add":"[JP]:任意の役職を追加します。[EN]:add a role that users can add", "remove":"[JP]:自由に選べる役職を減らします。[EN]:remove a role a user can manage", "list":"[JP]:ユーザーが自由に選べる役職を表記します。[EN]:list all the roles users can manage", "cancel": "[JP]:コマンドキャンセル[EN]:cancels command"}
     
    

        
    def createReactionListEmbed(self, rolerecord, ctx):
        string = ""
        for record in rolerecord:
            tempObj = RoleObject(role=record['role'], reaction=record['reaction'])
            string = f"{string}\n{tempObj.get_role_mention()}: {tempObj.reaction}"
        embed = discord.Embed(title=self.bot.content_to_lang("[JP]:役職一覧[EN]:List of roles", ctx), description=string, color=0xc0ffee)
        return embed
        
    def has_permissions(self, ctx):
        if ctx.author.id == ctx.bot.owner_id:
            return True
        elif ctx.author.guild_permissions.manage_guild:
            return True
        elif ctx.author.guild_permissions.administrator:
            return True
        elif ctx.author.guild_permissions.manage_roles:
            return True
        else:
            return False
            
            
    def createRoleListEmbed(self, roles):
        embed = discord.Embed()
        return embed
        
    async def add_reaction_role(self, reaction, role):
        await self.data_handler.add_entry()
        
        
    def member_has_role(self, member, role):
        for roles in member.roles:
            if roles.id == role:   
                return True         
        return False
    
    @commands.guild_only()
    @commands.command(help="[JP]:droproleで排除したい役目を選ぶことができます。[EN]:droprole  lets you drop any valid role you currently have", aliases=["退部"])
    async def droprole(self, ctx):
        await self.data_handler.create_table(ctx.guild.id)
        all_roles = await self.data_handler.get_all_data(ctx.guild.id)
        all_role_consolidated = [x  for x in all_roles if self.member_has_role(ctx.author, (x["role"]))]
        prompt = await ctx.send(self.bot.content_to_lang("[JP]:外したい役職の絵文字にリアクトしてください。❌で終了します。50秒で自動廃止します。[EN]:React to message below for all the roles you want to remove. ❌ to finish. 50 second timeout.", ctx))
        role_list = await ctx.send(embed=self.createReactionListEmbed(all_role_consolidated, ctx))
        dict_of_reactions = {}
        for record in all_role_consolidated:
            await role_list.add_reaction(record['reaction'])
            dict_of_reactions[record['reaction']] = record['role']
        await role_list.add_reaction("❌")
        def check(r, u):
            return r.message.id == role_list.id and u == ctx.author and (str(r.emoji) == "❌" or str(r.emoji) in dict_of_reactions.keys())
        
        while True:
            try:
                reaction, user = await ctx.bot.wait_for('reaction_add', check=check, timeout = 50)
            except asyncio.TimeoutError:
                await prompt.delete()
                await role_list.delete()
                break
            else:                
                if str(reaction.emoji) == "❌":
                    await prompt.delete()
                    await role_list.delete()
                    break
                new_role = dict_of_reactions[str(reaction.emoji)]
                if self.canGetRole(ctx, new_role):
                    await ctx.author.remove_roles(ctx.guild.get_role(new_role))       
                    all_role_consolidated = [x for x in all_role_consolidated if x["role"] != new_role]
                    del dict_of_reactions[str(reaction.emoji)]
                    await role_list.edit(embed=self.createReactionListEmbed(all_role_consolidated, ctx))
                    await reaction.clear()
        
    
    @commands.guild_only()
    @commands.command(help="[JP]:addroleで任意の役職を与えることができます。[EN]:addrole gives you any role deemed valid by your administrators", aliases=["入部"])
    async def addrole(self, ctx):
        await self.data_handler.create_table(ctx.guild.id)
        all_roles = await self.data_handler.get_all_data(ctx.guild.id)
        all_role_consolidated = [x  for x in all_roles if not self.member_has_role(ctx.author, (x["role"]))]
        prompt = await ctx.send(self.bot.content_to_lang("[JP]:追加したい役職の絵文字にリアクトしてください。❌で終了します。50秒で自動廃止します。[EN]:React to message below for all the roles you want. ❌ to finish. 50 second timeout.", ctx))
        role_list = await ctx.send(embed=self.createReactionListEmbed(all_role_consolidated, ctx))
        dict_of_reactions = {}
        for record in all_role_consolidated:
            await role_list.add_reaction(record['reaction'])
            dict_of_reactions[record['reaction']] = record['role']
        await role_list.add_reaction("❌")
        def check(r, u):
            return r.message.id == role_list.id and u == ctx.author and (str(r.emoji) == "❌" or str(r.emoji) in dict_of_reactions.keys())
        
        while True:
            try:
                reaction, user = await ctx.bot.wait_for('reaction_add', check=check, timeout = 50)
            except asyncio.TimeoutError:
                await prompt.delete()
                await role_list.delete()
                break
            else:
                if str(reaction.emoji) == "❌":
                    await prompt.delete()
                    await role_list.delete()
                    break
                new_role = dict_of_reactions[str(reaction.emoji)]
                if self.canGetRole(ctx, new_role):
                    await ctx.author.add_roles(ctx.guild.get_role(new_role))
                    all_role_consolidated = [x for x in all_role_consolidated if x["role"] != new_role]
                    del dict_of_reactions[str(reaction.emoji)]
                    await role_list.edit(embed=self.createReactionListEmbed(all_role_consolidated, ctx))
                    await reaction.clear()

        
        
        
        
    def canGetRole(self, ctx, role):
        return True
    
    
    
    def find_roles(self, guild, txt):
        temp_list = []
        for role in guild.roles:
            if role.name == txt:
                temp_list.append(role)
            elif str(role.id) == txt:
                temp_list.append(role)
        if len(temp_list) > 0:
            return temp_list
        return None
    
   
    
    
    
        
    def is_manage_subcommand(self, txt):
        if txt.lower() in self.manage_subcommand.keys():
            return True
        else:
            return False
        
    
    @commands.guild_only()
    @commands.command(help="[JP]:manageroleでつけたい役職を決めることができます。[EN]:managerole lets you manage the roles that will be accesible for everyone")
    async def managerole(self, ctx):
        await self.data_handler.create_table(ctx.guild.id)
        if self.has_permissions(ctx):
            stringx = ""
            for command in self.manage_subcommand.keys():
                stringx=f"{stringx}\n ``{command}``: {self.bot.content_to_lang(self.manage_subcommand[command], ctx)}"
            embed = discord.Embed(title=self.bot.content_to_lang("[JP]:コマンド一覧[EN]:List of commands:", ctx), description=stringx)
            first_bot_message= await ctx.send(embed=embed)
            def check(message):
                return message.author == ctx.author and self.is_manage_subcommand(message.content)
            
            def role_check(message):
                if message.author != ctx.author:
                    return False
                if len(message.role_mentions) >= 1:
                    return message.role_mentions
                else:
                    return self.find_roles(ctx.guild, message.content)

            def reaction_check(r, u):
                return r.message.id  == msg.id and u == ctx.author 
            try:       
                replymsg = await ctx.bot.wait_for('message', check=check, timeout = 50)
            except asyncio.TimeoutError:
                await first_bot_message.delete()
                return
            else:     
                await first_bot_message.delete()
                reply = replymsg.content
                await replymsg.delete()
                if reply.lower() == 'add':
                    prompt=await ctx.send(self.bot.content_to_lang("[JP]:追加する役職を言ってください。50秒で自動廃止します。[EN]:Tell name of role(s). 50 second timeout.", ctx))
                    try:
                        message = await ctx.bot.wait_for('message', check=role_check, timeout = 50)
                    except asyncio.TimeoutError:
                        await prompt.delete()
                        return
                    else:
                        role_list = role_check(message)
                        await message.delete()
                        await prompt.delete()
                        count=0
                        for role in role_list:
                            if role.position >= ctx.guild.me.top_role.position:
                                await ctx.send(self.bot.content_to_lang(f"[JP]:``{role.name}``はあたしより上の役職だから管理できないわよ。[EN]:``{role.name}`` is a higher role than mine. I can't control it.", ctx),delete_after=5)
                            elif await self.data_handler.entry_exists(ctx.guild.id, role.id):
                                await ctx.send(self.bot.content_to_lang(f"[JP]:``{role.name}``は既に操作できるわよ。[EN]:``{role.name}`` is already available to the public.", ctx),delete_after=5)
                            else:
                                count+=1
                                msg = await ctx.send(self.bot.content_to_lang(f"[JP]:``{role.name}``に紐づける絵文字でリアクトしてください。50秒で自動廃止します。[EN]:React to message with emoji you want for ``{role.name}``. 50 second timeout.", ctx))
                                while True:
                                    try:
                                        rxn, user = await ctx.bot.wait_for('reaction_add', check=reaction_check, timeout = 50)
                                    except asyncio.TimeoutError:
                                        await msg.delete()
                                        return
                                    else:
                                        if await self.data_handler.value_exists(ctx.guild.id, str(rxn.emoji)):
                                            await ctx.send(self.bot.content_to_lang(f"[JP]:このリアクションは既に使われています。別のリアクションを選択ください。[EN]:This reaction is already tied to another role. Please select another.", ctx))
                                        else:
                                            await self.data_handler.add_entry(ctx.guild.id, RoleObject(role.id, str(rxn.emoji)))
                                            await msg.delete()
                                            break
                        if count >= 1:
                            await ctx.send(self.bot.content_to_lang(f"[JP]:役職を{count}つ追加しました。[EN]:Successfully added {count} roles", ctx),delete_after=5) 
                        
                        
                    
                    
                elif reply.lower() == 'remove':
                    prompt=await ctx.send(self.bot.content_to_lang("[JP]:削除する役職を言ってください。50秒で自動廃止します。[EN]:Tell name of role(s). 50 second timeout.", ctx))
                    try:
                        message = await ctx.bot.wait_for('message', check=role_check, timeout = 50)
                    except asyncio.TimeoutError:
                        await prompt.delete()
                        return
                    else:
                        role_list = role_check(message)
                        await message.delete()
                        for role in role_list:
                            if await self.data_handler.entry_exists(ctx.guild.id, role.id):
                                await self.data_handler.remove_entry(ctx.guild.id, role.id)
                                await ctx.send(self.bot.content_to_lang(f"[JP]:``{role.name}``は今後自由に選択できません。[EN]:``{role.name}`` can no longer be added freely", ctx),delete_after=5)
                            else:
                                await ctx.send(self.bot.content_to_lang(f"[JP]:``{role.name}``はもともと追加されていません。[EN]:``{role.name}``has not been added", ctx),delete_after=5)
                        
                        
                        
                    
                    
                elif reply.lower() == 'change':
                    prompt=await ctx.send(self.bot.content_to_lang("[JP]:変える役職を言ってください。50秒で自動廃止します。[EN]:Tell name of role(s). 50 second timeout.", ctx))
                    try:
                        message = await ctx.bot.wait_for('message', check=role_check, timeout = 50)
                    except asyncio.TimeoutError:
                        await prompt.delete()
                        return
                    else:
                        role_list = role_check(message)
                        await prompt.delete()
                        await message.delete()
                        for role in role_list:
                            if not await self.data_handler.entry_exists(ctx.guild.id, role.id):
                                await ctx.send(self.bot.content_to_lang(f"[JP]:``{role.name}``をまず追加してね。[EN]:``{role.name}``has not been added", ctx))
                            else:   
                                msg = await ctx.send(self.bot.content_to_lang(f"[JP]:``{role.name}``に紐づける新たなリアクションをしてください。50秒で自動廃止します。[EN]:React to message with new reaction you want for ``{role.name}`` 50 second timeout.", ctx))
                                while True:
                                    try:
                                        rxn, user = await ctx.bot.wait_for('reaction_add', check=reaction_check, timeout = 50)
                                    except asyncio.TimeoutError:
                                        await msg.delete()
                                        return
                                    else:
                                        if await self.data_handler.value_exists(ctx.guild.id, str(rxn.emoji)):
                                            await ctx.send(self.bot.content_to_lang(f"[JP]:このリアクションは既に使われています。別のリアクションを選択ください。[EN]:This reaction is already tied to another role. Please select another.", ctx))
                                        else:
                                            await self.data_handler.update_entry(ctx.guild.id, RoleObject(role.id, str(rxn.emoji)))
                                            await msg.delete()
                                            await ctx.send(self.bot.content_to_lang("[JP]:リアクション変更に成功しました。[EN]:Successfully changed reaction", ctx), delete_after=5)
                                            break
                                 
                        
                    
                
                elif reply.lower() == 'cancel':
                    return
                
                    
                elif reply.lower() == 'list':
                    await ctx.send(embed=self.createReactionListEmbed(await self.data_handler.get_all_data(ctx.guild.id), ctx))
                    
        
    @commands.guild_only()
    @commands.command(help="[JP]:listroleで選べる役職一覧を見ることができます。[EN]:listrole allows you to view roles which are available")
    async def listrole(self, ctx):
        await self.data_handler.create_table(ctx.guild.id)
        roles = await self.data_handler.get_all_data(ctx.guild.id)
        embed = self.createReactionListEmbed(roles, ctx)
        await ctx.send(embed=embed)
        
        
        
    @commands.Cog.listener()
    async def on_guild_join(self, guild):  #When the bot joins a server, we initalize certain parameters to avoid KeyError later on.
        await self.data_handler.create_table(guild.id)  #If the Server id is not registered in the JSON, we initailize it.
        
        
class RoleObject():
    __slots__=["role", "reaction"]


    def __init__(self, role, reaction):
        self.role = role
        self.reaction = reaction

        
        
    def to_dict(self):
        temp_dict = {"role": self.role, "reaction": self.reaction}
        return temp_dict
      
        
    def get_role_mention(self):
        return f"<@&{self.role}>"
        
def setup(bot):
    bot.add_cog(RoleReact(bot))