# DCIT403 Lab 3 Report (draft)

> Draft following the Lab Report Template. Fill the TODO parts from your own runs, rewrite in your own words, then export as `DCIT403_Lab03_<StudentID>.pdf`.

**Student name:** TODO
**Student ID:** TODO
**Lab number and title:** Lab 3: Percepts and Actions as Tools: Function Calling and MCP
**Lab repository link:** https://github.com/calebadjei-05/Intelligent-agent-lab2
**Date submitted:** TODO

## 1. Objective

This lab built a pharmacy stock assistant for a community pharmacy that answers questions such as "Do we have amoxicillin 500mg?", "Which items expire within 60 days?" and "What do 2 packs of paracetamol cost?", and records sales. The tools live on an MCP server, and an agent discovers and calls them through native function calling instead of the Lab 2 text protocol.

## 2. Concept and Classical Root

In the classical agent model, an agent perceives its environment through sensors and changes it through actuators. Here the environment is the stock file `data/pharmacy_stock.csv`. The read tools (`check_stock`, `search_items`, `list_expiring`) are sensors: their results come back to the model as tool messages, which are its percepts. The write tool `record_sale` is an actuator: it changes the world, so its mistakes have real effects. The list of tool schemas is the agent's knowledge of its own capabilities, and the MCP server is the environment interface in front of the data.

Native function calling keeps the same perceive, decide, act loop as the Lab 2 ReAct agent, but the API enforces the format (structured `tool_calls` with JSON arguments) instead of my regex parser. MCP is a protocol, not a model: the server exposes tools, the client discovers them at run time, and my code (not the model) executes them. (See `concept_check.md` for the four answers.)

## 3. Implementation

- [`server.py`](server.py): FastMCP server `pharmacy-stock` with four tools. Three read tools and one write tool.
- [`client_agent.py`](client_agent.py): starts the server over stdio, lists its tools, converts them to function-calling schemas and runs the agent loop with `acompletion`. Every tool call is logged to `evidence/tool_calls.jsonl` (timestamp, tool, arguments, result summary, duration in ms).
- [`function_calling.py`](function_calling.py): Step 1, one plain `check_stock` function described as a JSON schema, without MCP.
- [`react_via_mcp.py`](react_via_mcp.py): the Lab 2 ReAct agent with its tool list taken from the MCP server.

Key design decision: `record_sale` checks the request itself rather than trusting the prompt.

```python
if not isinstance(qty, int) or qty <= 0:
    return f"REFUSED: quantity must be a whole number above 0 (got {qty}). Stock unchanged."
...
if qty > in_stock:
    return (f"REFUSED: only {in_stock} packs of {row['item']} {row['strength']} in stock, "
            f"cannot sell {qty}. Stock unchanged.")
row["quantity"] = str(in_stock - qty)
save(rows)
```

It also refuses when the strength is missing or more than one item matches, so a vague request cannot sell the wrong product. Changes to the Lab 2 agent: the tool section of the prompt is generated from `list_tools()`, and `Action Input` must now be a JSON object because MCP tools take named arguments (Lab 2 tools took a single string).

## 4. Evidence

- `evidence/mcp_inspector.png`: the MCP Inspector connected to `pharmacy-stock`, showing all four tools and a successful `list_expiring(days=60)` call.
- `evidence/tool_calls.jsonl`: TODO, paste 2 or 3 lines after running `python client_agent.py` (six questions, including a sale and an oversale).
- `evidence/react_via_mcp.txt`: TODO, paste the trace after running `python react_via_mcp.py`.

## 5. Failure and Fix

TODO from your own runs. Describe one real wrong tool call (for example, the model passing `strength="500"` instead of `"500mg"`, calling `record_sale` for a price question, or calling `search_items` with a word that is not in the stock list such as "malaria") and how a clearer docstring or schema fixed it. Do not invent this: the rubric gives zero for an invented failure.

## 6. AI-Use Log

| Date | Lab | Tool | What I asked | What I used | What I changed or checked |
|---|---|---|---|---|---|
| 2026-11-25 | 3 | Claude Code (Claude, Anthropic) | Complete Lab 3 from the lab manual | Code in `lab03/`, concept-check answers, Inspector screenshot, this draft | TODO |

## 7. Project Link

Team repository: TODO
My contribution this week (one line): TODO
