import json

from openai import OpenAI
# from colorama import init, Fore
from wiki_utils import *
from functions import get_tools, dispatch_tool

CONFIG = get_config()

client = OpenAI(
    base_url=f"http://127.0.0.1:{CONFIG['llm']['port']}/v1",
    api_key="114514"
)

functions = get_tools()
conversation = []
params = dict(model="chatglm3", messages=[], stream=False)


def run_conversation(query: str, stream=False, functions=None, max_retry=5):
    global params
    params["messages"].append({"role": "user", "content": query})
    if functions:
        params["functions"] = functions
    response = client.chat.completions.create(**params)

    for _ in range(max_retry):
        if not stream:
            if response.choices[0].message.function_call:
                function_call = response.choices[0].message.function_call
                log(f"Function Call Response: {function_call.model_dump()}", "INFO")

                function_args = json.loads(function_call.arguments)
                tool_response = dispatch_tool(
                    function_call.name, function_args)
                log(f"Tool Call Response: {tool_response}", "INFO")

                params["messages"].append(response.choices[0].message)
                params["messages"].append(
                    {
                        "role": "function",
                        "name": function_call.name,
                        "content": tool_response,  # 调用函数返回结果
                    }
                )
            else:
                reply = response.choices[0].message.content
                print(f"<<< {reply}")
                return

        else:
            output = ""
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                # print(Fore.BLUE + content, end="", flush=True)
                output += content

                if chunk.choices[0].finish_reason == "stop":
                    return

                elif chunk.choices[0].finish_reason == "function_call":
                    print("\n")

                    function_call = chunk.choices[0].delta.function_call
                    log(
                        f"Function Call Response: {function_call.model_dump()}", "INFO")

                    function_args = json.loads(function_call.arguments)
                    tool_response = dispatch_tool(
                        function_call.name, function_args)
                    log(f"Tool Call Response: {tool_response}", "INFO")

                    params["messages"].append(
                        {
                            "role": "assistant",
                            "content": output
                        }
                    )
                    params["messages"].append(
                        {
                            "role": "function",
                            "name": function_call.name,
                            "content": tool_response,
                        }
                    )

                    break

        response = client.chat.completions.create(**params)


if __name__ == "__main__":
    update()
    while True:
        query = input(">>> ")
        if query == "clear":
            params["messages"] = []
        else:
            run_conversation(query, functions=functions)
