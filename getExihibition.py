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
    config.read('settings.ini')
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
    with open('settings.ini', 'w') as configfile:
        config.write(configfile)

    with open('keywords.txt', 'r', encoding='utf-8') as file:
        keywords = [line.strip() for line in file]
    return

# 数据存、取
def SaveData(sorted_exhibitions, area_code):
    file_path = f'./db/{area_code}.json'
    data_to_save = {
        'lastUpdated': datetime.now().strftime('%Y-%m-%d'),
        'sorted_exhibitions': sorted_exhibitions,
    }
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data_to_save, file, ensure_ascii=False, indent=4)

def LoadData(area_code):
    file_path = f'./db/{area_code}.json'
    today = datetime.now().strftime('%Y-%m-%d')
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if data.get('lastUpdated') == today:
                return data.get('sorted_exhibitions')
    return None

# 数据抓取
def FetchExhibitions(area_code):
    page = 1
    exhibition_dict = {}
    while True:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5410.0 Safari/537.36'
        }
        url = f'https://show.bilibili.com/api/ticket/project/listV2?version=134&page={page}&pagesize=16&area={area_code}&filter=&platform=web&p_type=全部类型'
        
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
        SaveData(exhibition_dict, area)
        _log.info(f"[F145H] data{{'{area}'}} returned")
    # exhibition
    """# 获取输出 ed1
    for result in exhibition_dict:
        name = result['project_name']
        date = f"{result['start_time']} - {result.get('end_time', result['start_time'])}"
        venue = result['venue_name']
        start_date = datetime.strptime(result['start_time'], '%Y-%m-%d')
        end_date = datetime.strptime(result['end_time'], '%Y-%m-%d')
        duration = (end_date - start_date).days + 1

        if not any(keyword in result['project_name'] for keyword in keywords) and\
            duration <= duration_limit_max and duration >= duration_limit_min and \
            start_date.date() >= start_limit and end_date.date() <= end_limit:
            
            output += f"{name}\n{date}\n{venue}\n\n"
    """
    exhibitions_by_date = {}

    for result in exhibition_dict:
        name = result['project_name']
        start_date_str = result['start_time']
        end_date_str = result['end_time']

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        duration = (end_date - start_date).days + 1

        if not any(keyword in result['project_name'] for keyword in keywords) and\
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
    
def GetExtraInfo(input): # doing
    init()
    with open('LastSearch.json', 'w', encoding='utf-8') as f:
        sorted_exhibitions = json.load(f)