import requests
import json
import os
import re
import difflib
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
show_guests = False
keywords = []

settings_path = './settings.ini'
keywords_path = './keywords.txt'
infodb_path = './infodb/'
detaildb_path = './detaildb/'
alldata_path = './infodb/alldata.json'

chinese_to_arabic = {
    '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, '百': 100, '千': 1000,
    '万': 10000, '〇': 0, '壹': 1, '贰': 2, '叁': 3, '肆': 4,
    '伍': 5, '陆': 6, '柒': 7, '捌': 8, '玖': 9, '拾': 10
}
pattern = re.compile(r'第([\u4e00-\u9fa5]+)届')

def init():
    global _log 
    global isInit
    global duration_limit_min
    global duration_limit_max
    global today
    global start_limit
    global end_limit
    global show_guests
    global keywords
    
    _log = logging.get_logger()
    if isInit == 1:
        return
    isInit = 1
    _log.info(f"[F145H] GetExihibition initiating")
    
    # 初始化设置信息
    config = configparser.ConfigParser()
    config.read(settings_path)
    if not config.has_section('General'):
        config.add_section('General')
        config.set('General', 'duration_limit_min', str(1))
        config.set('General', 'duration_limit_max', str(2))
        config.set('General', 'start_limit', str(3))
        config.set('General', 'end_limit', str(30))
        config.set('General', 'show_guests', str(False))
    
    # 读取设置信息
    duration_limit_min = config.getint('General', 'duration_limit_min', fallback=1)
    duration_limit_max = config.getint('General', 'duration_limit_max', fallback=2)
    today = datetime.now().date()
    start_limit = today - timedelta(days=config.getint('General', 'start_limit', fallback=3))
    end_limit = today + timedelta(days=config.getint('General', 'end_limit', fallback=45))
    show_guests = config.getboolean('General', 'show_guests', fallback=False)
    # 读取屏蔽关键词
    with open(keywords_path, 'r', encoding='utf-8') as file:
        keywords = [line.strip() for line in file]
    return

def is_chinese_digit(s):
    """检查给定的字符串s是否是一个有效的中文数字"""
    try:
        int(''.join(str(chinese_to_arabic[c]) for c in s if c in chinese_to_arabic))
        return True
    except KeyError:
        return False

def position_weighted_ratio(search_term, target_string):
    search_len = len(search_term)
    target_len = len(target_string)
    max_score = min(search_len, target_len)
    score = 0

    # 遍历search_term的每个字符
    for i, char in enumerate(search_term):
        # 检查char是否在target_string中
        if char in target_string:
            # 获取char在target_string中的第一个出现位置
            pos = target_string.find(char)
            # 根据位置计算权重
            weight = (1 - abs(pos - i) / 256) if target_len > 0 else 1
            score += weight

    # 归一化分数
    normalized_score = score / max_score * 10000
    return int(normalized_score)

def find_id(word):
    _log.info(f"[F145H] searching id with {word}")

    with open(alldata_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        exhibitions = data.get('exhibitions', [])
        
        # 初始化最佳匹配和最高分数
        best_match = None
        highest_score = 0
        
        for exhibition in exhibitions:
            # 移除展览名称中的“第XX届”
            clean_name = pattern.sub('', exhibition['name'])
            
            # 计算修改后的名称与查询词的匹配得分
            score = position_weighted_ratio(word, clean_name)
            _log.info(f"[F145H] searching {clean_name} score {score}")
            
            # 更新最佳匹配
            if score > highest_score:
                highest_score = score
                best_match = exhibition
        
        if best_match is not None:
            _log.info(f"[F145H] GetExhibition id {best_match['id']} found with score {highest_score}")
            return best_match['id']
        
    _log.info(f"[F145H] GetExhibition id not found")
    return None  # 如果没有找到匹配项

def save_event_info_as_json(json_data):
    event_dict = json.loads(json_data)
    
    # 提取事件的基本信息
    name = event_dict['data']['name']
    start_time = datetime.fromtimestamp(event_dict['data']['start_time']).strftime('%Y-%m-%d %H:%M:%S')
    end_time = datetime.fromtimestamp(event_dict['data']['end_time']).strftime('%Y-%m-%d %H:%M:%S')
    
    # 提取场地信息
    venue_info = {
        "name": event_dict['data']['venue_info']['name'],
        "address_detail": event_dict['data']['venue_info']['address_detail']
    }
    
    # 提取嘉宾信息
    guests = [{"name": guest['name']} for guest in event_dict['data']['guests']]
    
    # 提取交流群信息 *****
    communicate = []
    details_text = event_dict['data']['performance_desc']['list'][0]['details']
    print(details_text)

    # 创建输出字典
    output_dict = {
        "name": name,
        "start_time": start_time,
        "end_time": end_time,
        "venue_info": venue_info,
        "guests": guests,
        "communicate": communicate
    }
    
    # 获取事件ID
    event_id = event_dict['data']['id']
    
    file_path = os.path.join(detaildb_path, f"xhbt{event_id}.json")
    
    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(output_dict, file, indent=4)
    return

def fetch_save_exhibition(id):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5410.0 Safari/537.36'
    }
    url = f'https://show.bilibili.com/api/ticket/project/getV2?id={id}'
    response = requests.get(url=url, headers=headers)
    save_event_info_as_json(response.text)

def show(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
            event_dict = json.load(f)
            
            # 提取事件的信息
            name = event_dict['name']
            start_time = event_dict['start_time']
            end_time = event_dict['end_time']
            venue_info = f"""场馆名: {event_dict['venue_info']['name']}\n具体地址: {event_dict['venue_info']['address_detail']}\n"""
            guests = str()
            if show_guests == True:
                for guest in event_dict['guests']:
                    guests += f"嘉宾：{guest['name']}\n"

            communicate = str()
            #details_text = event_dict['performance_desc']['list'][0]['details'] # *****

            # 创建输出字典
            output_dict = f"""\n展览名: {name}\n开始时间: {start_time}\n结束时间: {end_time}\n{venue_info}{guests}{communicate}"""
            return output_dict[:-1]

def GetExtraInfo(input):
    init()
    id = find_id(input)
    file_path = os.path.join(detaildb_path, f"xhbt{id}.json")
    if os.path.exists(file_path):
        return show(file_path)
    else:
        fetch_save_exhibition(id)
    return show(file_path)