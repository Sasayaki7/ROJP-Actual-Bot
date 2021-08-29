
import datetime
import asyncpg

class DataHandler:
    
	
    def __init__(self, parameters = None, backup= 99999999, database_name=None):
        self.backup=backup
        self.data = {}
        self.parameters = parameters or {}
        self.debounce = False
        self.database_name = database_name or "botdb"


        
    def _convert_dict_to_keys_and_value_query(self,dict):
        keys = ""
        for key in dict.keys():
            keys=f"{keys},{key}"
        values = ""
        for value in dict.values():
            if isinstance(value, str):
                value = f"'{value}'"
            values=f"{values},{value}"
        return keys[1:], values[1:]
        
    async def _check_and_create_table_exists(self, tablename, dict):
        connection = await self._get_connection()
        query = ""
        for i in dict:
            query = f"{query},{i} {dict[i]}"
        query = query[1:]
        await connection.execute(f'''IF EXISTS (SELECT FROM INFORMATION_SCHEMA.TABLES
           WHERE TABLE_NAME = {tablename})
        BEGIN
            drop table {tablename};
        END

        ELSE

        BEGIN
        CREATE TABLE {tablename} ({query}
             PRIMARY KEY(id));
        End''')
        await connection.close()

    
    async def _get_connection(self):
        connection = await asyncpg.connect(f'postgresql://postgres:akemichan4@localhost/{self.database_name}')
        return connection
    
    async def update_entry(self, tablename, id=None, *,object=None, parameter=None,value=None):
        connection = await self._get_connection()
        entry_id = id
        if object:
            entry_id = object.id
        if await DataHandler.entry_exists(tablename, id=entry_id):
            query=""
            if object:
                query = self._convert_dict_to_string_query(object.to_dict())
            elif index and value:
                if isinstance(value, str):
                    query = f"{index}='{value}'"
                else:
                    query = f"{index}={value}"
            await connection.execute(f'''UPDATE {tablename}
            SET {index}=$1
            WHERE id=$2;''',  parameter, value, entry_id)
            await connection.close()        
        else:
            await connection.close()
            await DataHandler.add_entry(tablename, object.to_dict())

    
    
    async def add_entry(self, tablename, parameters, parameter_length, *args): 
        connection= await self._get_connection()
        #key, value = self._convert_dict_to_keys_and_value_query(dict)
        value=""
        for i in range(parameter_length):
            value=f"{value},${i+1}"
        value=value[1:]
        await connection.execute(f'''INSERT INTO {tablename} ({parameters}) 
            VALUES ({value});''', args)
        await connection.close()
              
    
    async def remove_entry(self, tablename, *, object=None, id=None):
        connection = await self._get_connection()
        entry_id = id
        if object:
            entry_id = object.id
        if await DataHandler.entry_exists(self, tablename, id=entry_id):
            await connection.execute(f'''DELETE FROM {tablename}
            WHERE id=$1;''', entry_id)
            await connection.close()           
        else:
            await connection.close()

    
    
    async def get_entry(self, tablename, id):
        connection = await self._get_connection()
        entry = await connection.fetchrow(f''' SELECT * FROM {tablename} WHERE id=$1;''', id)
        await connection.close()
        return entry
    
    
    async def get_all_where(self, tablename, parameter, condition):
        connection = await self._get_connection()
        """Gets all entries from the table where a certain condition is met. condition must be a valid SQL condition"""
        list = await connection.fetch(f""" SELECT * FROM {tablename} WHERE {parameter}=$1;""", condition)
        await connection.close()
        return list
    
    
    
    async def get_all_data(self, tablename):
        """Gets all entries in the table"""
        connection = await self._get_connection()
        list = await connection.fetch(f"""SELECT * FROM {tablename};""")
        await connection.close()
        return list
    
    
    async def entry_exists(self, tablename, *, object=None, id=None):       
        connection = await self._get_connection()    
        id = id
        if object:
            id = object.id
        TorF= (await connection.execute(f'''SELECT 1
            FROM {tablename}
            WHERE id =$1 LIMIT 1;''', id))
        if TorF=="SELECT 1":
            await connection.close()
            return True
        else:
            await connection.close()
            return False

        
    async def create_table(self, tablename, parameters):
        connection = await self._get_connection()
        await connection.execute(
            f"CREATE TABLE IF NOT EXISTS {tablename} ({parameters});"
        )
        await connection.close()



class StarboardParameterHandler(DataHandler):
    
    async def entry_exists(self, guildId):
        if isinstance(guildId, int):
            return await super().entry_exists(f"starboard_parameters",id=guildId)
            
            
    async def add_entry(self, guildId, channel): 
        connection= await self._get_connection()
        await connection.execute(f'''INSERT INTO starboard_parameters (id, starboard_threshold, starboard_emoji, starboard_channel) 
            VALUES ($1, 3, $2 , $3);''', guildId ,"\u2b50", channel)
        await connection.close()

    async def update_entry(self, guildId, parameter, value):
        connection = await self._get_connection()
        entry_id = guildId
        await connection.execute(f'''UPDATE starboard_parameters
        SET {parameter}=$2
        WHERE id=$1;''',  guildId, value)
        await connection.close()
        
    async def get_entry(self, id):
        return await super().get_entry("starboard_parameters", id)        



class ParameterHandler(DataHandler):
    async def entry_exists(self, guildId):
        if isinstance(guildId, int):
            return await super().entry_exists(f"server_parameters",id=guildId)
            
            
    async def add_entry(self, guildId, channel): 
        connection= await self._get_connection()
        await connection.execute(f'''INSERT INTO server_parameters (id, welcome_channel, welcome_message, command_prefix, language, welcomes) 
            VALUES ($1, $2, $3, $4, $5, $6);''', guildId , channel, "Welcome!", "!", "EN", 0)
        await connection.close()

    async def update_entry(self, guildId, parameter, value):
        connection = await self._get_connection()
        entry_id = guildId
        await connection.execute(f'''UPDATE server_parameters
        SET {parameter}=$2
        WHERE id=$1;''',  guildId, value)
        await connection.close()

    async def increment_entry(self, guildId):
        connection = await self._get_connection()
        if not isinstance(guildId, int):
            return
        await connection.execute(f'''UPDATE server_parameters SET welcomes = welcomes+1 WHERE id=$1;''',guildId)
        await connection.close()        
        
    async def get_entry(self, id):
        return await super().get_entry("server_parameters", id)
        
    
class StarboardHandler(DataHandler):
    def __init__(self):
        super().__init__()
    
    async def get_all_data(self, guildId):
        if isinstance(guildId, int):
            return await super().get_all_data(f"starboard_{guildId}")
            
    async def entry_exists(self, guildId, *, object=None, id=None):
        if isinstance(guildId, int):
            return await super().entry_exists(f"starboard_{guildId}",object=object, id=id)
    
    async def add_entry(self, guildId, object): 
        connection= await self._get_connection()
        await connection.execute(f'''INSERT INTO starboard_{guildId} (id, starboard_message, count, author_id, starboard_channel) 
            VALUES ($1, $2, $3, $4, $5);''', object.id, object.starboard_message, object.count, object.author_id, object.starboard_channel)
        await connection.close()

    async def remove_entry(self, guildId, object):
        if isinstance(guildId, int):
            await super().remove_entry(f"starboard_{guildId}",object=object)

    async def update_entry(self, guildId, object):
        connection = await self._get_connection()
        entry_id = object.id
        if await self.entry_exists(guildId, id=entry_id):
            await connection.execute(f'''UPDATE starboard_{guildId}
            SET starboard_message=$1, count=$2, author_id=$3, starboard_channel=$4
            WHERE id=$5;''',  object.starboard_message, object.count, object.author_id, object.starboard_channel, entry_id)
            await connection.close()        
        else:
            await connection.close()
            await self.add_entry(guildId, object)

    async def get_all_user_and_count(self, guildId):
        connection = await self._get_connection()
        list= await connection.fetch(f'''SELECT author_id, count FROM starboard_{guildId}''')
        await connection.close()
        return list
        
    async def get_entry(self, guildId, id):
        return await super().get_entry(f"starboard_{guildId}", id)

    async def create_table(self, guildId):
        await super().create_table(f"starboard_{guildId}", "id bigint, starboard_message bigint, count bigint, author_id bigint, starboard_channel bigint, PRIMARY KEY(id)") 

class AnalyticsHandler(DataHandler):
    def __init__(self):
        super().__init__()
    
    async def get_all_data(self, guildId):
        if isinstance(guildId, int):
            return await super().get_all_data(f"analytics")
            
    
    async def add_entry(self, guild, type, author_id, channel, stamp): 
        if not isinstance(guild, int):
            return
        connection= await self._get_connection()
        await connection.execute(f'''INSERT INTO analytics (guild, type, author_id, channel, stamp) 
            VALUES ($1, $2, $3, $4, $5);''', guild, type, author_id, channel, stamp)
        await connection.close()
  
    async def get_data_where(self, paramDict):
        pass
    
    async def get_entry(self, guildId, id):
        return await super().get_entry(f"analytics", id)   
            
    async def create_table(self, guildId):
        await super().create_table(f"analytics", "guild bigint, type text, author_id bigint, channel bigint, stamp timestamp")

    async def fetch_all(self, guildId):
        if isinstance(guildId, int):
            connection = await self._get_connection()
            return await connection.fetch(f'''SELECT * FROM analytics WHERE guild={guildId};''')
        else:
            raise TypeError
            
    async def fetch_all_after(self, guildId, after):
        connection = await self._get_connection()
        return await connection.fetch(f'''SELECT * FROM analytics WHERE guild={guildId} AND stamp > $1;''', after)
        
    async def fetch_all_after_for_user(self, guildId, after, id):
        connection = await self._get_connection()
        return await connection.fetch(f'''SELECT * FROM analytics WHERE guild={guildId} AND stamp > $1 AND author_id=$2;''', after, id)

class AnalyticLogs(DataHandler):
    def __init__(self):
        super().__init__()
    
    async def get_all_data(self, guildId):
        if isinstance(guildId, int):
            return await super().get_all_data(f"analyticslog")
            
    async def data_exists(self, guildId, check_time):
        if await self.get_latest_date(guildId, check_time):
            return True
        else:
            return False
    
    async def add_entry(self, guild, author_id, channel, stamp, count): 
        if not isinstance(guild, int):
            return
        connection= await self._get_connection()
        await connection.execute(f'''INSERT INTO analyticslog (guild, author_id, channel, stamp, count) 
            VALUES ($1, $2, $3, $4, $5);''', guild, author_id, channel, stamp, count)
        await connection.close()
  
    async def get_data_where(self, paramDict):
        pass
    
    async def get_entry(self, guildId, id):
        return await super().get_entry(f"analyticslog", id)   
            
    async def create_table(self, guildId):
        await super().create_table(f"analyticslog", "guild bigint, author_id bigint, channel bigint, stamp timestamp, count int")

    async def fetch_all(self, guildId):
        if isinstance(guildId, int):
            connection = await self._get_connection()
            return await connection.fetch(f'''SELECT * FROM analytics WHERE guild={guildId};''')
        else:
            raise TypeError("guildId must be an integer")
            
    async def fetch_all_after(self, guildId, after):
        connection = await self._get_connection()
        return await connection.fetch(f'''SELECT * FROM analyticslog WHERE guild=$2 AND stamp >= $1;''', after, guildId)
        
    async def fetch_all_after_for_user(self, guildId, after, id):
        connection = await self._get_connection()
        return await connection.fetch(f'''SELECT * FROM analyticslog WHERE guild=$3 AND stamp >= $1 AND author_id=$2;''', after, id, guildId)

    async def get_earliest_date(self, guildId, after):
        connection = await self._get_connection()
        result= await connection.fetch(f'''SELECT * FROM analyticslog WHERE guild=$2 AND stamp >= $1 ORDER BY stamp asc LIMIT 1;''', after,  guildId)
        await connection.close()
        return result

    async def get_latest_date(self, guildId, before):
        connection = await self._get_connection()
        result= await connection.fetch(f'''SELECT * FROM analyticslog WHERE guild=$2 AND stamp <= $1 ORDER BY stamp desc LIMIT 1;''', before,  guildId)
        await connection.close()
        return result

    async def entry_exists(self, author, channel, stamp):       
        connection = await self._get_connection()
        TorF= (await connection.execute(f'''SELECT 1
            FROM analyticslog
            WHERE channel = $2 AND stamp = $3 AND author_id = $1;''', author, channel, stamp))
        if TorF=="SELECT 1":
            await connection.close()
            return True
        else:
            await connection.close()
            return False
        
    async def save_entry(self, guildId, channel, author, stamp, count):
        connection = await self._get_connection()
        if await self.entry_exists(author, channel, stamp):
            await connection.execute(f'''UPDATE analyticslog SET count = count+{count} WHERE author_id=$1 AND stamp=$2 AND channel=$3;''', author, stamp, channel)
        else:
            await self.add_entry(guildId, author, channel, stamp, count)
        await connection.close()        
    
    async def cleanup(self, after, converter):
        connection = await self._get_connection()
        results = await connection.fetch(f'''SELECT * FROM analyticslog WHERE stamp>=$1''', after)
        for record in results:
            new_record = converter(record["stamp"])
            if str(new_record) != str(record["stamp"]):
                await connection.execute(f'''DELETE FROM analyticslog WHERE stamp=$1 AND author_id=$2 AND channel=$3''', record["stamp"], record["author_id"], record["channel"])
                await self.save_entry(record["guild"], record["channel"], record["author_id"], record["stamp"], record["count"])

class VoiceAnalyticsHandler(DataHandler):
    def __init__(self):
        super().__init__()
    
    async def get_all_data(self, guildId):
        if isinstance(guildId, int):
            return await super().get_all_data(f"voiceanalytics")
            
    
    async def add_entry(self, guild, author_id, channel, stamp, duration): 
        if not isinstance(guild, int):
            return
        connection= await self._get_connection()
        await connection.execute(f'''INSERT INTO voiceanalytics (guild,  author_id, channel, stamp, duration) 
            VALUES ($1, $2, $3, $4, $5);''', guild, author_id, channel, stamp, duration)
        await connection.close()
  
    async def get_data_where(self, paramDict):
        pass
    
    async def get_entry(self, guildId, id):
        return await super().get_entry(f"voiceanalytics", id)   
            
    async def create_table(self, guildId):
        await super().create_table(f"voiceanalytics", "guild bigint, author_id bigint, channel bigint, stamp timestamp, duration int")

    async def fetch_all(self, guildId):
        if isinstance(guildId, int):
            connection = await self._get_connection()
            return await connection.fetch(f'''SELECT * FROM voiceanalytics WHERE guild={guildId};''')
        else:
            raise TypeError
 
    async def fetch_all_after(self, guildId, after):
        connection = await self._get_connection()
        return await connection.fetch(f'''SELECT * FROM voiceanalytics WHERE guild={guildId} AND stamp > $1;''', after)


    async def fetch_all_after_for_user(self, guildId, after, id):
        connection = await self._get_connection()
        return await connection.fetch(f'''SELECT * FROM voiceanalytics WHERE guild={guildId} AND stamp > $1 AND author_id=$2;''', after, id)


class LogHandler(DataHandler):
    def __init__(self):
        super().__init__()
    
    async def get_all_data(self, guildId):
        if isinstance(guildId, int):
            return await super().get_all_data(f"logs_{guildId}")
            
    async def entry_exists(self, guildId, id):
        if isinstance(guildId, int):
            return await super().entry_exists(f"logs_{guildId}", id=id)
    
    async def add_entry(self, guildId, type, author, author_id, content, channel, stamp): 
        if not isinstance(guildId, int):
            return
        connection= await self._get_connection()
        await connection.execute(f'''INSERT INTO logs_{guildId} (type, author, author_id, content, channel, datetime) 
            VALUES ($1, $2, $3, $4, $5, $6);''', type, author, author_id, content, channel, datetime)
        await connection.close()

    async def fetch_and_delete(self, guildId):
        list = await connection.fetch(f'''SELECT * FROM logs_{guildId}''')
        await connection.execute(f'''DELETE * FROM logs_{guildId}''')
        return list
        
        
    async def fetch_all(self, guildId):
        list = await connection.fetch(f'''SELECT * FROM logs_{guildId}''')
        return list
            
    async def create_table(self, guildId):
        await super().create_table(f"log_{guildId}", "text type, text author, bigint author_id, text content, text channel, datetime datetime")

            
class LinkHandler(DataHandler):
    def __init__(self):
        super().__init__()
    
    async def get_all_data(self, guildId):
        if isinstance(guildId, int):
            return await super().get_all_data(f"links_{guildId}")
            
    async def entry_exists(self, guildId, *, object=None, id=None):
        if isinstance(guildId, int):
            return await super().entry_exists(f"links_{guildId}",object=object, id=id)
        else:
            return False
            
    async def tag_exists(self, guildId, tag):
        connection = await self._get_connection()    
        TorF= await connection.fetch(f'''SELECT 1
            FROM links_{guildId}
            WHERE tag=$1 LIMIT 1;''', tag)
        if len(TorF)== 1:
            await connection.close()
            return TorF
        else:
            await connection.close()
            return False    
    
    async def get_id_of_tag(self, guildId, tag):
        connection = await self._get_connection()    
        id= await connection.fetch(f'''SELECT *
            FROM links_{guildId}
            WHERE tag=$1;''', tag)
        await connection.close()
        return id
        
    
    async def add_entry(self, guildId, object): 
        connection= await self._get_connection()
        await connection.execute(f'''INSERT INTO links_{guildId} (id, tag, owner) 
            VALUES ($1, $2, $3);''', object.id, object.tag, object.owner)
        await connection.close()

    async def remove_entry(self, guildId, object):
        if isinstance(guildId, int):
            await super().remove_entry(f"links_{guildId}", object=object)

    async def update_entry(self, guildId, object):
        connection = await self._get_connection()
        if await self.entry_exists(guildId, id=id):
            await connection.execute(f'''UPDATE links_{guildId}
            SET tag=$2, owner=$3
            WHERE id=$1;''', object.id, object.tag, object.owner)
            await connection.close()
        else:
            await connection.close()
            await self.add_entry(guildId, object)
    
    async def get_entry(self, guildId, id):
        return await super().get_entry(f"links_{guildId}", id)
        
        
    async def create_table(self, guildId):
        await super().create_table(f"links_{guildId}", "id text, tag text, owner bigint, PRIMARY KEY(id)")
        
class FortuneHandler(DataHandler):

    def __init__(self):
        super().__init__()
    
    async def get_all_data(self):
        return await super().get_all_data(f"fortune")
            
    async def entry_exists(self, *, object=None, id=None):
        return await super().entry_exists(f"fortune",object=object, id=id)

    async def check_with_multiple_conditions(self, **kwargs):
        prep_string = ""
        for key in (kwargs):
            prep_string = f"{prep_string} and {key}={kwargs[key]}"
        prep_string = prep_string[5:]
        query = f""" SELECT * FROM fortune WHERE {prep_string}"""
        connection = await self._get_connection()
        list =  await connection.fetch(query)
        return list
        

    async def add_entry(self, guildId, object): 
        connection= await self._get_connection()
        await connection.execute(f'''INSERT INTO fortune (id, date, luck, description, type) 
            VALUES ($1, $2, $3, $4, $5);''', object.author, object.date, object.luck, object.description, object.type)
        await connection.close()

    async def remove_entry(self, guildId, object):
        if isinstance(guildId, int):
            await super().remove_entry(f"fortune", object=object)

    
    async def get_entry(self, guildId, id):
        return await super().get_entry(f"fortune", id)
        
        
    async def create_table(self, guildId):
        await super().create_table(f"fortune", "id text, tag text, owner bigint, PRIMARY KEY(id)")
        
        
        
class ReactionRoleHandler(DataHandler):
    def __init__(self):
        super().__init__()
        
    async def get_all_data(self, guildId):
        return await super().get_all_data(f"reactionrole_{guildId}")
        
    async def add_entry(self, guildId, object):
        connection = await self._get_connection()
        await connection.execute(f'''INSERT INTO reactionrole_{guildId} (role, reaction) VALUES ($1, $2);''', object.role, object.reaction)
        await connection.close()
        
    async def remove_entry(self, guildId, role):
        if isinstance(guildId, int):
            connection = await self._get_connection()
            await connection.execute(f'''DELETE FROM reactionrole_{guildId}
            WHERE role=$1;''', role)
            
            
    async def get_entry(self, guildId, id):
        return await super().get_entry(f"reactionrole_{guildId}", id)
        
        
    async def create_table(self, guildId):
        await super().create_table(f"reactionrole_{guildId}", "role bigint, reaction text, PRIMARY KEY(role)")
        
        
    async def update_entry(self, guildId, object):
        connection = await self._get_connection()
        entry_id = guildId
        await connection.execute(f'''UPDATE reactionrole_{guildId}
        SET reaction=$2
        WHERE role=$1;''',  object.role, object.reaction)
        await connection.close()
        
    async def entry_exists(self, guildId, role):       
        connection = await self._get_connection()    
        TorF= (await connection.execute(f'''SELECT 1
            FROM reactionrole_{guildId}
            WHERE role =$1 LIMIT 1;''', role))
        if TorF=="SELECT 1":
            await connection.close()
            return True
        else:
            await connection.close()
            return False        
        
    async def value_exists(self, guildId, reaction):       
        connection = await self._get_connection()    
        TorF= (await connection.execute(f'''SELECT 1
            FROM reactionrole_{guildId}
            WHERE reaction =$1 LIMIT 1;''', reaction))
        if TorF=="SELECT 1":
            await connection.close()
            return True
        else:
            await connection.close()
            return False
        