from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr
import time
from collections import defaultdict, deque

load_dotenv(override=True)

# ── Cost and abuse limits ─────────────────────────────────────────────────────
# This chatbot is public and every message is paid for with my OpenAI key, so cap
# everything a visitor (or a script) can make it spend.
MAX_MESSAGE_CHARS = 2000        # longest message a visitor can send
MAX_HISTORY_MESSAGES = 20       # only the most recent turns are sent back to OpenAI
MAX_REPLY_TOKENS = 600          # longest answer
MAX_TOOL_ROUNDS = 4             # tool-calling steps per message (stops runaway loops)
PER_VISITOR_LIMIT = (15, 600)   # 15 messages per 10 minutes per visitor
DAILY_LIMIT = 300               # all visitors together, per day
MAX_PUSHES_PER_HOUR = 20        # phone notifications

_visitor_hits = defaultdict(deque)
_daily = {"day": None, "count": 0}
_pushes = deque()

def _rate_limited(visitor):
    now = time.time()
    hits = _visitor_hits[visitor]
    limit, window = PER_VISITOR_LIMIT
    while hits and now - hits[0] > window:
        hits.popleft()
    today = time.strftime("%Y-%m-%d")
    if _daily["day"] != today:
        _daily.update(day=today, count=0)
    if len(hits) >= limit or _daily["count"] >= DAILY_LIMIT:
        return True
    hits.append(now)
    _daily["count"] += 1
    return False

def push(text):
    now = time.time()
    while _pushes and now - _pushes[0] > 3600:
        _pushes.popleft()
    if len(_pushes) >= MAX_PUSHES_PER_HOUR:
        return
    _pushes.append(now)
    try:
        requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": os.getenv("PUSHOVER_TOKEN"),
                "user": os.getenv("PUSHOVER_USER"),
                "message": str(text)[:1000],
            },
            timeout=10,
        )
    except requests.RequestException as e:
        print(f"Pushover failed: {e}", flush=True)

def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question}")
    return {"recorded": "ok"}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            }
            ,
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}]

# Only these functions can ever be called by the model
TOOL_FUNCTIONS = {
    "record_user_details": record_user_details,
    "record_unknown_question": record_unknown_question,
}

class Me:

    def __init__(self):
        self.openai = OpenAI()
        self.name = "Brian Athey"
        reader = PdfReader("me/Athey_Brian_Resume.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        with open("me/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()

    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            print(f"Tool called: {tool_name}", flush=True)
            tool = TOOL_FUNCTIONS.get(tool_name)
            try:
                arguments = json.loads(tool_call.function.arguments)
                result = tool(**arguments) if tool else {"error": "unknown tool"}
            except (ValueError, TypeError) as e:
                result = {"error": f"bad arguments: {e}"}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results

    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. "

        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt

    def chat(self, message, history, request: gr.Request = None):
        visitor = getattr(getattr(request, "client", None), "host", None) or "unknown"
        if _rate_limited(visitor):
            return "Thanks for all the questions! I've reached my limit for now. Please try again a little later, or reach me on LinkedIn."
        message = str(message)[:MAX_MESSAGE_CHARS]
        recent = [{"role": h["role"], "content": str(h["content"])[:MAX_MESSAGE_CHARS]}
                  for h in (history or [])[-MAX_HISTORY_MESSAGES:] if isinstance(h, dict) and h.get("role") in ("user", "assistant")]
        messages = [{"role": "system", "content": self.system_prompt()}] + recent + [{"role": "user", "content": message}]
        for _ in range(MAX_TOOL_ROUNDS):
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini", messages=messages, tools=tools, max_tokens=MAX_REPLY_TOKENS)
            if response.choices[0].finish_reason == "tool_calls":
                reply = response.choices[0].message
                messages.append(reply)
                messages.extend(self.handle_tool_call(reply.tool_calls))
            else:
                return response.choices[0].message.content
        # Too many tool steps: answer without tools so the loop always ends
        response = self.openai.chat.completions.create(
            model="gpt-4o-mini", messages=messages, max_tokens=MAX_REPLY_TOKENS)
        return response.choices[0].message.content

if __name__ == "__main__":
    me = Me()
    gr.ChatInterface(me.chat, type="messages").queue(default_concurrency_limit=4).launch()
