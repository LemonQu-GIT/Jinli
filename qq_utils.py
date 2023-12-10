import re
import json
from datetime import datetime
from tqdm import tqdm

with open("./data/schoolID.json", "r", encoding="utf-8") as f:
    schoolID_list = json.loads(f.read())


def get_qq_number(text):
    content = text.split(' ')[2:]
    content = ' '.join(content)
    qq_number_re = re.search("[1-9][0-9]{6,12}", content)
    try:
        qq_number_split = content.split('<')
        qq_number_split = qq_number_split[-1].split('>')[0]
        try:
            qq_number_split = int(qq_number_split)
            return str(qq_number_split).strip()
        except:
            return qq_number_re.group().strip()
    except:
        try:
            qq_number_split = content.split('<')
            qq_number_split = qq_number_split[-1].split('>')[0]
            return qq_number_split.strip()
        except:
            return None


def get_schoolID(text):
    content = text.split(' ')[2:]
    content = ' '.join(content)
    qq_num = get_qq_number(text)
    try:
        qq_num = int(qq_num)
        content = content.replace(f"({qq_num})", '').strip()
    except:
        content = content.replace(f"<{qq_num}>", '').strip()
    id = re.search("^[0-2][0-9]0?[1-8](([0-3][0-9])|([5-9][0-9]))", content)
    try:
        int(content[id.span()[1]+1])
        return None
    except:
        return id.group().strip() if id != None else None


def get_name(text):
    content = text.split(' ')[2:]
    content = ' '.join(content)
    qq_num = get_qq_number(text)
    try:
        qq_num = int(qq_num)
        content = content.replace(f"({qq_num})", '').strip(
            'AM ').strip('PM ').strip()
    except:
        content = content.replace(f"<{qq_num}>", '').strip(
            'AM ').strip('PM ').strip()
    content = re.sub(r'【(.+?)】', '', content)
    return content.strip()


def build_id_dict(force_rebuild: bool):
    if force_rebuild:
        id_dict = {}
        qq_number = ''
        schoolID = ''
        with open("./data/log.txt", 'r', encoding='utf-8') as f:
            content = f.read()
            f.close()
        truncate = content.split('\n')
        pbar = tqdm(truncate)
        pbar.set_description('Building SchoolID Dictionary')
        for msg in pbar:
            date_in = re.match("^((([0-9]{3}[1-9]|[0-9]{2}[1-9][0-9]{1}|[0-9]{1}[1-9][0-9]{2}|[1-9][0-9]{3})-(((0[13578]|1[02])-(0[1-9]|[12][0-9]|3[01]))|((0[469]|11)-(0[1-9]|[12][0-9]|30))|(02-(0[1-9]|[1][0-9]|2[0-8]))))|((([0-9]{2})(0[48]|[2468][048]|[13579][26])|((0[48]|[2468][048]|[3579][26])00))-02-29))\\s+([0-1]?[0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])", msg)
            if date_in != None:
                schoolID = get_schoolID(msg)
                qq_number = get_qq_number(msg)
                if not (qq_number in id_dict.keys()) and schoolID != None:
                    id_dict[qq_number] = schoolID
        with open("./data/schoolID.json", 'w', encoding='utf-8') as f:
            f.write(json.dumps(id_dict, ensure_ascii=False, indent=4))
        return id_dict
    else:
        with open("./data/schoolID.json", 'r', encoding='utf-8') as f:
            id_dict = json.loads(f.read())
            f.close()
        return id_dict


def parse_log(force_rebuild_id_dict=False):
    with open("./data/log.txt", 'r', encoding='utf-8') as f:
        content = f.read()
        f.close()
    now = datetime.now()
    parsed = []
    message = ''
    qq_number = ''
    date = ''
    schoolID = ''
    name = ''
    id_dict = build_id_dict(force_rebuild_id_dict)
    content += f'\n\n{now.strftime("%Y-%m-%d %H:%M:%S")} (1145141919810)'
    truncate = content.split('\n')
    pbar = tqdm(truncate)
    pbar.set_description('Building Text')
    for msg in pbar:
        date_in = re.match("^((([0-9]{3}[1-9]|[0-9]{2}[1-9][0-9]{1}|[0-9]{1}[1-9][0-9]{2}|[1-9][0-9]{3})-(((0[13578]|1[02])-(0[1-9]|[12][0-9]|3[01]))|((0[469]|11)-(0[1-9]|[12][0-9]|30))|(02-(0[1-9]|[1][0-9]|2[0-8]))))|((([0-9]{2})(0[48]|[2468][048]|[13579][26])|((0[48]|[2468][048]|[3579][26])00))-02-29))\\s+([0-1]?[0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])", msg)
        if date_in != None:
            if message != '' and qq_number != '' and date != '':
                if qq_number in id_dict.keys():
                    schoolID = id_dict[qq_number]
                else:
                    schoolID = 'Unknown'
                parsed.append({"date": date.strip(), "schoolID": schoolID, "name": name,
                              "qq_number": qq_number.strip(), "message": message.strip()})
                message = ''
            date = date_in[0]
            schoolID = get_schoolID(msg)
            qq_number = get_qq_number(msg)
            name = get_name(msg)
        else:
            message += " " + msg
    return parsed


def get_message_count(content, qq_number):
    count = 0
    pbar = tqdm(content)
    pbar.set_description('Counting Message')
    for msg in pbar:
        if msg['qq_number'] == qq_number:
            count += 1
    return count


def schoolID_qqnumber(schoolID):
    keys = dict(schoolID_list).values()
    if schoolID in keys:
        for k, v in dict(schoolID_list).items():
            if v == schoolID:
                return k
    else:
        return None


def qqnumber_schoolID(qq_number):
    keys = dict(schoolID_list).keys()
    if qq_number in keys:
        return schoolID_list[qq_number]
    else:
        return None


def get_message_range(start, end, content):
    try:
        start = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
    except:
        print(start, end)
        return None
    pbar = tqdm(content)
    pbar.set_description('Getting Message Range')
    message_range = []
    for msg in pbar:
        date = datetime.strptime(msg['date'], '%Y-%m-%d %H:%M:%S')
        if start <= date <= end:
            message_range.append(msg)
        if date > end:
            break
    return message_range
