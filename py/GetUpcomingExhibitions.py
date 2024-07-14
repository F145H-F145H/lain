import requests
import json
import os
from botpy import logging
from datetime import datetime, timedelta
from Levenshtein import ratio
import configparser

_log = logging.get_logger()
isInit = 0
duration_limit_min = -1
duration_limit_max = -1
today = datetime.now().date()
start_limit = today - timedelta(days=3)
end_limit = today + timedelta(days=30)
keywords = []

settings_path = './settings.ini'
keywords_path = './keywords.txt'
infodb_path = './infodb/'
detaildb_path = './detaildb/'
alldata_path = './infodb/alldata.json'

def init():
    global _log 
    global isInit
    global duration_limit_min
    global duration_limit_max
    global today
    global start_limit
    global end_limit
    global keywords

    _log = logging.get_logger()
    if isInit == 1:
        return
    isInit = 1
    _log.info(f"[F145H] GetExihibition initiating")
    
    config = configparser.ConfigParser()
    config.read(settings_path)
    if not config.has_section('General'):
        config.add_section('General')
        config.set('General', 'duration_limit_min', str(1))
        config.set('General', 'duration_limit_max', str(2))
        config.set('General', 'start_limit', str(3))
        config.set('General', 'end_limit', str(30))
    
    duration_limit_min = config.getint('General', 'duration_limit_min', fallback=1)
    duration_limit_max = config.getint('General', 'duration_limit_max', fallback=2)
    today = datetime.now().date()
    start_limit = today - timedelta(days=config.getint('General', 'start_limit', fallback=3))
    end_limit = today + timedelta(days=config.getint('General', 'end_limit', fallback=30))

    with open(settings_path, 'w', encoding='utf-8') as configfile:
        config.write(configfile)

    with open(keywords_path, 'r', encoding='utf-8') as file:
        keywords = [line.strip() for line in file]
    return
    

# 数据存、取
def SaveData(sorted_exhibitions, area_code):
    _log.info(f"[F145H] saving {{'{area_code}'}}.json")

    file_path = os.path.join(infodb_path, f'{area_code}.json')
    data_to_save = {
        'lastUpdated': datetime.now().strftime('%Y-%m-%d'),
        'sorted_exhibitions': sorted_exhibitions,
    }
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data_to_save, file, ensure_ascii=False, indent=4)

def LoadData(area_code):
    file_path = os.path.join(infodb_path, f'{area_code}.json')
    today = datetime.now().strftime('%Y-%m-%d')
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if data.get('lastUpdated') == today:
                return data.get('sorted_exhibitions')
    return None

def UpdateAllData(all_exhibitions_data):
    _log.info(f"[F145H] updating alldata.json")
    today_str = datetime.now().strftime('%Y-%m-%d')

    data = [
        {"name": exhibition['project_name'], "id": exhibition['id']}
        for exhibition in all_exhibitions_data
        if not any(keyword in exhibition['project_name'] for keyword in keywords)
    ]

    new_data = {
        "exhibitions": [],
        "lastUpdated": today_str
    }

    if os.path.exists(alldata_path):
        with open(alldata_path, 'r', encoding='utf-8') as file:
            existing_data = json.load(file)

        if 'exhibitions' in existing_data and 'lastUpdated' in existing_data:
            if existing_data['lastUpdated'] == today_str:
                existing_data["exhibitions"].extend(data)
                new_data = existing_data
            else:
                new_data["exhibitions"] = data
                new_data['lastUpdated'] = today_str
        else:
            new_data = {
                "exhibitions": data,
                "lastUpdated": today_str
            }
    else:
        # 如果文件不存在，使用初始化数据结构
        new_data["exhibitions"] = data
        new_data['lastUpdated'] = today_str

    # 写入数据
    with open(alldata_path, 'w', encoding='utf-8') as file:
        json.dump(new_data, file, ensure_ascii=False, indent=4)

# 数据抓取
def FetchExhibitions(area_code):
    page = 1
    exhibition_dict = {}
    while True:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5410.0 Safari/537.36'
        }
        url = f'https://show.bilibili.com/api/ticket/project/listV2?version=134&page={page}&pagesize=16&area={area_code}&filter=&platform=web&p_type=%E5%B1%95%E8%A7%88'
        
        response = requests.get(url=url, headers=headers)
        data = response.json()
        
        for exhibition in data['data']['result']:
            exhibition_dict[exhibition['id']] = exhibition
            
        page += 1
        if page > data['data']['numPages']:
            break    

    # 数据排序 可以使用该函数获取数据
    sorted_exhibitions = sorted(exhibition_dict.values(), key=SortExhibition)
    return sorted_exhibitions

# 按照展览时间排序
def SortExhibition(exhibition):
    return (
        datetime.strptime(exhibition['start_time'], '%Y-%m-%d'),
        exhibition['project_name']
    )

# 定义排序函数
def sort_key(key):
    if isinstance(key, tuple):
        # 对于多日展览，返回一个元组，其中包含最小日期和最大日期
        return key[0], key[1]
    else:
        # 对于单日展览，返回该日期
        return key, key
    
# 粗匹配查找地名
def FindClosestProvinceCode(query,province_codes):
    query = query.lower()
    best_match = None
    highest_ratio = 0.0
    
    for name, code in province_codes.items():
        similarity = ratio(name, query)
        
        if similarity > highest_ratio:
            highest_ratio = similarity
            best_match = code
    return best_match if best_match is not None else '340100'

# 获取当地近期展会
def GetInfo(input):
    init()
    output=""
    exhibition_dict = {}

    with open('area.json', 'r', encoding='utf-8') as file:
        provinces = json.load(file)
    province_codes = {province['name'].lower(): province['code'] for province in provinces}
    area = FindClosestProvinceCode(query=input, province_codes=province_codes)
    _log.info(f"[F145H] Search target")

    # 尝试从本地加载数据
    existing_data = LoadData(area)
    
    if existing_data is not None:
        _log.info(f"[F145H] Using cached data.")
        exhibition_dict = existing_data
    else: 
        # 如果本地数据不存在或过期，从网络获取数据
        _log.info(f"[F145H] Fetching new data from the internet...")
        exhibition_dict = FetchExhibitions(area)
        
        # 保存数据到本地
        UpdateAllData(exhibition_dict)
        SaveData(exhibition_dict, area)

    exhibitions_by_date = {}

    for exhibition in exhibition_dict:
        name = exhibition['project_name']
        start_date_str = exhibition['start_time']
        end_date_str = exhibition['end_time']

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        duration = (end_date - start_date).days + 1
        
        if not any(keyword in exhibition['project_name'] for keyword in keywords) and\
            duration <= duration_limit_max and duration >= duration_limit_min and \
            start_date >= start_limit and end_date <= end_limit:

            if start_date != end_date:
                key = (start_date, end_date)
            else:
                key = start_date

            exhibitions_by_date.setdefault(key, []).append(name)

    sorted_keys = sorted(exhibitions_by_date.keys(), key=sort_key)

    for key in sorted_keys:
        if isinstance(key, tuple):
            output += f"{key[0].strftime('%m%d')}-{key[1].strftime('%m%d')}\n"
        else:
            output += f"{key.strftime('%m%d')}\n"
        output += '\n'.join(exhibitions_by_date[key]) + "\n\n"
    output = output.rstrip('\n')

    _log.info(f"[F145H] data{{'{area}'}} returned")
    return output
    