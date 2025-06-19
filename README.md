# credit-card-recommendation
This project is a conversational credit card recommendation system built using FastAPI, vanilla HTML + JavaScript for the frontend, and Google Gemini as the LLM agent.

It guides users through a series of natural interactions to collect their financial preferences and recommends credit cards that match their profile. The system uses an intelligent agent to extract information and generate personalized follow-up questions — one at a time.

---

## 🔥 Features

- 💬 LLM-powered understanding of natural user messages (e.g., "I spend mostly on groceries and prefer cashback")
- ❓ Intelligent follow-up question generation using Google Gemini
- 📊 Personalized credit card recommendations based on income, spending habits, credit score, and preferred perks
- 📱 Mobile-responsive, minimal UI built with just HTML and JavaScript
- 🔁 Ability to restart the flow at any time

---
## 🚀 How It Works

1. User types a natural sentence (e.g., _“I earn 60K and spend mostly on groceries”_)
2. Gemini extracts structured fields like income and spending
3. The system stores user data and asks **only the next missing question**
4. Once all 5 fields are collected, it returns the **top 3 card recommendations**
---
 Local Setup
1. Clone this repository
-git clone https://github.com/your-username/credit-card-recommendation.git
-cd credit-card-recommendation

3. Install dependencies
-pip install -r requirements.txt

5. Add your Gemini API key
-Create a .env file in the root (same level as main.py):
-GEMINI_API_KEY=your_actual_gemini_api_key_here

4. Start the server
-uvicorn main:app --reload
-Open the browser at http://localhost:8000 — the frontend UI will load.

---
🧪 API Overview

| Method | Endpoint     | Description                             |
| ------ | ------------ | --------------------------------------- |
| POST   | `/chat`      | Accepts user message, returns next step |
| GET    | `/recommend` | Returns top credit card recommendations |
| POST   | `/reset`     | Resets current session data             |

---
📄 Environment Variables
| Name             | Description                |
| ---------------- | -------------------------- |
| `GEMINI_API_KEY` | Your Google Gemini API key |

---
🌐 Deployment (Render or Replit)
You can deploy using any platform that supports Python FastAPI:

Suggested Render settings:
Build command:
pip install -r requirements.txt

Start command:
uvicorn main:app --host 0.0.0.0 --port 10000

Add Environment Variable:
GEMINI_API_KEY=your_actual_key

Frontend will be auto-served from the /static folder.

---
📸 Demo
A demo video or GIF will be added here soon!
