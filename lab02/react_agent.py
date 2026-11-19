import os
import re
import litellm
from dotenv import load_dotenv
from litellm import completion
from tools import calculator, wiki_lookup

load_dotenv()
litellm.drop_params = True
MODEL = os.getenv("LLM_MODEL")

# --- Parser (from the manual) ---
ACTION_RE = re.compile(r"Action:\s*(\w+)\s*\nAction Input:\s*(.*)", re.DOTALL)

def parse(text):
    m = ACTION_RE.search(text)
    if not m:
        return None, None
    return m.group(1).strip(), m.group(2).strip()

# --- System prompt (my suggestion; the format lines come from the manual) ---
SYSTEM_PROMPT = """You are a helpful assistant that solves problems step by step using tools.

Tools:
- calculator: evaluates arithmetic such as 4*185 + 3*95
- wiki_lookup: gets a short Wikipedia summary for a page title such as Bono East Region

You cannot call tools directly. Do not use function calling. Write everything as plain text.

On every step reply in exactly this format:
Thought: <your reasoning>
Action: calculator | wiki_lookup | finish
Action Input: <input for the tool, or the final answer if finish>

Never write an Observation yourself. Wait for it."""

TOOLS = {"calculator": calculator, "wiki_lookup": wiki_lookup}

# --- Model call with one retry (my suggestion) ---
def call_model(messages):
    for attempt in range(2):
        try:
            resp = completion(model=MODEL, messages=messages,
                              temperature=0, stop=["Observation:"])
            return resp.choices[0].message.content or ""
        except Exception as e:
            print(f"Model error (attempt {attempt + 1}): {str(e)[:150]}")
    return ""

# --- The loop (my suggestion) ---
def run_agent(question, max_steps=6):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    trace = ["Question: " + question]
    for step in range(max_steps):
        text = call_model(messages)
        if not text.strip():
            obs = "The model gave no usable reply. Reply with Thought, Action and Action Input."
            trace.append("Observation: " + obs)
            messages.append({"role": "user", "content": "Observation: " + obs})
            continue
        trace.append(text.strip())
        action, action_input = parse(text)
        if action is None:
            obs = ("Format error. Reply with exactly: Thought, then Action, "
                   "then Action Input.")
        elif action == "finish":
            return action_input, trace
        elif action in TOOLS:
            obs = TOOLS[action](action_input)
        else:
            obs = f"Unknown action '{action}'. Use calculator, wiki_lookup or finish."
        trace.append("Observation: " + str(obs))
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": "Observation: " + str(obs)})
    return "Stopped: reached max_steps without finishing.", trace

# --- Save a trace file (my suggestion) ---
def save_trace(n, trace, answer):
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"trace_{n}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(trace) + "\nFINAL ANSWER: " + answer + "\n")

# --- Run the six questions (my suggestion) ---
if __name__ == "__main__":
    QUESTIONS = [
        "I have GHS 1,200. I want 4 bags of rice at GHS 185 each and "
        "3 gallons of oil at GHS 95 each. How much will I have left?",
        "What is the capital of the Bono East Region? Also, what is 15 * 240?",
        "Look up Makola Market on Wikipedia, then work out the cost of 12 bags of rice at GHS 185 each.",
        "Tell me about the Wikipedia page Zorblax Mountain Spaceport.",
        "What is the opposite of cold?",
        "rice oil money left how much 1200 4 3",
    ]
    for n, q in enumerate(QUESTIONS, start=1):
        answer, trace = run_agent(q)
        print("\n".join(trace))
        print("FINAL ANSWER:", answer)
        print("=" * 40)
        save_trace(n, trace, answer)