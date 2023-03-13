import discord, datetime, re
from dateutil.parser import parse

endpoint = "server.votes"
class Votes:
    def __init__(self, redis):
        self.connector = redis
        
    def _format(self, attribute):
       return f"{endpoint}.{attribute}" 
    def _parent(self):
        return f"{endpoint}"


    async def store_election_event(self, election_info: dict, guild_id:int):
        return await self.connector.store(self._format((guild_id)),election_info)
    
    async def get_election_event(self, guild_id:int):
        data = await self.connector.get(self._format(guild_id))
        data['vote_start_date'] = parse(data['vote_start_date'])
        data['vote_end_date'] = parse(data['vote_end_date'])
        data['registration_start_date'] = parse(data['registration_start_date'])
        data['registration_end_date'] = parse(data['registration_end_date'])        
        return data
    
    async def find_candidate(self, guild_id:int, user_id:int):
        election = await self.get_election_event(guild_id)
        
        for position in election['open_positions']:
            for candidate in position['candidates']:
                if candidate['id'] == user_id:
                    candidate['position_title'] = position['title']
                    return candidate
        return None
    
    async def add_candidate(self, guild_id:int, user_id:int, real_name:str, position_slug:str, qualifications:str, platform:str):
        ## check if candidate already exists
        candidate = await self.find_candidate(guild_id, user_id)
        if candidate is not None: return False

        ## get election info
        election = await self.get_election_event(guild_id)

        candidate = {
            'id':user_id,
            'real_name':re.sub(r'[^\w\s]', '', real_name),
            'register_time':datetime.datetime.now(),
            'votes':[],
            'position':position_slug,
            'platform':platform,
            'qualifications':qualifications
        }

        for position in election['open_positions']:
            if position['slug'] == position_slug:
                position['candidates'].append(candidate)
                await self.store_election_event(election, guild_id)
                return True
        return False
    async def add_vote_to_candidate(self, guild_id:int, user_id:int, candidate_id:int):
        ## find candidate and increase vote by one
        election = await self.get_election_event(guild_id)
        for position in election['open_positions']:
            for candidate in position['candidates']:
                if candidate['id'] == candidate_id:
                    if not isinstance(candidate['votes'], list):
                        candidate['votes'] = []
                    #candidate['votes'] += 1
                    ## ensure you can't for same user twice
                    if user_id not in candidate['votes']:
                        candidate['votes'].append(user_id)
    
        ## add user to list of people who have voted
        if not user_id in election['voting_users']:
            election['voting_users'].append(user_id)
        return await self.store_election_event(election, guild_id)     


    async def remove_candidate(self, guild_id:int, user_id:int):
        candidate = await self.find_candidate(guild_id, user_id)
        if not candidate: return False

        election = await self.get_election_event(guild_id)
        for position in election['open_positions']:
            for candidate in position['candidates']:
                if candidate['id'] == user_id:
                    position['candidates'].pop(position['candidates'].index(candidate))
        
        return await self.store_election_event(election, guild_id)


    async def update_candidate(self, guild_id:int, user_id:int, real_name:str, qualifications:str, platform:str):
        election = await self.get_election_event(guild_id)
        
        for position in election['open_positions']:
            for candidate in position['candidates']:
                if candidate['id'] == user_id:
                    candidate['qualifications'] = qualifications
                    candidate['platform'] = platform
                    candidate['real_name'] = re.sub(r'[^\w\s]', '', real_name)

        await self.store_election_event(election, guild_id)      

    async def get_ordered_votes(self, guild_id):
        ## get election info
        election = await self.get_election_event(guild_id)

        for position in election['open_positions']:
            ordered_list = sorted(position['candidates'], key=lambda d:len(d['votes']),reverse=True)
            position['candidates'] = ordered_list
        
        return election

    async def store_user_votes(self, guild_id:int, user_id: int, candidate_id:int, position_title:str, position_slug:str):
        new_vote = {
            'position_title':position_title,
            'position_slug':position_slug,
            'id':user_id,
            'candidate_id':candidate_id
        }
        user_votes = await self.get_user_votes(guild_id, user_id)
        if user_votes is None:
            user_votes = []
        
        user_votes.append(new_vote)
        await self.connector.store(self._format(f"{guild_id}.{user_id}"), user_votes)
    async def get_user_votes(self,guild_id,user_id):
        #data = await self.connector.get(self._format(f"{guild_id}.{user_id}"))
        #return data
        user_votes = []
        election = await self.get_election_event(guild_id)
        for position in election['open_positions']:
            for candidate in position['candidates']:
                if user_id in candidate['votes']:
                    vote = {
                        'candidate_id':candidate['id'],
                        'position_title':position['title']
                    }
                    user_votes.append(vote)
        
        if len(user_votes) > 0: return user_votes
        else: return None

    async def remove_user_votes(self, guild_id:int, user_id:int):
        return await self.connector.delete(self._format(f"{guild_id}.{user_id}"))
    
    async def delete_user_votes(self, guild_id: int, user_id:int):
        ## get election info
        election = await self.get_election_event(guild_id)
        if not user_id in election['voting_users']: return False

        #user_votes = await self.get_user_votes(guild_id, user_id)
        #if user_votes is None: return False

        for position in election['open_positions']:
            for candidate in position['candidates']:
                # for vote in user_votes:
                #     if vote['candidate_id'] == candidate['id']:
                #         candidate['votes'] -= 1
                if user_id in candidate['votes']:
                    candidate['votes'].pop(candidate['votes'].index(user_id))
                
        ## remove that user has voted
        if user_id in election['voting_users']:
            election['voting_users'].pop(election['voting_users'].index(user_id))
        ## remove user votes
        await self.connector.delete(self._format(f"{guild_id}.{user_id}"))
        ## store new election
        return await self.store_election_event(election, guild_id)