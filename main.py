from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json, re, traceback
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load Gemini API Key
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

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

# Gemini Prompt Logic
def extract_user_info(message: str):
    prompt = f"""
You are helping a user get a credit card.
Extract the following from the user's message in JSON:
- income (convert 60k or 1.2L to numbers)
- spending (fuel, groceries, travel, dining)
- benefits (cashback, lounge access, travel points)
- cards (yes or none)
- score (good, low, unknown)
Return ONLY JSON with all fields. Use null for missing.

User: {message}
"""
    try:
        model = genai.GenerativeModel(model_name="gemini-pro")
        response = model.generate_content(prompt)
        text = response.text
        print("Gemini Response:", text)
        match = re.search(r'{[\s\S]*}', text)
        return json.loads(match.group(0)) if match else {}
    except Exception as e:
        print("Gemini Error:", e)
        return {}

def fallback_question(field):
    return {
        "income": "What is your monthly income?",
        "spending": "Where do you spend the most? (fuel, groceries, travel, dining)",
        "benefits": "What benefits do you prefer? (cashback, lounge access, travel points)",
        "cards": "Do you currently have any credit cards? (yes/none)",
        "score": "What is your credit score? (good, low, unknown)"
    }.get(field, "Can you tell me more about your preferences?")


def generate_next_question():
    for field in ["income", "spending", "benefits", "cards", "score"]:
        if field not in user_data:
            prompt = f"""
You are a helpful assistant guiding a user through a credit card recommendation.
Ask a friendly and specific question to gather the missing field: {field}.

Respond with just the question. Examples:
- income → "What is your monthly income?"
- spending → "Where do you spend the most? (fuel, groceries, travel, dining)"
- benefits → "What type of benefits do you prefer? (cashback, lounge access, travel points)"
- cards → "Do you currently own any credit cards? (yes or none)"
- score → "How is your credit score? (good, low, or unknown)"

Now ask a question for: {field}
"""
            try:
                model = genai.GenerativeModel("gemini-pro")
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                print("Gemini question error:", e)
                return fallback_question(field)
    return None


def update_user_data(message: str):
    message = message.lower().strip()
    print("Message Received:", message)

    if any(c.isdigit() for c in message):
        num = int(''.join(filter(str.isdigit, message)))
        if "income" not in user_data:
            user_data["income"] = num

    for s in spendings:
        if s in message and "spending" not in user_data:
            user_data["spending"] = s

    for b in benefits:
        if b in message and "benefits" not in user_data:
            user_data["benefits"] = b

    if "yes" in message and "cards" not in user_data:
        user_data["cards"] = "yes"
    if "no" in message and "cards" not in user_data:
        user_data["cards"] = "none"

    if "unknown" in message and "score" not in user_data:
        user_data["score"] = "unknown"
    if "good" in message and "score" not in user_data:
        user_data["score"] = "good"
    if "low" in message and "score" not in user_data:
        user_data["score"] = "low"

    # Use Gemini extraction only if fields are still missing
    if len(user_data) < 5:
        extracted = extract_user_info(message)
        if extracted:
            if extracted.get("income") and "income" not in user_data:
                user_data["income"] = int(extracted["income"])
            for key in ["spending", "benefits", "cards", "score"]:
                if extracted.get(key) and key not in user_data:
                    user_data[key] = extracted[key].lower()

    print("User Data So Far:", user_data)


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
            reasons.append(f"Matches your benefit preference: {benefits}")
        if spending in c.get("perks", []):
            score += 2
            reasons.append(f"Matches your spending habit: {spending}")
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
    next_q = generate_next_question()
    return {"reply": next_q or "Thanks! I'm ready to recommend cards now."}

@app.get("/recommend")
def get_recommend():
    if len(user_data) < 5:
        return {"error": "Please complete all questions first."}
    return {"cards": recommend_cards()}

@app.post("/reset")
def reset_data():
    global user_data
    user_data = {}
    return {"status": "reset"}

app.mount("/", StaticFiles(directory="static", html=True), name="static")

