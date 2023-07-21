import discord
from discord import app_commands
from discord.ext import commands
from enum import Enum


import requests
import json
import os
import csv
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

################################################################################################


# PUBG API json데이터에서 id는 식별자의 의미처럼 사용되므로 name이랑 혼동하지 않도록 주의 할 것


## 전역변수



# string
API_KEY = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiIxMWRlNGJiMC1mZTFjLTAxM2ItODI3Ny00MmY3ZTdiY2Q3MWIiLCJpc3MiOiJnYW1lbG9ja2VyIiwiaWF0IjoxNjg4NjQyMDEzLCJwdWIiOiJibHVlaG9sZSIsInRpdGxlIjoicHViZyIsImFwcCI6Ii1jYWNmZTRkOS01ZDc0LTQxNGQtYTViNi0xZTFlODA2YjRiMDUifQ.tj5njHUXJvUsR850EFswKj2j36hwbkP-RzhN9YCbqbY' # 여기에 PUBG API 키를 넣으세요.
PLATFORM = 'kakao' # 플랫폼을 설정하세요. 예: steam, kakao, xbox, psn 등
DEFAULT_PLATFORM = 'kakao'


PLAYER_JSON_DIR = 'player_json' # 플레이어의 json 파일을 저장할 폴더를 지정하세요.
MATCH_JSON_DIR = 'match_json' # 매치의 json 파일을 저장할 폴더를 지정하세요.

REAL_TIME_MATCH_CSV_DIR = 'real_time_match_csv'
DISCORD_USER_DATA_DIR = 'discord_user_data.csv'


USER_ID = 'baboyeji'
# int

REFRESH_PLAYER_DATA_CYCLE = 1200 # player_data를 새로고침할 주기 (api 요청 횟수를 줄이기 위함)
REFRESH_UNKNOWN_PLAYER_DATA_CYCLE = 3600
REFRESH_STATS_CYCLE = 3600 # stats를 새로고침할 주기



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


def default_setting():
    season_update()
    #data / player_json / match_json 폴더 생성
    if not os.path.exists('data'):
        os.mkdir('data')
    if not os.path.exists('data'/'kakao'/PLAYER_JSON_DIR):
        os.mkdir('data'/'kakao'/PLAYER_JSON_DIR)
    if not os.path.exists('data'/'kakao'/MATCH_JSON_DIR):
        os.mkdir('data'/'kakao'/MATCH_JSON_DIR)
    if not os.path.exists('data'/'kakao'/REAL_TIME_MATCH_CSV_DIR):
        os.mkdir('data'/'kakao'/REAL_TIME_MATCH_CSV_DIR)


def send_error_message(player_name, resultdict):
    messages = {
        None: f'```\n플레이어 {player_name}는 ai입니다.```',
        404: f'```\n플레이어 {player_name}을 찾을 수 없습니다.' + "\n" + "플레이어 이름을 정확히 입력해주세요(대소문자 구별)." + "\n" + "만약 정확히 입력해도 안된다면 ai플레이어 입니다.```",
        429: f'```\nToo Many Requests 잠시후 다시 시도해주세요.```',
        0: f'```\n플레이어 {player_name}의 최근 매치가 없습니다.```'
    }
    return messages[resultdict]

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
    

def get_server_name(discord_user_id):
    # csv파일을 읽어서 discord_user_id에 해당하는 server_name을 반환
    with open(DISCORD_USER_DATA_DIR, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if(row[0] == discord_user_id):
                return row[1]
    return DEFAULT_PLATFORM

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

def get_real_matches_from_player_name(player_name):
    
    json_player_data = save_player_json(player_name)

    if(json_player_data == None):
        return None
    if(json_player_data == 404):
        return 404
    if(json_player_data == 429):
        return 429

    match_id_list = []
    for match in json_player_data['data'][0]['relationships']['matches']['data']:

        save_match_json(match['id'])
        json_match_data = load_match_json(match['id'])

        if json_match_data['data']['attributes']['isCustomMatch'] == False:
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

    

    matches = get_real_matches_from_player_name(player_name)
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

    print(team_name)

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

    print(count_list)

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
    
    matches = get_real_matches_from_player_name(player_name)
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

        
    print(count_list)

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
    matches = get_real_matches_from_player_name(player_name)

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

def real_time_killlogging(kill_time, killer, player_name, death_time, discord_id, total_player = None, team_name1 = None, team_name2 = None, team_name3 = None, isreset = False):

    server= get_server_name(discord_id)

    path = f'{server}/real_time_game/{discord_id}.json'

    if(os.path.isfile(path) == False or isreset == True):

        death_dict = analyze_player(player_name)
        killer_dict = analyze_player(killer)
        killer_kills = 0

        if(death_time is not None):
            killer_kills = 1

        
        with open(path, 'w') as outfile:
            initial_data = {'data': {'attributes': {}, 'killlog': {}, 'analysis': {}}}
            if death_dict in [None, 404, 429, 0]:
                print(send_error_message(player_name, death_dict))
                initial_data['data']['killlog'][player_name] = {"kill_time": kill_time , "killer": killer, "death_time": death_time}
                initial_data['data']['attributes']["total_player"] = total_player
                initial_data['data']['attributes']["team_name"] = [player_name , team_name1, team_name2, team_name3]
                initial_data['data']['attributes']["createdAt"] = current_time_utc().strftime('%Y-%m-%dT%H:%M:%SZ')
                
            else:
                playingmethod = death_dict['playingmethod']
                low_probability_team = death_dict['low_probability_team']
                high_probability_team = death_dict['high_probability_team']

                initial_data['data']['killlog'][player_name] = {"kill_time": kill_time , "kills": 0 ,"killer": killer, "death_time": death_time , "playingmethod": playingmethod, "low_probability_team": low_probability_team, "high_probability_team": high_probability_team}
                initial_data['data']['attributes']["total_player"] = total_player
                initial_data['data']['attributes']["team_name"] = [player_name , team_name1, team_name2, team_name3]
                initial_data['data']['attributes']["createdAt"] = current_time_utc().strftime('%Y-%m-%dT%H:%M:%SZ')
                
            
            if killer_dict in [None, 404, 429, 0]:
                print(send_error_message(killer, killer_dict))
                initial_data['data']['killlog'][player_name] = {"kill_time": kill_time , "killer": None, "death_time": death_time}
            else:
                playingmethod = killer_dict['playingmethod']
                low_probability_team = killer_dict['low_probability_team']
                high_probability_team = killer_dict['high_probability_team']

                initial_data['data']['killlog'][killer] = {"kill_time": kill_time , "kills": killer_kills , "killer": None, "death_time": death_time , "playingmethod": playingmethod, "low_probability_team": low_probability_team, "high_probability_team": high_probability_team}
            
            json.dump(initial_data, outfile, indent=4)
            




    else:
        with open(path, 'r') as f:


            json_data = json.load(f)
            death_dict = -1
            killer_dict = -1

            death_kills = 0
            killer_kills = 1


            #만약 data killlog 안에 player_name 과 같은 키가 없다면

            if not (player_name in json_data['data']['killlog'][player_name]):
                death_dict = analyze_player(player_name)
            else:
                death_kills = json_data['data']['killlog'][player_name]['kills']

            if not (killer in json_data['data']['killlog'][killer]):
                killer_dict = analyze_player(killer)
            
            else:
                killer_kills = json_data['data']['killlog'][killer]['kills']
                if death_time is not None:
                    killer_kills += 1

            if death_dict in [-1]:
                playingmethod = json_data['data']['killlog'][player_name]['playingmethod']
                low_probability_team = json_data['data']['killlog'][player_name]['low_probability_team']
                high_probability_team = json_data['data']['killlog'][player_name]['high_probability_team']
                json_data['data']['killlog'][player_name] = {"kill_time": kill_time , "kills": death_kills ,"killer": killer, "death_time": death_time , "playingmethod": playingmethod, "low_probability_team": low_probability_team, "high_probability_team": high_probability_team}

            elif death_dict in [None, 404, 429, 0]:
                print(send_error_message(player_name, death_dict))
                json_data['data']['killlog'][player_name] = {"kill_time": kill_time , "kills": death_kills ,"killer": killer, "death_time": death_time}
            else:
                playingmethod = death_dict['playingmethod']
                low_probability_team = death_dict['low_probability_team']
                high_probability_team = death_dict['high_probability_team']
                json_data['data']['killlog'][player_name] = {"kill_time": kill_time , "kills": death_kills ,"killer": killer, "death_time": death_time , "playingmethod": playingmethod, "low_probability_team": low_probability_team, "high_probability_team": high_probability_team}

            if killer_dict in [-1]:
                playingmethod = json_data['data']['killlog'][killer]['playingmethod']
                low_probability_team = json_data['data']['killlog'][killer]['low_probability_team']
                high_probability_team = json_data['data']['killlog'][killer]['high_probability_team']
                exkiller = json_data['data']['killlog'][killer]['killer']
                json_data['data']['killlog'][killer] = {"kill_time": kill_time , "kills": killer_kills,"killer": exkiller, "death_time": None , "playingmethod": playingmethod, "low_probability_team": low_probability_team, "high_probability_team": high_probability_team}

            elif killer_dict in [None, 404, 429, 0]:
                print(send_error_message(killer, killer_dict))
                json_data['data']['killlog'][killer] = {"kill_time": kill_time , "kills": killer_kills ,"killer": None, "death_time": death_time}
            else:
                playingmethod = killer_dict['playingmethod']
                low_probability_team = killer_dict['low_probability_team']
                high_probability_team = killer_dict['high_probability_team']
                json_data['data']['killlog'][killer] = {"kill_time": kill_time , "kills": killer_kills ,"killer": None, "death_time": death_time , "playingmethod": playingmethod, "low_probability_team": low_probability_team, "high_probability_team": high_probability_team}

            
            with open(path, 'w') as outfile:
                json.dump(json_data, outfile, indent=4)


def season_update():
    url = "https://api.pubg.com/shards/steam/seasons"
    response = requests.get(url, headers=HEADERS)
    seasons = response.json()

    with open('./data/seasons.json', 'w') as outfile:
        json.dump(seasons, outfile, indent=4)

    
    
def get_current_season_id():
    with open('./data/seasons.json', 'r') as f:
        seasons = json.load(f)
        for season in seasons['data']:
            if season['attributes']['isCurrentSeason']:
                current_season_id = season['id']
                break
    return current_season_id




def get_recent_json_file(path):
    # Check if the file exists and was modified within the last 5 minutes
    if os.path.exists(path) and os.path.getmtime(path) > (datetime.now() - timedelta(seconds=REFRESH_STATS_CYCLE)).timestamp():
        # If so, open the file and return its contents
        with open(path, 'r') as infile:
            return json.load(infile)
    else:
        # If not, return None
        return None
    


def get_stats_from_player_name(player_name, game_type):
    server = get_server_name(player_name)

    player_json_data = save_player_json(player_name)

    if player_json_data is None:
        return None
    if player_json_data == 404:
        return 404
    if player_json_data == 429:
        return 429

    player_id = player_json_data['data'][0]['id']

    current_season_id = get_current_season_id()

    path = f"./data/{server}/{player_name}_{game_type}.json"

    stats_json = get_recent_json_file(path)

    if stats_json is None:
        url = f"https://api.pubg.com/shards/{server}/players/{player_id}/seasons/{current_season_id}"
        if game_type == "ranked":
            url += "/ranked"
            
        response = requests.get(url, headers=HEADERS)

        print("api 호출 1번")
        stats_json = response.json()

        # data createdAt
        stats_json['data']['createdAt'] = current_time_utc().strftime('%Y-%m-%dT%H:%M:%SZ')

        with open(path, 'w') as outfile:
            json.dump(stats_json, outfile, indent=4)
        
    return stats_json



           



# 킬로그 유형

# 1. 기절 알수있는거 -> 죽인사람 기절한사람 -> high_probability_team을 제외하고는 다른팀이라고 가정.
    

        
        





###########################

# discord

###########################


SERVER_ID = 1127695613048389763
# SERVER_ID = 480315799857528853
CLIENT_ID = 1127694844207321150
TOKEN = "MTEyNzY5NDg0NDIwNzMyMTE1MA.G9p00n.d8hSMN-uZ2wuRu0SpwB0VD3yHr30SujOc4Dw_4"
TEST_TOKEN = "MTEzMTA0NTExMzQyNzEzMjQxNg.GEd6If.Cm7PsKQ7XIZGQ9ec01jFWUPXh_uu4HGu3J0N-M"



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


#analyze_player
@tree.command(description='플레이어의 플레이 방식을 분석합니다.')
@discord.app_commands.describe(player_name='플레이어 이름')
async def analyzeplayer(interaction: discord.Interaction, player_name: str):

    await interaction.response.defer()


    resultdict = analyze_player(player_name)

    

    if resultdict in [None, 404, 429, 0]:
        error_message = send_error_message(player_name, resultdict)
        await interaction.followup.send(error_message)
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


    await interaction.followup.send(f'```\n플레이어 {player_name}의 플레이 방식은 {text1}입니다.' + "\n" + 
                                    f'현재 시간 높은 확률로 같은 팀인 플레이어는 {text2}입니다.' + "\n" + 
                                    f'현재 시간 낮은 확률로 같은 팀인 플레이어는 {text3}입니다.```')
    
    #help 도움말 및 여러가지 명령어들을 출력하는 명령어
@tree.command(description='도움말을 출력합니다.')
async def help(interaction: discord.Interaction):
    
    text_header = "[1;34;41mPUBGanalyzer[0m" + "  명령어 목록"

    text_body = ("[1;36m/set_server[0m\n"
    "-사용자가 이용하는 서버를 설정합니다. 선택 가능한 서버는 steam이나 kakao입니다."
    "\n\n[1;36m/analyzeplayer[0m\n" 
    "-플레이어의 최근 팀 플레이 확률을 분석합니다. \nAI 플레이어는 없다고 뜨는 경우도 있습니다."
    "\n\n[1;36m/get_stats[0m\n"
    "-플레이어의 최근 시즌 전적을 출력합니다.")



    text_footer = "-디스코드 링크: https://discord.gg/4xFy4zHZCn" + "\n"

    await interaction.response.send_message("```ansi\n" + text_header + "\n" + "\n" + text_body+ "\n" + "\n" + text_footer + "```" +"made by " + "<@389952737359560705>")


# kakao /steam 서버 설정

server_name = Enum(value='server_name', names=['kakao', 'steam'])

@tree.command(description='서버를 설정합니다.')
@discord.app_commands.describe(server='카카오/스팀 서버 이름')
async def set_server(interaction: discord.Interaction, server: server_name):
    user = str(interaction.user.id)  # ID를 문자열로 변환

    if os.path.exists(DISCORD_USER_DATA_DIR):
        df = pd.read_csv(DISCORD_USER_DATA_DIR, dtype={'user': str})  # 'user' column as string

        if user in df['user'].values:  # if user already exists
            df.loc[df['user'] == user, 'server'] = server.name  # update the 'server' value
        else:
            new_df = pd.DataFrame({'user': [user], 'server': [server.name]})
            df = pd.concat([df, new_df], ignore_index=True)

    else:
        df = pd.DataFrame({'user': [user], 'server': [server.name]})  # create a new dataframe

    df.to_csv(DISCORD_USER_DATA_DIR, index=False)  # save the dataframe to a CSV file

    await interaction.response.send_message(f'<@{user}>님의 서버를 {server.name}로 설정했습니다!')




#get_season_stats

@tree.command(description='플레이어의 최근 시즌 경쟁전 스탯을 출력합니다.')
async def get_stats(interaction: discord.Interaction, player_name: str):

    await interaction.response.defer()

    data = get_stats_from_player_name(player_name,'normal')

    if data == None:
        error_message = send_error_message(player_name, data)
        await interaction.followup.send(error_message)
        return
    if data == 404:
        error_message = send_error_message(player_name, data)
        await interaction.followup.send(error_message)
        return
    if data == 429:
        error_message = send_error_message(player_name, data)
        await interaction.followup.send(error_message)
        return

    squad_data = data['data']["attributes"]["rankedGameModeStats"]["squad"]
    createdAt = data['data']['createdAt']
    createdAt = datetime.strptime(createdAt, '%Y-%m-%dT%H:%M:%SZ')
    createdAt = createdAt + timedelta(hours=9)
    formatted_date = createdAt.strftime('%m-%d %H:%M')
    tier = squad_data["currentTier"]["tier"]
    kda = squad_data["kda"]
    avg_damage = squad_data["damageDealt"] / squad_data["roundsPlayed"]
    win_ratio = squad_data["winRatio"]
    top10_ratio = squad_data["top10Ratio"]
    current_rank_point = squad_data["currentRankPoint"]

    # Creating a figure
    fig, axs = plt.subplots(1, 2, figsize=(15,7))

    fig.subplots_adjust(left=0.1)  # adjust the left side of the subplots of the figure

    # Creating the pie chart for win ratio
    labels = 'Wins', 'Losses'
    sizes = [win_ratio, 1-win_ratio]
    explode = (0.1, 0)  # only "explode" the 1st slice (i.e. 'Wins')
    colors = ['red', 'gray']

    axs[0].pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors, textprops={'fontsize': 14})
    axs[0].axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    axs[0].set_title('Win Ratio', fontsize=20)

    # Creating the pie chart for top10 ratio
    labels = 'Top 10', 'Not Top 10'
    sizes = [top10_ratio, 1-top10_ratio]
    explode = (0.1, 0)  # only "explode" the 1st slice (i.e. 'Top 10')
    colors = ['red', 'gray']

    axs[1].pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors, textprops={'fontsize': 14})
    axs[1].axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    axs[1].set_title('Top 10 Ratio', fontsize=20)

    # Adding the text
    stats_text = f'Tier: {tier}\nCurrent Rank Point: {current_rank_point}\nKDA: {kda}\nAverage Damage: {avg_damage:.2f}\nLast Updated: {formatted_date}'
    bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
    axs[1].text(0.5, 0.95, stats_text, transform=axs[1].transAxes, fontsize=22,
            verticalalignment='top', bbox=bbox_props)

    plt.suptitle(f"{player_name}'s Statistics", fontsize=24)



    server = get_server_name(player_name)

    plt.savefig('temporary_data.png')

    await interaction.followup.send(file=discord.File('temporary_data.png'))

    #delete the figure data
    os.remove('temporary_data.png')


#season_update
@tree.command(description='가장 최근 시즌으로 업데이트 합니다.')
async def update_season(interaction: discord.Interaction):
    season_update()
    await interaction.response.send_message("성공!")
    







@client.event
async def on_message(message):
  # This checks if the message is not from the bot itself. If it is, it'll ignore the message.
  if message.author == client.user:
    return

  # From here, you can add all the rules and the behaviour of the bot.
  # In this case, the bot checks if the content of the message is "Hello!" and send a message if it's true.
  if message.content == 'Hello!':
    get_stats_from_player_name("babomingji")
    await message.channel.send("Hello! I'm happy to see you around here.")

  if message.content == 'Good bye!':
    await message.channel.send("Hope to see you soon!")
    return





client.run(f'{TOKEN}')
# client.run(f'{TEST_TOKEN}')

# 명령어 get_team(플레이어 이름) : 플레이어의 팀원들을 반환

# https://discord.com/api/oauth2/authorize?client_id=1127694844207321150&permissions=8&scope=bot%20applications.commands
# https://discord.com/api/oauth2/authorize?client_id=1131045113427132416&permissions=8&scope=bot%20applications.commands