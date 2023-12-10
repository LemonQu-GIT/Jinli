from qq_utils import *
from datetime import datetime
from datetime import datetime, timedelta
from tqdm import tqdm
from copy import deepcopy
from types import GenericAlias
from typing import get_origin, Annotated
import re
import inspect
import traceback
import json
import json
import jieba
import logging
from wiki_utils import *
from qq_utils import *

_TOOL_HOOKS = {}
_TOOL_DESCRIPTIONS = {}
content = parse_log(False)


def register_tool(func: callable):
    tool_name = func.__name__
    tool_description = inspect.getdoc(func).strip()
    python_params = inspect.signature(func).parameters
    tool_params = []
    for name, param in python_params.items():
        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            raise TypeError(f"Parameter `{name}` missing type annotation")
        if get_origin(annotation) != Annotated:
            raise TypeError(
                f"Annotation type for `{name}` must be typing.Annotated")

        typ, (description, required) = annotation.__origin__, annotation.__metadata__
        typ: str = str(typ) if isinstance(typ, GenericAlias) else typ.__name__
        if not isinstance(description, str):
            raise TypeError(f"Description for `{name}` must be a string")
        if not isinstance(required, bool):
            raise TypeError(f"Required for `{name}` must be a bool")

        tool_params.append(
            {
                "name": name,
                "description": description,
                "type": typ,
                "required": required,
            }
        )
    tool_def = {
        "name": tool_name,
        "description": tool_description,
        "params": tool_params,
    }

    # print("[registered tool] " + pformat(tool_def))
    _TOOL_HOOKS[tool_name] = func
    _TOOL_DESCRIPTIONS[tool_name] = tool_def

    return func


def dispatch_tool(tool_name: str, tool_params: dict) -> str:
    if tool_name not in _TOOL_HOOKS:
        return f"Tool `{tool_name}` not found. Please use a provided tool."
    tool_call = _TOOL_HOOKS[tool_name]
    try:
        ret = tool_call(**tool_params)
    except:
        ret = traceback.format_exc()
    return str(ret)


def get_tools() -> dict:
    return deepcopy(_TOOL_DESCRIPTIONS)


@register_tool
def get_at_someone(
    query: Annotated[str, "需要查找的这个人的学号（通常为五到六位数字）或是qq号，输入为字符串", True],
    delta: Annotated[float, "容差值，通常为0.005", True] = 0.005,
) -> str:
    """
    Get the count of the times that someone @ the student
    """
    def get_name_history(inpt: str):
        name = ""
        history = []
        if 5 <= len(inpt) <= 6:
            schoolID = inpt
            pbar = tqdm(content)
            pbar.set_description("Iterating content")
            for i in pbar:
                if i["schoolID"] == schoolID:
                    if i["name"] != name:
                        name = i["name"]
                        history.append(i["name"])
        else:
            qq_number = inpt
            pbar = tqdm(content)
            pbar.set_description("Iterating content")
            for i in pbar:
                if i["qq_number"] == qq_number:
                    if i["name"] != name:
                        name = i["name"]
                        history.append(i["name"])
        return history

    def get_be_at(target: str):  # 谁@了目标
        history = []
        pbar = tqdm(content)
        pbar.set_description("Iterating content")
        target_used_name = get_name_history(target)
        for i in pbar:
            message = i["message"]
            if "@" in message:
                for names in target_used_name:
                    if names in message:
                        history.append(i["qq_number"])
        return history

    trends = get_be_at(str(query))
    labels = []
    sizes = []
    for index in trends:
        if index in labels:
            sizes[labels.index(index)] += 1
        else:
            labels.append(index)
            sizes.append(1)

    with open("./data/schoolID.json", "r", encoding="utf-8") as f:
        id_dict = json.loads(f.read())
        f.close()

    for qq_number in labels:
        if qq_number in id_dict:
            labels[labels.index(qq_number)] = id_dict[qq_number]

    size_sum = sum(sizes)

    for i in range(len(sizes)):
        if sizes[i] / size_sum < delta:
            sizes[i] = 0
            labels[i] = ""

    for i in range(len(sizes)):
        try:
            sizes.remove(0)
            labels.remove("")
        except:
            break
    at_implements = {}
    for i in range(len(labels)):
        at_implements[labels[i]] = sizes[i]
    # sort the dict by value
    at_implements = dict(
        sorted(at_implements.items(), key=lambda d: d[1], reverse=True)
    )
    return str(at_implements)[:get_config()['llm']['max_length']]


@register_tool
def get_conversation(
    arguments_: Annotated[dict, "参与此次对话的同学的学号或是qq号，以及此人发言所在本次对话片段中所占的比例，通常为0.25，输入应为字典类型，如{'学号1': 0.25, '学号2': 0.25}", True],
    time_: Annotated[list,
                     "所筛选的聊天片段，为列表格式，格式为[%Y-%m-%d %H:%M:%S,%Y-%m-%d %H:%M:%S]，若是全部时间段则回复[-1,-1]", True]
) -> str:
    """
    Get the conversation between the students in `arguments_` in the time period `time_`, more often used for getting the conversation or argument between several students
    """
    chattingAllTime = []
    chattingSTTime1 = []
    chattingSTTime2 = []
    arguments = []
    pbar = tqdm(content)
    pbar.set_description("Iterating content")
    old_time = datetime.strptime(content[0]["date"], "%Y-%m-%d %H:%M:%S")
    start_time = datetime.strptime(content[0]["date"], "%Y-%m-%d %H:%M:%S")
    part_id = []
    for msg in pbar:
        time = datetime.strptime(msg["date"], "%Y-%m-%d %H:%M:%S")
        if time - old_time < timedelta(minutes=3):
            part_id.append(msg["qq_number"])
            old_time = datetime.strptime(msg["date"], "%Y-%m-%d %H:%M:%S")
        else:
            chattingSTTime1.append(start_time.strftime("%Y-%m-%d %H:%M:%S"))
            chattingAllTime.append(part_id)
            chattingSTTime2.append(old_time.strftime("%Y-%m-%d %H:%M:%S"))
            part_id = []
            old_time = datetime.strptime(msg["date"], "%Y-%m-%d %H:%M:%S")
            start_time = old_time
    chattingSTTime = [chattingSTTime2, chattingSTTime1]

    for i in range(len(chattingAllTime)):
        if chattingAllTime[i] == []:
            chattingAllTime[i] = ["other"]
            chattingSTTime[0][i] = "other"

    for i in range(len(chattingAllTime)):
        try:
            chattingSTTime[0].remove("other")
            chattingAllTime.remove("other")
        except:
            break

    def require(sTime, tTime, *args):
        length = len(args)
        schoolIDs = []
        s2pDict = {}
        return_list = []
        for id in range(0, length, 2):
            schoolID = args[id]
            probability = args[id + 1]
            schoolIDs.append(schoolID)
            s2pDict[schoolID] = probability
        situations = 0
        parts = len(chattingAllTime)
        for partId in range(parts):
            if sTime != -1 or tTime != -1:
                if (
                    chattingSTTime[0][partId] < sTime
                    or chattingSTTime[1][partId] > tTime
                ):
                    continue
            correct = True
            chattingEachPart = chattingAllTime[partId]
            partlength = len(chattingEachPart)
            if partlength <= 10:
                continue
            s2fDict = {}
            for schoolID in chattingEachPart:
                if schoolID == "other":
                    continue
                if not schoolID in s2fDict:
                    s2fDict[schoolID] = 0
                s2fDict[schoolID] += 1
            for schoolID in s2pDict:
                if not schoolID in s2fDict:
                    correct = False
                    break
                if s2fDict[schoolID] / partlength <= s2pDict[schoolID]:
                    correct = False
                    break
            if correct:
                situations += 1
                start = chattingSTTime[1][partId]
                end = chattingSTTime[0][partId]
                return_list.append([start, end])
        return return_list

    keys = list(arguments_.keys())
    for i in range(len(keys)):
        if 5 <= len(keys[i]) <= 6:
            keys[i] = schoolID_qqnumber(keys[i])

    values = list(arguments_.values())
    for i in range(len(keys)):
        arguments.append(keys[i])
        arguments.append(values[i])
    ret = require(time_[0], time_[1], *arguments)
    return str(ret)[:get_config()['llm']['max_length']]


@register_tool
def get_search_message(
    inpt: Annotated[list, "同学的学号（通常为五到六位数字）或是qq号，为列表格式，为['21159','25266']，若是全体同学则输入为['all']", True],
    regx_expr: Annotated[str, "查找的聊天内容需要包含的字词 ", True],
) -> str:
    """
    Using regular expression to search the message that matches `regx_expr` of a students `inpt`'s message, need to generate the regular expression from user's input, more often used for searching a specify message instead of a conversation
    """
    rep = re.compile(regx_expr)
    ret = []
    if inpt == ["all"]:
        for i in content:
            if rep.search(i["message"]) != None:
                ret.append(i)
    else:
        for students in inpt:
            if 5 <= len(students) <= 6:
                for i in content:
                    if rep.search(i["message"]) != None and i["schoolID"] == students:
                        ret.append(i)
            else:
                for i in content:
                    if rep.search(i["message"]) != None and i["qq_number"] == students:
                        ret.append(i)
    new_ret = []
    for i in range(len(ret)):
        new_ret.append([ret[i]["date"], ret[i]["message"]])
    return str(new_ret)[:get_config()['llm']['max_length']]


@register_tool
def get_word_trend_times(trends: Annotated[str, '需要查找的字词', True]) -> str:
    """
    Get the count of the word `query` in each month
    """
    def get_trend(query: str):
        history = []
        pbar = tqdm(content)
        pbar.set_description("Iterating content")
        for i in pbar:
            message = i["message"]
            if query in message:
                history.append([message, i["date"]])
        return history

    history = get_trend(str(trends))
    counts = {}
    for item in history:
        date_time = datetime.strptime(item[1], "%Y-%m-%d %H:%M:%S")
        year = date_time.year
        month = date_time.month
        key = str(year) + "-" + str(month)
        if key in counts:
            counts[key] += 1
        else:
            counts[key] = 1
    return str(counts)[:get_config()['llm']['max_length']]


@register_tool
def get_word_trend_students(query: Annotated[str, '需要查找的字词', True], delta: Annotated[float, "容差值，通常为0.005", True] = 0.005,) -> str:
    """
    Get the count of different students that use the word `query` in all months
    """
    def get_trend(query: str, enable_re: bool = False):
        history = []
        pbar = tqdm(content)
        pbar.set_description("Iterating content")
        for i in pbar:
            message = i["message"]
            if enable_re:
                rep = re.compile(query)
                if rep.search(message) != None:
                    history.append(i["qq_number"])
            else:
                if query in message:
                    history.append(i["qq_number"])
        return history

    trends = get_trend(str(query), True)
    labels = []
    sizes = []
    for index in trends:
        if index in labels:
            sizes[labels.index(index)] += 1
        else:
            labels.append(index)
            sizes.append(1)

    with open("./data/schoolID.json", "r", encoding="utf-8") as f:
        id_dict = json.loads(f.read())
        f.close()

    for qq_number in labels:
        if qq_number in id_dict:
            labels[labels.index(qq_number)] = id_dict[qq_number]

    size_sum = sum(sizes)

    for i in range(len(sizes)):
        if sizes[i] / size_sum < delta:
            sizes[i] = 0
            labels[i] = ""

    for i in range(len(sizes)):
        try:
            sizes.remove(0)
            labels.remove("")
        except:
            break
    ret = {}
    for i in range(len(labels)):
        ret[labels[i]] = sizes[i]
    return str(ret)[:get_config()['llm']['max_length']]


@register_tool
def get_name_history(
        inpt: Annotated[str, '同学的学号（通常为五到六位数字）或是qq号', True]
) -> str:
    """
    The history of the student's ID or qq number
    """
    if not isinstance(inpt, str):
        raise TypeError("SchoolID or qq number must be a string")
    name = ""
    history = []
    if 5 <= len(inpt) <= 6:
        schoolID = inpt
        for i in content:
            if i["schoolID"] == schoolID:
                if i["name"] != name:
                    name = i["name"]
                    history.append({"name": i["name"], "date": i["date"]})
    else:
        qq_number = inpt
        for i in content:
            if i["qq_number"] == qq_number:
                if i["name"] != name:
                    name = i["name"]
                    history.append({"name": i["name"], "date": i["date"]})
    return str(history)[:get_config()['llm']['max_length']]


@register_tool
def get_wiki(
        title: Annotated[str, 'The query string', True],
) -> str:
    """
    Get the detailed information of `query` on wiki
    """
    jieba.setLogLevel(logging.INFO)
    enable_history = False
    with open('././data/wiki.json', 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    def cut_dataset(dataset):
        jieba.load_userdict('./data/user_dict.txt')
        new_dataset = {}
        for i in range(len(dataset)):
            new_dataset[dataset[i]['title']] = jieba.lcut_for_search(
                dataset[i]['content'])
        return new_dataset

    cut_data = cut_dataset(dataset)

    def get_count(query):
        log(f"Counting {query}", "INFO")
        count = {}
        keys = list(cut_data.keys())
        values = list(cut_data.values())
        for i in range(len(keys)):
            count[keys[i]] = 0
            for j in range(len(values[i])):
                if values[i][j] == query:
                    count[keys[i]] += 1
        count_keys = list(count.keys())
        count_values = list(count.values())
        for i in range(len(count_keys)):
            if count_values[i] == 0:
                del count[count_keys[i]]
        count = dict(
            sorted(count.items(), key=lambda item: item[1], reverse=True))
        return count

    def get_rank(query):
        log(f"Ranking {query}", "INFO")
        count = get_count(query)
        all_count = sum(count.values())
        for key in count:
            count[key] /= all_count
        return count

    def normalize_query(prompt):
        embedding = []
        jieba.load_userdict('./data/user_dict.txt')
        cut = jieba.lcut(prompt)
        log(f"Embedding query: {prompt}", "INFO")
        for c in cut:
            content = get_content(c, dataset)
            if content != None:
                embedding.append({"title": c, "content": content, "rank": 1})
            else:
                rank_list = get_rank(c)
                for i in range(len(rank_list)):
                    rank_key = get_content(list(rank_list.keys())[i], dataset)
                    if list(rank_list.values())[i] > get_config()['wiki']['threshold'] and rank_key != None:
                        if not if_in_data(embedding, rank_list.keys()):
                            embedding.append({"title": list(rank_list.keys())[
                                i], "content": rank_key, "rank": list(rank_list.values())[i]})
        for i in range(len(embedding)):
            for j in range(i+1, len(embedding)):
                if embedding[i]['title'] == embedding[j]['title']:
                    del embedding[j]
                    break
        return embedding, cut

    def embedding_answer(embedding, cut, max_length=2048):
        log(f"Embedding answer, max_length: {max_length}", "INFO")
        answer = []
        reference = []
        max_rank_count = 0
        word_last = max_length
        for i in range(len(embedding)):
            if embedding[i]['rank'] == 1:
                max_rank_count += 1
        for i in range(len(embedding)):
            additional = f"{embedding[i]['title']}，{embedding[i]['content']}"
            if embedding[i]['rank'] == 1:
                if len(embedding[i]['content']) <= int(max_length/max_rank_count):
                    answer.append(additional)
                    reference.append(embedding[i]['title'])
                    word_last -= len(additional)
                    if word_last <= 0:
                        return answer, reference
                else:
                    answer.append(additional[:int(max_length/max_rank_count)])
                    reference.append(embedding[i]['title'])
                    word_last -= len(additional[:int(max_length/max_rank_count)])
                    if word_last <= 0:
                        return answer, reference
            else:
                if len(embedding[i]['content']) <= word_last:
                    if word_last >= 0 or answer == []:
                        answer.append(additional)
                        reference.append(embedding[i]['title'])
                        word_last -= len(additional)
                    else:
                        return answer, reference
                else:
                    if word_last >= 0 or answer == []:
                        answer.append(additional[:word_last])
                        reference.append(embedding[i]['title'])
                        word_last -= len(additional[:word_last])
                    else:
                        return answer, reference
            if word_last != 0:
                log(
                    f"Word last: {word_last} for {embedding[i]['title']}", "INFO")
        loss = calculate_loss(embedding, answer, cut)
        log(f"Loss: {loss}", "INFO")
        return answer, reference

    def calculate_loss(embedding, answer, cut):
        embedding_loss = {}
        wiki_loss = {}
        for c in cut:
            raw_count = 0
            ans_count = 0
            wiki_count = 0
            for i in range(len(embedding)):
                raw_count += str(embedding[i]['content']).count(c)
            for i in range(len(dataset)):
                wiki_count += str(dataset[i]['content']).count(c)
            for i in range(len(answer)):
                ans_count += str(answer[i]).count(c)
            try:
                embedding_loss[c] = max((raw_count - ans_count)/raw_count, 0)
                wiki_loss[c] = max((wiki_count - ans_count)/wiki_count, 0)
            except ZeroDivisionError:
                embedding_loss[c] = 0
                wiki_loss[c] = 0
        return {"embedding": embedding_loss, "wiki": wiki_loss}
    embedding, cut = normalize_query(title)
    embed, reference = embedding_answer(
        embedding=embedding, cut=cut, max_length=get_config()['wiki']['max_length'])
    embeddings = ('\n'.join(embed)).strip()
    new_reference = []
    for titles in reference:
        new_reference.append(titles.strip())
    log(f"Reference: {generate_reference(new_reference)}", "INFO")
    if embeddings != '':
        prompt = f'''内容：\'\'\'{embeddings[:get_config()['wiki']['max_length']].strip()}\'\'\'，引用了{new_reference}的词条'''
    else:
        prompt = f'''未找到相关信息'''
    return str(prompt)


@register_tool
def get_month_message_count_all() -> str:
    '''
    Get the count of the message of each month of all students instead of a specify student
    '''
    counts = {}
    pbar = tqdm(content)
    pbar.set_description('Iterating')
    for item in pbar:
        date_time = item['date']
        date_time = datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S')
        year = date_time.year
        month = date_time.month
        key = str(year) + '-' + str(month)
        if key in counts:
            counts[key] += 1
        else:
            counts[key] = 1
    return str(counts)[:get_config()['llm']['max_length']]


@register_tool
def get_student_message_count(
    student: Annotated[str, '学生的学号或qq号', True]
) -> str:
    '''
    Get the count of the message which a specify student sent in all months
    '''
    count = {}
    if 5 <= len(student) <= 6:
        for i in content:
            if i['schoolID'] == student:
                date = datetime.strptime(i['date'], '%Y-%m-%d %H:%M:%S')
                key = str(date.year) + '-' + str(date.month)
                if key in list(count.keys()):
                    count[key] += 1
                else:
                    count[key] = 1
    else:
        for i in content:
            if i['qq_number'] == student:
                date = datetime.strptime(i['date'], '%Y-%m-%d %H:%M:%S')
                key = str(date.year) + '-' + str(date.month)
                if key in list(count.keys()):
                    count[key] += 1
                else:
                    count[key] = 1
    return str(count)[:get_config()['llm']['max_length']]


@register_tool
def get_message_range(
    student: Annotated[list, '学生的学号或qq号', True],
    time: Annotated[list,
                    '所筛选的聊天片段，为列表格式，格式为[%Y-%m-%d %H:%M:%S,%Y-%m-%d %H:%M:%S]，若是全部时间段则回复[-1,-1]', True]
) -> str:
    """
    Get the message of a specify student message or some students' conversation in a specify time period
    """
    message = get_message_range(time[0], time[1], content)
    ret = []
    for i in range(len(message)):
        if message[i]['schoolID'] in student or message[i]['qq_number'] in student:
            ret.append(message[i])
    return str(ret)[:get_config()['llm']['max_length']]
