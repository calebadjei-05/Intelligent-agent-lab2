# Step 1: native function calling without MCP.
# One plain Python function, described to the model as a JSON schema.
import csv
import json
import os
import litellm
from dotenv import load_dotenv
from litellm import completion

load_dotenv()
litellm.drop_params = True
MODEL = os.getenv("LLM_MODEL")
DATA = "data/pharmacy_stock.csv"   # run from inside lab03/


def check_stock(item, strength=""):
    with open(DATA, newline="") as f:
        rows = [r for r in csv.DictReader(f) if item.lower() in r["item"].lower()]
    if strength:
        rows = [r for r in rows if strength.lower() in r["strength"].lower()]
    return rows


TOOLS = {"check_stock": check_stock}

tool_schemas = [{
    "type": "function",
    "function": {
        "name": "check_stock",
        "description": "Return pharmacy stock rows whose item name contains item "
                       "(and strength, if given). Use it to answer 'Do we have X?'.",
        "parameters": {
            "type": "object",
            "properties": {
                "item": {"type": "string", "description": "Medicine name, e.g. amoxicillin"},
                "strength": {"type": "string", "description": "Optional strength, e.g. 500mg"},
            },
            "required": ["item"],
        },
    },
}]

if __name__ == "__main__":
    messages = [
        {"role": "system", "content": "You are a pharmacy stock assistant. Use the tools to check stock."},
        {"role": "user", "content": "Do we have amoxicillin 500mg?"},
    ]
    resp = completion(model=MODEL, messages=messages, tools=tool_schemas, temperature=0)

    # Loop from the manual: run every tool call and send the result back
    while resp.choices[0].message.tool_calls:
        msg = resp.choices[0].message
        messages.append(msg.model_dump())
        for tc in msg.tool_calls or []:
            args = json.loads(tc.function.arguments)
            print(f"Tool call: {tc.function.name}({args})")
            result = TOOLS[tc.function.name](**args)
            print(f"Tool result: {result}")
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(result)})
        resp = completion(model=MODEL, messages=messages, tools=tool_schemas, temperature=0)

    print("Final answer:", resp.choices[0].message.content)
