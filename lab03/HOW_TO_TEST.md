# Lab 3: How to test (with expected output)

Run these in the Codespace, in order. Lines like `Processing request of type ...` are normal server messages.
The tool results below are exact; the model's wording in its answers will vary.

1. Check setup and key (from the repository root)

   ```bash
   python scripts/check_setup.py --call
   ```
   Expected: every check passes and one small model reply comes back. If a key is missing, add `GROQ_API_KEY` as a Codespaces secret and restart the Codespace.

2. Reset the stock data and go into the lab folder

   ```bash
   python scripts/refresh_dates.py
   cd lab03
   ```
   Expected: `wrote lab03/data/pharmacy_stock.csv (20 rows)`

3. Test the server's tools (no key needed)

   ```bash
   npx @modelcontextprotocol/inspector --cli python server.py --method tools/list
   ```
   Expected: JSON naming the four tools `check_stock`, `search_items`, `list_expiring`, `record_sale`.

4. Step 1: function calling without MCP

   ```bash
   python function_calling.py
   ```
   Expected:
   ```
   Tool call: check_stock({'item': 'amoxicillin', 'strength': '500mg'})
   Tool result: [{'item': 'Amoxicillin', 'strength': '500mg', ... 'quantity': '40' ...}]
   Final answer: Yes, we have 40 packs of Amoxicillin 500mg ...
   ```

5. Main agent through MCP (six questions, writes the tool-call log)

   ```bash
   python client_agent.py
   cat evidence/tool_calls.jsonl
   ```
   Expected: `Tools discovered from the server: ['check_stock', 'search_items', 'list_expiring', 'record_sale']`, then `Question:`, `tool call:` and `Answer:` lines for each question. Key results:
   - Sale: `SALE RECORDED: 3 x Ibuprofen 400mg ... GHS 36.00. 57 packs left.`
   - Oversale: `REFUSED: only 8 packs of Artemether-Lumefantrine 80/480mg in stock, cannot sell 20. Stock unchanged.`
   - The log has one line per tool call with `timestamp`, `tool`, `arguments`, `result_summary`, `duration_ms`.

6. Wednesday: Lab 2 ReAct agent using the MCP tools

   ```bash
   python react_via_mcp.py "Do we have amoxicillin 500mg?"
   ```
   Expected: `Thought:` / `Action: check_stock` / `Action Input: {"item": "amoxicillin", ...}` / `Observation:` with quantity 40, then `FINAL ANSWER: ...`. Saved to `evidence/react_via_mcp.txt`.

7. Save the evidence (step 5 really sold 3 packs, so reset the stock first)

   ```bash
   cd ..
   python scripts/refresh_dates.py
   git add lab03/evidence
   git commit -m "lab03: evidence from my runs"
   git push
   ```
