# Steps 3 and 5: an agent that discovers its tools from the MCP server.
# It never imports the tool functions: it asks the server for them at run time.
import asyncio
import json
import os
import sys
import time
from datetime import datetime
import litellm
from dotenv import load_dotenv
from litellm import acompletion
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
litellm.drop_params = True
MODEL = os.getenv("LLM_MODEL")

# sys.executable is the same Python that runs this file (the manual uses "python")
params = StdioServerParameters(command=sys.executable, args=["server.py"])
LOG = "evidence/tool_calls.jsonl"   # run from inside lab03/

SYSTEM_PROMPT = """You are a stock assistant for a community pharmacy.
Use the tools to look up stock, prices and expiry dates. Never guess numbers.
Prices are in GHS per pack. Only record a sale when the user says a sale was made.
Never oversell. If a tool refuses, tell the user why. Keep answers short."""


def summarise(text, limit=150):
    # Short one-line summary of a tool result for the log
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "..."


def log_call(name, args, result_text, ms):
    os.makedirs("evidence", exist_ok=True)
    entry = {"timestamp": datetime.now().isoformat(timespec="seconds"),
             "tool": name, "arguments": args,
             "result_summary": summarise(result_text), "duration_ms": ms}
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


async def call_model(messages, schemas):
    # One retry, as in Lab 2
    for attempt in range(2):
        try:
            resp = await acompletion(model=MODEL, messages=messages,
                                     tools=schemas, temperature=0)
            return resp.choices[0].message
        except Exception as e:
            print(f"Model error (attempt {attempt + 1}): {str(e)[:150]}")
    return None


async def run_agent(session, schemas, question, max_steps=6):
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}]
    for step in range(max_steps):
        msg = await call_model(messages, schemas)
        if msg is None:
            return "Stopped: the model could not be reached."
        if not msg.tool_calls:
            return msg.content
        messages.append(msg.model_dump())
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            print(f"  tool call: {name}({args})")
            start = time.perf_counter()
            result = await session.call_tool(name, args)   # the server runs the tool
            ms = round((time.perf_counter() - start) * 1000, 1)
            text = "\n".join(c.text for c in result.content if hasattr(c, "text")) or "[]"
            print(f"  result: {summarise(text)}")
            log_call(name, args, text, ms)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": text})
    return "Stopped: reached max_steps without finishing."


QUESTIONS = [
    "Do we have amoxicillin 500mg?",
    "Which items expire within 60 days?",
    "What do 2 packs of paracetamol 500mg cost?",
    "Do we have any inhalers, and how much is one?",
    "Sell 3 packs of ibuprofen 400mg.",                 # sale
    "Sell 20 packs of Artemether-Lumefantrine 80/480mg.",  # oversale (only 8 in stock)
]


async def main():
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            schemas = [{"type": "function", "function": {
                "name": t.name, "description": t.description,
                "parameters": t.inputSchema}} for t in tools]
            print("Tools discovered from the server:", [t.name for t in tools])

            questions = sys.argv[1:] or QUESTIONS   # pass your own question on the command line
            for q in questions:
                print("\nQuestion:", q)
                answer = await run_agent(session, schemas, q)
                print("Answer:", answer)


if __name__ == "__main__":
    asyncio.run(main())
