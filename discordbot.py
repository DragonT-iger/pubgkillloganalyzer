import discord, asyncio
from discord import app_commands
from discord.ext import commands
from enum import Enum


import requests
import json
import os
from datetime import datetime, timedelta

################################################################################################


# PUBG API json데이터에서 id는 식별자의 의미처럼 사용되므로 name이랑 혼동하지 않도록 주의 할 것


## 전역변수



# string
API_KEY = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiIxMWRlNGJiMC1mZTFjLTAxM2ItODI3Ny00MmY3ZTdiY2Q3MWIiLCJpc3MiOiJnYW1lbG9ja2VyIiwiaWF0IjoxNjg4NjQyMDEzLCJwdWIiOiJibHVlaG9sZSIsInRpdGxlIjoicHViZyIsImFwcCI6Ii1jYWNmZTRkOS01ZDc0LTQxNGQtYTViNi0xZTFlODA2YjRiMDUifQ.tj5njHUXJvUsR850EFswKj2j36hwbkP-RzhN9YCbqbY' # 여기에 PUBG API 키를 넣으세요.
PLATFORM = 'kakao' # 플랫폼을 설정하세요. 예: steam, kakao, xbox, psn 등



PLAYER_JSON_DIR = 'player_json' # 플레이어의 json 파일을 저장할 폴더를 지정하세요.
MATCH_JSON_DIR = 'match_json' # 매치의 json 파일을 저장할 폴더를 지정하세요.


USER_ID = 'baboyeji'
# int

REFRESH_PLAYER_DATA_CYCLE = 1200 # player_data를 새로고침할 주기 (api 요청 횟수를 줄이기 위함)
REFRESH_UNKNOWN_PLAYER_DATA_CYCLE = 3600




#float
UTC_PLUS_HOURS = 0



# const
RANDOM_SQUAD = 0
MERCENARY = 1
SOMETIMES_SAME_TEAM = 2
OFTEN_SAME_TEAM = 3
FIXED_TEAM = 4
UNKNOWN = -1

MATCH_REPETITIONS = 50


# dict
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/vnd.api+json"
}

## 함수

# 플레이어의 json 파일을 저장하는 함수
# player_json에서는저장하는 시간에대한 정보가 없기 때문에 시간을 같이 저장하도록 수정
# 저장함수에서 조심해야 할것은 저장할때 json이 있는지 검사하는 로직이 없음 덮어 씌워지는것을 고려 잘해야함



# 플레이어의 json 파일을 저장할 수 있는지 검사하는 함수

#json 파일이 존재하는지 검사
def current_time_utc():
    return datetime.utcnow() + timedelta(hours=UTC_PLUS_HOURS)


# 대소문자 구분없이 파일을 찾는 함수
def find_case_insensitive_path(dir_path, target_filename): 
    lowercase_target = target_filename.lower()
    for filename in os.listdir(dir_path):
        if filename.lower() == lowercase_target:
            # print(os.path.join(dir_path, filename))
            return os.path.join(dir_path, filename)
    print("경고! 파일이 존재하지 않습니다.")
    return None

# 경로의 파일 이름의 대소문자를 구별해서 존재하는지 검사하는 함수

def file_exists_case_sensitive(dir_path, target_filename):
    for filename in os.listdir(dir_path):
        if filename == target_filename:  # case-sensitive comparison
            return True
    return False

def is_file_error(player_name):
    # json을 exist검사
    if(not os.path.exists(os.path.join(PLAYER_JSON_DIR, f'{player_name}.json'))):
        return True

    path = find_case_insensitive_path(PLAYER_JSON_DIR, f'{player_name}.json')
    with open(path) as f:
        json_data = json.load(f)
        if 'errors' in json_data:
            return True
        
        return False

#대소문자 구분해야함
def isCanSavePlayerJson(player_name):
    
    is_exists = os.path.exists(os.path.join(PLAYER_JSON_DIR, f'{player_name}.json'))
    is_sensitive_exists = file_exists_case_sensitive(PLAYER_JSON_DIR, f'{player_name}.json')

    is_case_not_sensitive = is_exists and not is_sensitive_exists

    #json파일이 error 파일일 경우 iserror = True

    #open player_json
        

    if(is_case_not_sensitive):
        if(is_file_error(player_name)):
            os.remove(os.path.join(PLAYER_JSON_DIR, f'{player_name}.json'))
            print(f"{player_name}의 json파일이 존재하지만 대소문자가 다르고 에러파일이므로 삭제하고 다시 저장합니다.")
            return True
        else:
            print(f"{player_name}의 json파일이 존재하지만 대소문자가 다르므로 저장하지 않습니다.")
            return False
    
    if(os.path.exists(os.path.join(PLAYER_JSON_DIR, f'{player_name}.json'))):
        utc = current_time_utc()
        
        player_json_path = find_case_insensitive_path(PLAYER_JSON_DIR , f'{player_name}.json')

        with open(player_json_path) as f:
            json_data = json.load(f)


            if 'errors' in json_data:

                createAt = json_data['errors'][0]['createdAt']
                createAt = datetime.strptime(createAt, '%Y-%m-%dT%H:%M:%SZ')  # Convert string to datetime

                if((utc - createAt).seconds < REFRESH_UNKNOWN_PLAYER_DATA_CYCLE):
                    # print(f"{player_name}의 데이터는 {REFRESH_UNKNOWN_PLAYER_DATA_CYCLE}초 이내에 갱신되었으므로 갱신할 필요가 없습니다.")
                    return False
                return True

            if(json_data['data'][0]['id'].startswith('ai')):
                print(f"{player_name}의 데이터는 존재하지만 ai이므로 갱신할 필요가 없습니다.")
                return False

            createdAt_str = json_data['data'][0]['attributes']['createdAt']
            createdAt = datetime.strptime(createdAt_str, '%Y-%m-%dT%H:%M:%SZ')  # Convert string to datetime
        
        if((utc - createdAt).seconds < REFRESH_PLAYER_DATA_CYCLE):
            print(f"{player_name}의 데이터는 {REFRESH_PLAYER_DATA_CYCLE}초 이내에 갱신되었으므로 갱신할 필요가 없습니다.")
            return False 
        else:
            print(f"{player_name}의 데이터는 {REFRESH_PLAYER_DATA_CYCLE}초 이상이므로 갱신할 필요가 있습니다.")
            return True
    else:
        print(f"{player_name}의 데이터는 존재하지 않으므로 갱신할 필요가 있습니다.")
        return True

# 플레이어의 json 파일을 저장하는 함수
def save_player_json(player_name):
    if(isCanSavePlayerJson(player_name)):
        utc = current_time_utc()
        
        player_matches_url = f"https://api.pubg.com/shards/{PLATFORM}/players?filter[playerNames]={player_name}"
        response = requests.get(player_matches_url, headers=HEADERS)

        print("API 호출 1회")
        json_player_data = response.json()



        #response가 200이 아니면
        if(response.status_code != 200):
            print(f"ERROR {response.status_code}")
            
            if(is_file_error(player_name) == False):
                # 파일을 load한다
                with open(os.path.join(PLAYER_JSON_DIR, f'{player_name}.json')) as f:
                    json_data = json.load(f)
                    return json_data
            else:
                json_error_data = response.json()
                json_error_data['errors'][0]['createdAt'] = utc.strftime('%Y-%m-%dT%H:%M:%SZ')

                with open(os.path.join(PLAYER_JSON_DIR, f'{player_name}.json'), 'w') as outfile:
                    json.dump(json_error_data, outfile, indent=4)
                return response.status_code

        
        
        #만약 data id가 ai로 시작하면

        


        if(json_player_data['data'][0]['id'].startswith('ai')):
            json_player_data['data'][0]['attributes']['createdAt'] = utc.strftime('%Y-%m-%dT%H:%M:%SZ')

            with open(os.path.join(PLAYER_JSON_DIR, f'{player_name}.json'), 'w') as outfile:
                json.dump(json_player_data, outfile, indent=4)

            print("100% 봇임")
            return None
        

        json_player_data['data'][0]['attributes']['createdAt'] = utc.strftime('%Y-%m-%dT%H:%M:%SZ')

        with open(os.path.join(PLAYER_JSON_DIR, f'{player_name}.json'), 'w') as outfile:
            json.dump(json_player_data, outfile, indent=4)
        
        return json_player_data
    else:
        with open(os.path.join(PLAYER_JSON_DIR, f'{player_name}.json')) as json_file:
            json_data = json.load(json_file)

        

        if 'errors' in json_data:
            
            error = json_data['errors'][0]['title']

            if(error == "Not Found"):
                # print("플레이어가 존재하지 않습니다.")
                return 404
            elif(error == "Too Many Requests"):
                # print("API 호출 횟수를 초과하였습니다.")
                return 429

        if(json_data['data'][0]['id'].startswith('ai')):
            print("봇임")
            return None
        
        return json_data
    

        
    



# match json 파일을 저장할 수 있는지 검사하는 함수
def isCanSaveMatchJson(match_id):
    if(os.path.exists(os.path.join(MATCH_JSON_DIR, f"{match_id}.json"))):
        # print(f"{match_id}라는 match 데이터는 이미 존재합니다.")
        return False
    else:
        return True

# match json 파일을 저장하는 함수
def save_match_json(match_id):
    if(isCanSaveMatchJson(match_id)):
        url = f"https://api.pubg.com/shards/{PLATFORM}/matches/{match_id}"
        response = requests.get(url, headers=HEADERS)

        if(response.status_code == 429):
            print("WARNING Too many requests")

        with open(os.path.join(MATCH_JSON_DIR, f"{match_id}.json"), 'w') as outfile:
            json.dump(response.json(), outfile, indent=4)

        
        

# match json 파일을 불러오는 함수
def load_match_json(match_id):
    with open(os.path.join(MATCH_JSON_DIR, f"{match_id}.json")) as json_file:
        json_data = json.load(json_file)
    return json_data

def get_team_info(name , match_id):

    save_match_json(match_id)
    
    
    json_match_data = load_match_json(match_id)
    
    team_name = [] # 팀 닉네임
    team_id = [] # 팀 아이디 식별자
    team_player_id = [] # 아이디 식별자
    game_createdAt = '' # 게임 생성 시간

    user_id = name

    for included in json_match_data['included']:
        if included['type'] == 'participant' and included['attributes']['stats']['name'].lower() == user_id.lower():
            participant_id = included['id']
            # print(f'Participant ID: {participant_id}')
            for included in json_match_data['included']:
                if included['type'] == 'roster':
                    for participant in included['relationships']['participants']['data']:
                        if(participant['id'] == participant_id):
                            for other_participant in included['relationships']['participants']['data']:
                                team_id.append(other_participant['id'])
            # print(f'Team ID: {team_id}')

            for included in json_match_data['included']:
                if included['type'] == 'participant':
                    for id in team_id:
                        if included['id'] == id:
                            team_name.append(included['attributes']['stats']['name'])
                            team_player_id.append(included['attributes']['stats']['playerId'])

            game_createdAt = json_match_data['data']['attributes']['createdAt']
            # print(f'Team Name: {team_name}')
            # print(f'player_id: {team_player_id}')
            # print(f'Game Created At: {game_createdAt}')
    
    return team_name, team_player_id , game_createdAt

def get_matches_from_player_name(player_name):
    
    json_player_data = save_player_json(player_name)

    if(json_player_data == None):
        return None
    if(json_player_data == 404):
        return 404
    if(json_player_data == 429):
        return 429

    match_id_list = []
    for match in json_player_data['data'][0]['relationships']['matches']['data']:
        match_id_list.append(match['id'])
    return match_id_list


# 플레이어의 최근 매치 n개를 불러와서 팀 정보를 반환하는 함수
# 다른 매치인 경우에는 구분할 수 있게 저장해야함
# team_name_list만 있으면됨
# 생각보다 부하가 많은 작업
def get_recent_team_info_from_player_name(player_name, n):

    
    json_player_data = save_player_json(player_name)

    if(json_player_data == None):
        return None
    if(json_player_data == 404):
        return 404
    if(json_player_data == 429):
        return 429

    match_id_list = []
    for match in json_player_data['data'][0]['relationships']['matches']['data']:
        match_id_list.append(match['id'])
    match_id_list = match_id_list[:n]

    team_name_list = []

    for match_id in match_id_list:
        team_name, _ , _ = get_team_info(player_name, match_id)
        team_name_list.append(team_name)

    return team_name_list

def get_clan_tag_from_player_name(player_name):
    
    json_player_data = save_player_json(player_name)

    if(json_player_data == None):
        return None
    if(json_player_data == 404):
        return 404
    if(json_player_data == 429):
        return 429

    clan_tag = json_player_data['data'][0]['attributes']['clanTag']
    return clan_tag

#연속으로 몇 매치동안 "player_name"의 팀원들이 팀이였는지 확인하는 코드
def get_team_recent_count_from_player_name(player_name, n):

    team_name_list = get_recent_team_info_from_player_name(player_name, n)

    if(team_name_list == None):
        return None
    if(team_name_list == 404):
        return 404
    if(team_name_list == 429):
        return 429

    matches = get_matches_from_player_name(player_name)
    #get team info

    

    team_name0, _ , _ = get_team_info(player_name, matches[0])

    team_name1 , _  , _ = get_team_info(player_name, matches[1])

    team_name2 , _ , _ = get_team_info(player_name, matches[2])

    team_names = team_name0 + team_name1 + team_name2

    name_dict = {}
    for name in team_names:
        lower_name = name.lower()
        if lower_name not in name_dict:
            name_dict[lower_name] = name

    # also convert player name to lowercase before discarding
    player_name_lower = player_name.lower()
    if player_name_lower in name_dict:
        del name_dict[player_name_lower]

    team_name = list(name_dict.values())

    count_list = {}


    #count에 시간이 만약 2시간 이상 차이나면 break
    
    for elements in team_name:
        count = 0
        for sublist in team_name_list:
            if(elements in sublist):
                count += 1
            else:
                break
        count_list[elements] = count

    # print(count_list)

    # for team in team_name:
        # print(f"{player_name}의 팀원 {team}와 {count_list[team]}번 연속으로 팀이였습니다.")

    
    return count_list

#몇 매치동안 "player_name"의 팀원들이 팀이였는지 확인하는 코드
def get_team_count_from_player_name(player_name, n):

    team_name_list = get_recent_team_info_from_player_name(player_name, n)

    if(team_name_list == None):
        return None
    if(team_name_list == 404):
        return 404
    if(team_name_list == 429):
        return 429
    
    matches = get_matches_from_player_name(player_name)
    #get team info

    team_name0, _ , _ = get_team_info(player_name, matches[0])

    team_name1 , _  , _ = get_team_info(player_name, matches[1])

    team_name2 , _ , _ = get_team_info(player_name, matches[2])

    team_names = team_name0 + team_name1 + team_name2

    name_dict = {}
    for name in team_names:
        lower_name = name.lower()
        if lower_name not in name_dict:
            name_dict[lower_name] = name

    # also convert player name to lowercase before discarding
    player_name_lower = player_name.lower()
    if player_name_lower in name_dict:
        del name_dict[player_name_lower]

    team_name = list(name_dict.values())

    count_list = {}


    #count에 시간이 만약 2시간 이상 차이나면 break
    
    for elements in team_name:
        count = 0
        for sublist in team_name_list:
            if(elements in sublist):
                count += 1
        count_list[elements] = count

        
    # print(count_list)

    # for team in team_name:
        # print(f"{player_name}의 팀원 {team}와 {count_list[team]}번 연속으로 팀이였습니다.")

    
    return count_list

#클랜 태그를 반환하는 함수
def get_clan_id_from_name(name):
    json_player_data = save_player_json(name)

    if(json_player_data == None):
        return None
    if(json_player_data == 404):
        return 404
    if(json_player_data == 429):
        return 429
    
    clan_id = json_player_data['data'][0]['attributes']['clanId']
    return clan_id
#가장 최근 매치에서 시간이 얼마나 흘렀는지 반환하는 함수

def get_recent_match_time(player_name):
    json_player_data = save_player_json(player_name)

    if(json_player_data == None):
        return None
    if(json_player_data == 404):
        return 404
    if(json_player_data == 429):
        return 429

    recent_match = json_player_data['data'][0]['relationships']['matches']['data'][0]['id']
    json_match_data = load_match_json(recent_match)
    game_createdAt = json_match_data['data']['attributes']['createdAt']
    game_createdAt = datetime.strptime(game_createdAt, '%Y-%m-%dT%H:%M:%SZ')
    now = current_time_utc()
    return now - game_createdAt

def analyze_player(player_name):
    matches = get_matches_from_player_name(player_name)

    if(matches == None): # 봇
        return None
    if(matches == 404): # 404
        return 404
    if(matches == 429): # 429
        return 429
    if(len(matches) == 0): # 매치가 없음
        return 0
    

    providedMatchCount = len(matches)



    targetMatchCount = MATCH_REPETITIONS
    totalMatch = targetMatchCount if providedMatchCount > targetMatchCount else providedMatchCount

    
    
    # dict 값임
    consecutivePlaydict = get_team_recent_count_from_player_name(player_name,totalMatch)
    totalPlaydict = get_team_count_from_player_name(player_name,totalMatch)

    # 만약 두 dict의 key에 대한 value값이 같다면 isMercenary = True

   

    # 숫자 값

    recent_time = get_recent_match_time(player_name).seconds

    teamcount_in3match = len(consecutivePlaydict)


    playingmethod = UNKNOWN # 0은 랜덤 스쿼드, 1은 용병 , 2는 가끔 같은 팀 , 3은 자주 같은 팀, 4는 고정팀
    low_probability_team = []
    high_probability_team = []

  

    flag = True
    if(teamcount_in3match <= 7):
        for key, value in totalPlaydict.items():
            if(value >= totalMatch * 0.8 or (recent_time < 3600 and consecutivePlaydict[key] >= 1 and value >= totalMatch * 0.3)):
                high_probability_team.append(key)
                if(value >= totalMatch * 0.8):
                    playingmethod = FIXED_TEAM
                
            elif(value >= totalMatch * 0.4 or (recent_time < 3600 and consecutivePlaydict[key] >= 1 )):
                low_probability_team.append(key)
                if(playingmethod == UNKNOWN):
                    if playingmethod < OFTEN_SAME_TEAM and value >= totalMatch * 0.6:
                        playingmethod = OFTEN_SAME_TEAM
                    elif playingmethod < SOMETIMES_SAME_TEAM and value >= totalMatch * 0.4:
                        playingmethod = SOMETIMES_SAME_TEAM
                    elif playingmethod < MERCENARY:
                        playingmethod = MERCENARY
            
    else:
        flag = False

        for value in consecutivePlaydict.values():
            if(value >= totalMatch * 0.3):
                flag = True
                break

        if(flag == False):
            playingmethod = RANDOM_SQUAD
        
   
        
    return {
    "playingmethod": playingmethod,
    "low_probability_team": low_probability_team,
    "high_probability_team": high_probability_team,
    }


###########################

# discord

###########################


SERVER_ID = 1127695613048389763
# SERVER_ID = 480315799857528853
CLIENT_ID = 1127694844207321150
TOKEN = "MTEyNzY5NDg0NDIwNzMyMTE1MA.G9p00n.d8hSMN-uZ2wuRu0SpwB0VD3yHr30SujOc4Dw_4"



# This will load the permissions the bot has been granted in the previous configuration
intents = discord.Intents.default()
intents.message_content = True

class aclient(discord.Client):
  def __init__(self):
    super().__init__(intents = intents)
    self.synced = False # added to make sure that the command tree will be synced only once
    self.added = False

  async def on_ready(self):
    await self.wait_until_ready()
    if not self.synced: #check if slash commands have been synced 
      await tree.sync() #guild specific: you can leave sync() blank to make it global. But it can take up to 24 hours, so test it in a specific guild.
      self.synced = True
    if not self.added:
      self.added = True
    print(f"Say hi to {self.user}!")




client = aclient()
tree = discord.app_commands.CommandTree(client)

# @tree.command(description='Respond hello to you.', guild=discord.Object(f'{SERVER_ID}'))
# async def greet(interaction: discord.Interaction):
#   await interaction.response.send_message('Hello!')


# @tree.command(description='Respond hello to you and mention yout user.', guild=discord.Object(f'{SERVER_ID}'))
# async def greet_user(interaction: discord.Interaction):
#   user = interaction.user.id
#   await interaction.response.send_message(f'Hello, <@{user}>!')

# GreetingTime = Enum(value='GreetingTime', names=['MORNING', 'AFTERNOON', 'EVENING', 'NIGHT'])

# @tree.command(description='Respond according to the period of the day.', guild=discord.Object(f'{SERVER_ID}'))
# @discord.app_commands.describe(period='Period of the day')
# async def greet_user_time_of_the_day(interaction: discord.Interaction, period: GreetingTime):
#   user = interaction.user.id
#   if period.name == 'MORNING':
#     await interaction.response.send_message(f'Good Morning, <@{user}>!')
#     return
#   if period.name == 'AFTERNOON':
#     await interaction.response.send_message(f'Good Afternoon, <@{user}>!')
#     return
#   if period.name == 'EVENING':
#     await interaction.response.send_message(f'Good Evening, <@{user}>!')
#     return
#   if period.name == 'NIGHT':
#     await interaction.response.send_message(f'Have a good night, <@{user}>!')
#     return

# # 플레이어 이름을 입력하면 플레이어의 가장 최근 팀원들을 반환하는 명령어
# @tree.command(description='팀원들의 이름을 반환합니다.', guild=discord.Object(f'{SERVER_ID}'))
# @discord.app_commands.describe(player_name='플레이어 이름')
# async def get_team(interaction: discord.Interaction, player_name: str):
#     matches = get_matches_from_player_name(player_name)
#     if(matches == None):
#         await interaction.response.send_message(f'플레이어 {player_name}는 ai입니다.')
#         return
#     if(matches == 404):
#         await interaction.response.send_message(f'플레이어 {player_name}을 찾을 수 없습니다.')
#         return
#     if(len(matches) == 0):
#         await interaction.response.send_message(f'플레이어 {player_name}의 최근 매치가 없습니다.')
#         return
    
#     team_name , _ , _ = get_team_info(player_name, matches[0])

#     await interaction.response.send_message(f'플레이어 {player_name}의 팀원들은 {team_name}입니다.')


#analyze_player
@tree.command(description='플레이어의 플레이 방식을 분석합니다.')
@discord.app_commands.describe(player_name='플레이어 이름')
async def analyze_player_team(interaction: discord.Interaction, player_name: str):

    await interaction.response.defer()


    resultdict = analyze_player(player_name)

    if(resultdict in [None, 404, 429, 0]):
        messages = {
            None: f'플레이어 {player_name}는 ai입니다.',
            404: f'플레이어 {player_name}을 찾을 수 없습니다.' + "\n" + "플레이어 이름을 정확히 입력해주세요(대소문자 구별).",
            429: f'Too Many Requests 잠시후 다시 시도해주세요.',
            0: f'플레이어 {player_name}의 최근 매치가 없습니다.'
        }
        await interaction.followup.send(messages[resultdict])
        return
    
    playingmethod = resultdict["playingmethod"]
    low_probability_team = resultdict["low_probability_team"]
    high_probability_team = resultdict["high_probability_team"]

    text1 = ""
    text2 = ""
    text3 = ""

    methods = {
        RANDOM_SQUAD: "랜덤 스쿼드",
        MERCENARY: "용병",
        SOMETIMES_SAME_TEAM: "가끔 같은 팀",
        OFTEN_SAME_TEAM: "자주 같은 팀",
        FIXED_TEAM: "고정 팀"
    }

    text1 = methods.get(playingmethod, "알 수 없음")
    text2 = ", ".join(high_probability_team) if high_probability_team else "알 수 없음"
    text3 = ", ".join(low_probability_team) if low_probability_team else "알 수 없음"


    await interaction.followup.send(f'플레이어 {player_name}의 플레이 방식은 {text1}입니다.' + "\n" + 
                                    f'현재 시간 높은 확률로 같은 팀인 플레이어는 {text2}입니다.' + "\n" + 
                                    f'현재 시간 낮은 확률로 같은 팀인 플레이어는 {text3}입니다.')
    
    #help 도움말 및 여러가지 명령어들을 출력하는 명령어
@tree.command(description='도움말을 출력합니다.')
async def help(interaction: discord.Interaction):
    
    text_header = "[1;34;41mPUBGTracker[0m" + "\n" + "명령어 목록" + "\n"

    text_body = "[1;36;41m/analyze_player_team[0m" "\n" + "-플레이어의 최근 매치를 바탕으로 같은 팀일 대략적인 확률을 분석합니다." + "\n만약 대소문자까지 정확하게 입력했는데 없다고 나온다면 그 플레이어는 ai 플레이어 입니다." +  "\n" + "일부분의 ai는 구분하고 경쟁전에서 더 잘 분석되고 스쿼드만 고려했습니다."

    text_footer = "-디스코드 링크: https://discord.gg/4xFy4zHZCn" + "\n"

    await interaction.response.send_message("```ansi\n" + text_header + "\n" + "\n" + text_body+ "\n" + "\n" + text_footer + "```" +"made by " + "<@389952737359560705>")


# 최근 메세지 n개를 삭제합니다.
@tree.command(description='최근 메세지 n개를 삭제합니다.', guild=discord.Object(f'{480315799857528853}'))
@discord.app_commands.describe(n='삭제할 메세지 개수')
async def delete_message(interaction: discord.Interaction, n: int):
    await interaction.channel.purge(limit=n+1)






@client.event
async def on_message(message):
  # This checks if the message is not from the bot itself. If it is, it'll ignore the message.
  if message.author == client.user:
    return

  # From here, you can add all the rules and the behaviour of the bot.
  # In this case, the bot checks if the content of the message is "Hello!" and send a message if it's true.
  if message.content == 'Hello!':
    await message.channel.send("Hello! I'm happy to see you around here.")

  if message.content == 'Good bye!':
    await message.channel.send("Hope to see you soon!")
    return




client.run(f'{TOKEN}')

# 명령어 get_team(플레이어 이름) : 플레이어의 팀원들을 반환

# https://discord.com/api/oauth2/authorize?client_id=1127694844207321150&permissions=8&scope=bot%20applications.commands