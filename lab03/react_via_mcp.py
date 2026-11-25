# Wednesday Part C: the Lab 2 ReAct agent, but it gets its tools from the MCP server
# instead of importing tools.py. Same text protocol and parser as Lab 2.
# What changed (see comments marked CHANGED):
#   1. The tool list in the prompt is built from session.list_tools(), not typed by hand.
#   2. Action Input must now be JSON arguments, because MCP tools take named arguments
#      (Lab 2 tools took one plain string).
#   3. The loop is async and runs tools with session.call_tool().
import asyncio
import json
import os
import re
import sys
import litellm
from dotenv import load_dotenv
from litellm import acompletion
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
litellm.drop_params = True
MODEL = os.getenv("LLM_MODEL")
params = StdioServerParameters(command=sys.executable, args=["server.py"])

# --- Parser (same as Lab 2) ---
ACTION_RE = re.compile(r"Action:\s*(\w+)\s*\nAction Input:\s*(.*)", re.DOTALL)


def parse(text):
    m = ACTION_RE.search(text)
    if not m:
        return None, None
    return m.group(1).strip(), m.group(2).strip()


# CHANGED: the tool section of the prompt is generated from the server's tool list
def build_prompt(tools):
    lines = []
    for t in tools:
        args = ", ".join(t.inputSchema.get("properties", {}).keys())
        first_line = (t.description or "").strip().splitlines()[0]
        lines.append(f"- {t.name}({args}): {first_line}")
    names = " | ".join(t.name for t in tools)
    return f"""You are a pharmacy stock assistant that solves problems step by step using tools.

Tools:
{chr(10).join(lines)}

You cannot call tools directly. Do not use function calling. Write everything as plain text.

On every step reply in exactly this format:
Thought: <your reasoning>
Action: {names} | finish
Action Input: <JSON object with the tool's arguments, e.g. {{"item": "amoxicillin", "strength": "500mg"}}, or the final answer if finish>

Never write an Observation yourself. Wait for it."""


async def call_model(messages):
    for attempt in range(2):
        try:
            resp = await acompletion(model=MODEL, messages=messages,
                                     temperature=0, stop=["Observation:"])
            return resp.choices[0].message.content or ""
        except Exception as e:
            print(f"Model error (attempt {attempt + 1}): {str(e)[:150]}")
    return ""


async def run_agent(session, tools, question, max_steps=6):
    tool_names = [t.name for t in tools]
    messages = [{"role": "system", "content": build_prompt(tools)},
                {"role": "user", "content": question}]
    trace = ["Question: " + question]
    for step in range(max_steps):
        text = await call_model(messages)
        if not text.strip():
            obs = "The model gave no usable reply. Reply with Thought, Action and Action Input."
            trace.append("Observation: " + obs)
            messages.append({"role": "user", "content": "Observation: " + obs})
            continue
        trace.append(text.strip())
        action, action_input = parse(text)
        if action is None:
            obs = "Format error. Reply with exactly: Thought, then Action, then Action Input."
        elif action == "finish":
            return action_input, trace
        elif action in tool_names:
            # CHANGED: Action Input is parsed as JSON and sent to the MCP server
            try:
                args = json.loads(action_input)
                result = await session.call_tool(action, args)
                obs = "\n".join(c.text for c in result.content if hasattr(c, "text")) or "[]"
            except json.JSONDecodeError:
                obs = 'Action Input must be a JSON object, e.g. {"item": "amoxicillin"}.'
        else:
            obs = f"Unknown action '{action}'. Use {', '.join(tool_names)} or finish."
        trace.append("Observation: " + str(obs))
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": "Observation: " + str(obs)})
    return "Stopped: reached max_steps without finishing.", trace


async def main():
    question = " ".join(sys.argv[1:]) or "Do we have amoxicillin 500mg?"
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            answer, trace = await run_agent(session, tools, question)
    print("\n".join(trace))
    print("FINAL ANSWER:", answer)
    os.makedirs("evidence", exist_ok=True)
    with open("evidence/react_via_mcp.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(trace) + "\nFINAL ANSWER: " + answer + "\n")


if __name__ == "__main__":
    asyncio.run(main())
