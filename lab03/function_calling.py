# Step 1: native function calling without MCP.
# One plain Python function, described to the model as a JSON schema.
import csv
import json
import os
import sys
# Use LiteLLM's built-in model price list instead of downloading it (avoids a timeout warning)
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
import litellm
from dotenv import load_dotenv
from litellm import completion

# Load .env from the repository root, whichever folder you run from
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
load_dotenv()
litellm.drop_params = True
MODEL = os.getenv("LLM_MODEL") or "groq/openai/gpt-oss-20b"
if not (os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY")):
    sys.exit("No API key found. Put GROQ_API_KEY=... in the .env file in the repository root "
             "(next to README.md), then run again.")


def assistant_message(msg):
    # Copy only role, content and tool_calls. Some providers (e.g. Groq) reject
    # extra fields such as reasoning text if we send the whole message back.
    return {"role": "assistant", "content": msg.content or "",
            "tool_calls": [{"id": tc.id, "type": "function",
                            "function": {"name": tc.function.name,
                                         "arguments": tc.function.arguments or "{}"}}
                           for tc in msg.tool_calls]}
HERE = os.path.dirname(os.path.abspath(__file__))   # the lab03 folder, so any working folder works
DATA = os.path.join(HERE, "data", "pharmacy_stock.csv")


def check_stock(item, strength=""):
    with open(DATA, newline="", encoding="utf-8") as f:
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
        messages.append(assistant_message(msg))
        for tc in msg.tool_calls or []:
            args = json.loads(tc.function.arguments)
            print(f"Tool call: {tc.function.name}({args})")
            try:
                result = TOOLS[tc.function.name](**args)
            except Exception as e:
                result = f"Tool error: {e}"
            print(f"Tool result: {result}")
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(result)})
        resp = completion(model=MODEL, messages=messages, tools=tool_schemas, temperature=0)

    print("Final answer:", resp.choices[0].message.content)
