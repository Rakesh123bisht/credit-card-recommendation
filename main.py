from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import json, re, os
from dotenv import load_dotenv
import openai

# Load .env and set OpenRouter API
load_dotenv()
openai.api_key = os.getenv("OPENROUTER_API_KEY")
openai.api_base = "https://openrouter.ai/api/v1"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

user_data = {}
spendings = ["fuel", "groceries", "travel", "dining"]
benefits = ["cashback", "lounge access", "travel points"]

# Extract user info using OpenRouter
def extract_user_info(message: str):
    prompt = f"""
You are helping a user get a credit card.
Extract the following fields from the user's message as JSON:
- income (number only)
- spending (fuel, groceries, travel, dining)
- benefits (cashback, lounge access, travel points)
- cards (yes or none)
- score (good, low, unknown)
Respond only in JSON. Use null if not found.

User: {message}
"""
    try:
        response = openai.ChatCompletion.create(
            model="mistralai/mixtral-8x7b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = response.choices[0].message["content"]
        print("OpenRouter JSON response:", text)
        match = re.search(r'{[\s\S]*}', text)
        return json.loads(match.group(0)) if match else {}
    except Exception as e:
        print("OpenRouter Error:", e)
        return {}

def generate_followup_question(missing_fields):
    prompt = f"""
You are an assistant helping someone get a credit card.
They have not told you: {', '.join(missing_fields)}.
Ask a simple, friendly question to get the next one. Ask only one thing.
"""
    try:
        response = openai.ChatCompletion.create(
            model="mistralai/mixtral-8x7b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        print("Follow-up question error:", e)
        return "Could you tell me more?"

def update_user_data(message: str):
    message = message.lower().strip()

    if any(c.isdigit() for c in message):
        num = int(''.join(filter(str.isdigit, message)))
        if "income" not in user_data:
            user_data["income"] = num
            return

    for s in spendings:
        if s in message and "spending" not in user_data:
            user_data["spending"] = s
            return

    for b in benefits:
        if b in message and "benefits" not in user_data:
            user_data["benefits"] = b
            return

    if "yes" in message and "cards" not in user_data:
        user_data["cards"] = "yes"
        return
    if "no" in message and "cards" not in user_data:
        user_data["cards"] = "none"
        return

    if "good" in message and "score" not in user_data:
        user_data["score"] = "good"
        return
    if "low" in message and "score" not in user_data:
        user_data["score"] = "low"
        return
    if "unknown" in message and "score" not in user_data:
        user_data["score"] = "unknown"
        return

    extracted = extract_user_info(message)
    if extracted:
        if extracted.get("income"): user_data["income"] = int(extracted["income"])
        for key in ["spending", "benefits", "cards", "score"]:
            if extracted.get(key): user_data[key] = extracted[key].lower()

def get_next_question():
    needed = ["income", "spending", "benefits", "cards", "score"]
    missing = [field for field in needed if field not in user_data]
    return generate_followup_question(missing) if missing else None

def load_cards():
    with open("cards.json") as f:
        return json.load(f)

def recommend_cards():
    cards = load_cards()
    income = user_data.get("income", 0)
    spending = user_data.get("spending", "")
    benefits = user_data.get("benefits", "")

    scored = []
    for c in cards:
        if income < c.get("min_income", 0): continue
        score = 0
        reasons = []

        if benefits in c.get("perks", []):
            score += 2
            reasons.append(f"Matches your benefit: {benefits}")
        if spending in c.get("perks", []):
            score += 2
            reasons.append(f"Matches your spending: {spending}")
        if c.get("joining_fee", 0) == 0:
            score += 1
            reasons.append("Zero joining fee")
        if c.get("annual_fee", 0) == 0:
            score += 1
            reasons.append("No annual fee")

        reward = int(c.get("reward_rate", 0) * 5000 * 12)
        c["reward_estimate"] = f"Estimated yearly reward: ₹{reward}"
        c["score"] = score
        c["reasons"] = reasons + [f"You are eligible with income ₹{income}"]
        scored.append(c)

    top = sorted(scored, key=lambda x: -x["score"])[:3]
    return [{
        "name": x["name"],
        "issuer": x["issuer"],
        "image": x.get("image", ""),
        "reasons": x["reasons"],
        "reward_estimate": x["reward_estimate"],
        "apply_link": x["apply_link"]
    } for x in top]

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(req: ChatRequest):
    update_user_data(req.message)
    next_q = get_next_question()
    return {"reply": next_q or "Thanks! I'm ready to recommend cards now."}

@app.get("/recommend")
def get_recommend():
    if len(user_data) < 5:
        return {"error": "Please complete all questions first."}
    return {"cards": recommend_cards()}

@app.post("/reset")
def reset_data():
    user_data.clear()
    return {"status": "reset"}

app.mount("/", StaticFiles(directory="static", html=True), name="static")


