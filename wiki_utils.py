# coding=utf-8
import requests
import json
import time
import hashlib
import re
import sys
import os
import datetime
from tqdm import tqdm
from urllib.parse import quote
from datetime import datetime, timedelta

from rich.console import Console
console = Console()


def log(event: str, type: str, show: bool = False):
    back_frame = sys._getframe().f_back
    if back_frame is not None:
        back_filename = os.path.basename(back_frame.f_code.co_filename)
        back_funcname = back_frame.f_code.co_name
        back_lineno = back_frame.f_lineno
    else:
        back_filename = "Unknown"
        back_funcname = "Unknown"
        back_lineno = "Unknown"
    now = datetime.now()
    time = now.strftime("%Y-%m-%d %H:%M:%S")
    logger = f"[{time}] <{back_filename}:{back_lineno}> <{back_funcname}()> {type}: {event}"
    if type.lower() == "info":
        style = "green"
    elif type.lower() == "error":
        style = "red"
    elif type.lower() == "critical":
        style = "bold red"
    elif type.lower() == "event":
        style = "#ffab70"
    else:
        style = ""
    if show:
        console.print(logger, style=style)
    with open('latest.log', 'a', encoding='utf-8') as f:
        f.write(f'{logger}\n')


def if_in_data(data: list, obj: str):
    for things in data:
        if things['title'] == obj:
            return True
    return False


def get_config():
    with open('./config.json', encoding='utf-8') as f:
        return json.loads(f.read())


def change_latest(timestamp):
    config = get_config()
    with open('./config.json', 'w', encoding='utf-8') as f:
        config['wiki']['latest'] = timestamp
        config['wiki']['hash'] = hashlib.md5(
            str(timestamp).encode('utf-8')).hexdigest()
        f.write(json.dumps(config, ensure_ascii=False, indent=4))


def remove_wiki_tags(text):
    text = re.sub('<.*?>', '', text)
    text = re.sub('(分类:(\S)+|Category:(\S)+|文件:(\S)+\s)', '', text)
    return text


def wiki(title_list: list):
    cookie = get_config()['wiki']['cookie']
    headers = {'cookie': cookie}
    session = requests.Session()
    contents = []
    pbar = tqdm(title_list)
    for titles in pbar:
        pbar.set_description(f'Processing {titles}')
        try:
            quote_title = quote(titles, safe='/:?=.')
            url = f'''https://hywiki.xyz/api.php?action=query&format=json&formatversion=2&prop=categories|images|pageimages|revisions&titles={quote_title}&rvprop=content'''
            r = session.get(url, headers=headers)
            text = json.loads(r.text)
            content = text['query']['pages'][0]['revisions'][0]['content']
            contents.append(content)
            time.sleep(0.4)
        except:
            try:
                time.sleep(7)
                quote_title = quote(titles, safe='/:?=.')
                url = f'''https://hywiki.xyz/api.php?action=query&format=json&formatversion=2&prop=categories|images|pageimages|revisions&titles={quote_title}&rvprop=content'''
                r = session.get(url, headers=headers)
                text = json.loads(r.text)
                contents.append(content)
            except:
                contents.append(' ')
    return contents


def all_pages():
    titles = []
    cookie = get_config()['wiki']['cookie']
    url = f'''https://hywiki.xyz/api.php?action=query&format=json&formatversion=2&list=allpages&aplimit=max&apfilterredir=nonredirects&apnamespace=0'''
    headers = {'cookie': cookie}
    session = requests.Session()
    r = session.get(url, headers=headers)
    text = json.loads(r.text)
    try:
        pages = text['query']['allpages']
        for page in pages:
            titles.append(page['title'])
        apcontinue = text['continue']['apcontinue']
        while True:
            url = f'''https://hywiki.xyz/api.php?action=query&format=json&formatversion=2&list=allpages&aplimit=max&apfilterredir=nonredirects&apnamespace=0&apcontinue={apcontinue}'''
            r = session.get(url, headers=headers)
            text = json.loads(r.text)
            pages = text['query']['allpages']
            for page in pages:
                titles.append(page['title'])
            apcontinue = text['continue']['apcontinue']
    except:
        pass
    return titles


def recent_pages(rcend):
    rcend_date = datetime.strptime(rcend, '%Y-%m-%dT%H:%M:%SZ')
    rcend_date = rcend_date - timedelta(hours=8)
    titles = []
    cookie = get_config()['wiki']['cookie']
    url = f'''https://hywiki.xyz/api.php?action=query&format=json&formatversion=2&list=recentchanges&rcdir=older&rcstart=now&rctype=edit|new&rclimit=max'''
    headers = {'cookie': cookie}
    session = requests.Session()
    r = session.get(url, headers=headers)
    text = json.loads(r.text)
    try:
        pages = text['query']['recentchanges']
        for page in pages:
            if datetime.strptime(page['timestamp'], '%Y-%m-%dT%H:%M:%SZ') > rcend_date:
                if page['title'] not in titles:
                    titles.append(page['title'])
        rccontinue = text['continue']['rccontinue']
        while True:
            url = f'''https://hywiki.xyz/api.php?action=query&format=json&formatversion=2&list=recentchanges&rcdir=older&rcstart=now&rctype=edit|new&rclimit=max&rccontinue={rccontinue}'''
            r = session.get(url, headers=headers)
            text = json.loads(r.text)
            pages = text['query']['recentchanges']
            for page in pages:
                if datetime.strptime(page['timestamp'], '%Y-%m-%dT%H:%M:%SZ') > rcend_date:
                    if page['title'] not in titles:
                        titles.append(page['title'])
            rccontinue = text['continue']['rccontinue']
    except:
        pass
    return titles


def rebuild():
    titles = all_pages()
    dataset = wiki(titles)
    data = []
    for i in range(len(dataset)):
        dataset[i] = str(dataset[i]).replace(
            '\n', ' ').replace('[', '').replace(']', '')
    for i in range(len(dataset)):
        data.append({"title": titles[i], "content": dataset[i]})
    with open('././data/wiki.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=4) + '\n')


def create_user_dict(dataset):
    user_dict = []
    for i in range(len(dataset)):
        user_dict.append(dataset[i]['title'])
    with open('./data/user_dict.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(user_dict) + '\n')


def update_wiki():
    if get_config()['wiki']['latest'] == "":
        rebuild()
    else:
        rcstart = get_config()['wiki']['latest']
        hash = get_config()['wiki']['hash']
        if hash != hashlib.md5(str(rcstart).encode('utf-8')).hexdigest():
            log(f"Hash changed, rebuilding", "EVENT")
            rebuild()
        else:
            titles = recent_pages(rcstart)
            if len(titles) == 0:
                log(f"No new pages", "EVENT")
                return
            dataset = wiki(titles)
            log(f"Updating {len(titles)} pages", "EVENT")
            with open('././data/wiki.json', encoding='utf-8') as f:
                try:
                    data = json.loads(f.read())
                except:
                    rebuild()
            for i in range(len(dataset)):
                dataset[i] = remove_wiki_tags(str(dataset[i]))
            for i in range(len(dataset)):
                if not if_in_data(data, titles[i]):
                    data.append({"title": titles[i], "content": dataset[i]})
                else:
                    for j in range(len(data)):
                        if data[j]['title'] == titles[i]:
                            data[j]['content'] = dataset[i]
            with open('././data/wiki.json', 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False, indent=4) + '\n')


def update():
    try:
        last_update = get_config()['wiki']['latest']
        last_update = datetime.strptime(last_update, '%Y-%m-%dT%H:%M:%SZ')
        now = datetime.now()
        delta = now - last_update
        log(
            f"Checking for update, time delta: {int(delta.days)+round(delta.seconds/864)/100} days", "EVENT")
        if delta > timedelta(hours=1):
            update_wiki()
            create_user_dict(json.loads(
                open('././data/wiki.json', encoding='utf-8').read()))
        change_latest(now.strftime('%Y-%m-%dT%H:%M:%SZ'))
        log(f"Update passed", "EVENT")
    except:
        log(f"Update failed", "CRITICAL")
        log(f"{sys.exc_info()}", "CRITICAL")


def get_content(title, dataset):
    for i in range(len(dataset)):
        if dataset[i]['title'] == title:
            if title not in get_config()['wiki']['blacklist']:
                return remove_wiki_tags(dataset[i]['content'])
            else:
                return None
    return None


def generate_reference(reference: list):
    new_reference = []
    cookie = get_config()['wiki']['cookie']
    for titles in reference:
        if titles != None and titles.strip() != '':
            try:
                url = f'''https://hywiki.xyz/api.php?action=shortenurl&format=json&url=https://hywiki.xyz/wiki/{quote(titles, safe='/:?=.')}'''
                headers = {'cookie': cookie}
                session = requests.Session()
                r = session.post(url, headers=headers)
                text = json.loads(r.text)
                new_reference.append(text['shortenurl']['shorturl'])
            except:
                new_reference.append(titles)
    return new_reference


def basic_query(prompt, history=[]):
    log(f"Querying", "INFO")
    url = f"http://127.0.0.1:{get_config()['llm']['port']}/default"
    payload = {
        "prompt": prompt,
        "history": history,
        "max_length": 3000
    }
    try:
        response = requests.post(url, json=payload)
        return json.dumps(response.json(), ensure_ascii=False)
    except:
        log(f"Query failed, Err:{response}", "ERROR")


def stream_query(prompt, history=[]):
    url = f"http://127.0.0.1:{get_config()['llm']['port']}/stream"
    payload = {
        "prompt": prompt,
        "history": history,
        "max_length": 3000
    }
    response = requests.post(url, json=payload, stream=True)
    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            sys.stdout.write("\r " + " " * 60 + "\r")
            sys.stdout.flush()
            response = str(chunk.decode('utf-8', errors='ignore')
                           ).removeprefix("data: ").strip()
            sys.stdout.write(f"<<< {response}")
            sys.stdout.flush()
    return response
