"""Fixed commands and grounded MAA parameters shared by the bridge."""
import re

TASKS = ('startup', 'recruit', 'base', 'fight', 'credit', 'award', 'close')
STAGE_PATTERN = r'(?:[A-Z]{1,8}\d{0,2}|\d{1,2})-\d{1,2}(?:-(?:NORMAL|HARD))?'
SPECIAL_STAGES = ('Annihilation', 'Chernobog@Annihilation', 'LungmenOutskirts@Annihilation', 'LungmenDowntown@Annihilation')
HELP = '支持：/n8n maa daily；/n8n maa run fight stage=1-7 medicine=2；/n8n maa run recruit base credit award。任务结束自动关闭游戏。'


def valid_stage(stage):
    return isinstance(stage, str) and (stage == '' or stage in SPECIAL_STAGES or re.fullmatch(STAGE_PATTERN, stage) is not None)


def parse_command(message):
    parts = message.split()
    if parts in (['maa', 'test'], ['maa', 'daily']):
        return {'action': parts[1], 'tasks': [], 'medicine': 0, 'stage': ''}
    if len(parts) < 3 or parts[:2] != ['maa', 'run']:
        raise ValueError(HELP)
    tasks, medicine, stage, seen = [], 0, '', set()
    for part in parts[2:]:
        if part in TASKS and part not in tasks:
            tasks.append(part)
        elif re.fullmatch(r'medicine=\d{1,2}', part) and 'medicine' not in seen:
            medicine = int(part.split('=')[1]); seen.add('medicine')
        elif part.startswith('stage=') and 'stage' not in seen and valid_stage(part[6:]) and part[6:]:
            stage = part[6:]; seen.add('stage')
        else:
            raise ValueError(HELP)
    if not tasks or (seen and 'fight' not in tasks):
        raise ValueError('用药与关卡参数仅支持包含 fight 的组合。' + HELP)
    return {'action': 'run', 'tasks': tasks, 'medicine': medicine, 'stage': stage}


def to_command(selection):
    if selection['action'] in ('daily', 'test'):
        return 'maa ' + selection['action']
    result = 'maa run ' + ' '.join(selection['tasks'])
    if selection['stage']:
        result += ' stage=' + selection['stage']
    if selection['medicine']:
        result += ' medicine=' + str(selection['medicine'])
    return result


DIGITS = {'零':0,'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}

def number(value):
    if value.isdigit():
        return int(value)
    if '十' in value:
        a,b = value.split('十')
        return DIGITS.get(a,1)*10 + DIGITS.get(b,0)
    if value in DIGITS:
        return DIGITS[value]
    raise ValueError('请明确理智药数量（0–99）。')


def medicine_counts(text):
    return [number(v) for v in re.findall(r'([0-9]{1,3}|[零一二两三四五六七八九十]{1,3})\s*(?:瓶|份|个)\s*(?:理智药|药剂|药)?', text)]


def needs_medicine_count(text):
    return bool(re.search(r'(?:吃|用|喝|服用|消耗).{0,8}(?:理智药|药|瓶)',text)) and not medicine_counts(text) and not re.search(r'(?:不|别|禁止|无需).{0,4}(?:吃|用|喝|药)',text)


def validate_source(selection, text):
    """A model cannot grant medicine or a stage that the sender did not specify."""
    counts = medicine_counts(text)
    if selection['medicine'] and re.search(r'(?:不|别|禁止).{0,4}(?:吃|用|喝).{0,6}(?:药|瓶)',text):
        raise ValueError('消息要求不用药，不能执行用药任务。')
    if selection['medicine'] and (len(set(counts)) != 1 or selection['medicine'] != counts[0]):
        raise ValueError('请明确要使用几瓶理智药，例如“吃两瓶理智药刷 1-7”。')
    if selection['stage']:
        stage = selection['stage']
        mentions = re.findall(r'(?<![A-Za-z0-9])'+STAGE_PATTERN+r'(?![A-Za-z0-9-])', text.upper())
        aliases = {'当期剿灭':'Annihilation','切尔诺伯格':'Chernobog@Annihilation','龙门外环':'LungmenOutskirts@Annihilation','龙门市区':'LungmenDowntown@Annihilation'}
        grounded = stage in mentions or stage in text or any(k in text and v == stage for k,v in aliases.items())
        if not grounded:
            raise ValueError('请明确关卡编号，例如 1-7、CE-6 或 OF-1。')
    if needs_medicine_count(text):
        raise ValueError('请明确理智药数量；未指定数量时不会执行用药任务。')
    if counts and selection['medicine'] != counts[-1]:
        raise ValueError('识别的用药数量与消息不一致，请重新明确数量。')
