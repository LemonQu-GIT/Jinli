<div align=center><img src="image/header_new.png"></div>

本项目名取自于 华育中学鱼池 中的 **锦鲤**

## 介绍

本项目通过 [ChatGLM3](https://github.com/THUDM/ChatGLM3) 对华育中学 QQ 校群及 [HYWiki](https://hywiki.xyz/wiki) 项目进行分析处理

本项目隶属于 Huayu Dataverse，简称HYDV，[21159](https://hywiki.xyz/wiki/21159) (https://github.com/AntonyJia159) 于2023年11月5日提出的项目概念。指与[华育](https://hywiki.xyz/wiki/华育)、[华育校群](https://hywiki.xyz/wiki/校群)（[校群史](https://hywiki.xyz/wiki/校群史)）、[华育维基](https://hywiki.xyz/wiki/华育维基史) 等有关的数据收集、管理、分析体系

⭐ 由于此项目的依赖性，模型只支持 [chatglm3-6b](https://huggingface.co/THUDM/chatglm3-6b)

## 代码

由于 HuayuChatting 的代码特殊性，”采取了—种很买椟还珠的做法，完全丢弃了"聊天”，只在乎“记录”那一行“。不过显然只把“记录”给 LLM 进行处理是几乎毫无意义的。本项目重写了 HuayuChatting 的代码，使其能”聊天“和记录”两者兼得

现有功能如下，之后将逐步加入新功能

| 功能                    | HuayuChatting | HuayuGLM |
| ----------------------- | ------------- | -------- |
| age_chart               | ✅             | ❌        |
| chatting_part           | ✅             | ✅        |
| day(chart\|table)       | ✅             | ❌        |
| week(chart\|table\|pie) | ✅             | ❌        |
| month(chart\|table)     | ✅             | ✅        |
| decay_chart             | ✅             | ❌        |
| at_chart                | ❌             | ✅        |
| search_message          | ❌             | ✅        |
| word_trend              | ❌             | ✅        |
| name_history            | ❌             | ✅        |

除校群聊天记录外，加入了 HYWiki 以便更好查询信息

> 若想改写该部分的代码，需确保目标 Wiki 是基于 [MediaWiki](https://m.mediawiki.org/wiki/MediaWiki) 构建的

为了本地易修改性 ~~不会使用数据库导致的~~，Wiki数据采用 JSON 存储，每次运行时会访问目标网站查询是否需要更新

## 部署

本项目在 Windows11 Python 3.9.16 成功部署

### config_template.json

```json
{
    "wiki": {
        "cookie": "",
        "latest": "",
        "hash": "",
        "blacklist": [],
        "threshold": 0.05,
        "max_length": 2000
    },
    "llm": {
        "model": "THUDM/chatglm3-6b",
        "port": 8000,
        "quantize": 8,
        "max_length": 2000
    }
}
```

复制`config_template.json`为`config.json`

打开目标 wiki 网址，获取 cookie 并填入 `"cookie": ""` 一项中 (可自行搜索如何获取 cookie)

若不想在运行时获取某一较为无用 (~~若至~~) 的页面，可将页面的标题输入`"blacklist": []`中

### Data

```
HuayuGLM 
└─data
       log.txt # QQ群聊天记录
       schoolID.json # 会自动生成
       user_dict.txt # 会自动生成
       wiki.json # 会自动生成
```

`log.txt` 可以在 QQ 群中导出聊天记录，并将开头的

```
消息记录（此消息记录为文本格式，不支持重新导入）

================================================================
消息分组:???
================================================================
消息对象: ???
================================================================

```

删去并保存为 `UTF-8` 格式

### 环境

 在部署前建议先成功部署 [ChatGLM3](https://github.com/THUDM/ChatGLM3)

```bash
pip install -r requirements.txt #requirements-py3.9.txt
```

之后运行 ChatGLM3 API 以及主程序

```bash
python openai_api.py
python main.py
```

## Reference

* HYWiki https://hywiki.xyz/wiki (23564)

* HuayuChatting https://github.com/jack20081117/HuayuChatting (24885)
* ChatGLM3 https://github.com/THUDM/ChatGLM3
* ChatGLM-6B-Engineering https://github.com/LemonQu-GIT/ChatGLM-6B-Engineering