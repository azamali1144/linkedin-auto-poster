import os
import json
import time
import random
import requests
import pytz
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
STATE_FILE = "state.json"
PKT = pytz.timezone('Asia/Karachi')

genai.configure(api_key=GEMINI_API_KEY)


def get_state():
    """Reads the state from a local JSON file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"last_post_time": None, "last_post_urn": None, "commented": True, "pending_comment": None}


def save_state(last_time, urn, commented, pending_comment=None):
    """Saves the current state to persist between GitHub Action runs."""
    with open(STATE_FILE, 'w') as f:
        json.dump({
            "last_post_time": last_time.isoformat() if last_time else None,
            "last_post_urn": urn,
            "commented": commented,
            "pending_comment": pending_comment
        }, f)


def get_linkedin_user_urn():
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {'Authorization': f'Bearer {LINKEDIN_ACCESS_TOKEN}'}
    response = requests.get(url, headers=headers)
    return f"urn:li:person:{response.json()['sub']}"


def generate_content():
    """YOUR RESTORED ORIGINAL PROMPT: Generates main post AND promotional comment"""
    # Note: Using gemini-1.5-flash as 2.5 is not a public stable version yet,
    # but keeping your logic exactly the same.
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = """
    You are Muhammad Azam, a Senior Software Engineer and Agentic AI Solutions Architect with 10+ years of experience. 
    You specialize in helping startups and Fortune 500 companies transform business ideas into real-time, scalable, high-performance systems.

    Your core consulting services include:
    - Agentic AI & Custom Bots (LangGraph, CrewAI, LLM integration)
    - Cloud Scalability & Infrastructure (AWS, GCP, Microservices)
    - Advanced System Architecture & Database Optimization (PostgreSQL, MongoDB, DynamoDB)
    - DevOps, Automations, and robust CI/CD pipelines
    - Data Science & Machine Learning workflows

    Write two things for me in strict JSON format:

    1. "main_post": A highly engaging 150-200 word thought-leadership LinkedIn post. 
    Randomly focus deeply on ONLY ONE of the core consulting services listed above. 

    CRITICAL TONE & CONTENT RULES for main_post:
    - Tone: Confident, veteran, and slightly contrarian. Do NOT sound like a generic AI or textbook. Sound like an architect sharing a hard-learned lesson from the trenches.
    - The Hook: Start with a bold, attention-grabbing statement (e.g., "The biggest mistake companies make with...", "Unpopular opinion: ...", or "Stop doing X...").
    - Business Value: Include a realistic, impressive business metric (e.g., "reducing AWS costs by 40%", "saving 20 hours a week of manual work", or "scaling to 10k requests/sec").
    - The End: Finish with a thought-provoking question to the audience to drive comments.

    CRITICAL FORMATTING RULES for main_post:
    - Use plenty of vertical spacing (insert blank newlines between every concept).
    - Use emojis strategically but minimally (2-4 max).
    - Use a bulleted list (•) for key technical insights.
    - DO NOT use markdown bold (**) or italics (*). LinkedIn API does not render them well. If you must emphasize a word, use ALL CAPS.
    - End with 3-4 highly relevant hashtags.

    2. "first_comment": A short, confident comment (2-3 sentences) acting as a Call to Action (CTA). Mention your 10+ years of experience and state that you are open for contract/freelance work to help businesses build scalable infrastructure or integrate Agentic AI into their systems. Tell them to DM you to discuss their project. Include 1-2 emojis.

    Return ONLY valid JSON in this exact structure, with no markdown formatting around it:
    {
      "main_post": "...",
      "first_comment": "..."
    }
    """

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)


def post_to_linkedin(content, user_urn):
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        'Authorization': f'Bearer {LINKEDIN_ACCESS_TOKEN}',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    payload = {
        "author": user_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        return response.json()['id']
    return None


def post_comment(post_urn, user_urn, comment_text):
    url = f"https://api.linkedin.com/v2/socialActions/{post_urn}/comments"
    headers = {
        'Authorization': f'Bearer {LINKEDIN_ACCESS_TOKEN}',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    payload = {
        "actor": user_urn,
        "message": {"text": comment_text}
    }
    res = requests.post(url, headers=headers, json=payload)
    return res.status_code == 201


def main():
    state = get_state()
    now = datetime.now(PKT)
    user_urn = get_linkedin_user_urn()

    # 1. LOGIC: CHECK FOR PENDING COMMENTS (THE 30-MINUTE DELAY)
    if state["last_post_urn"] and not state["commented"]:
        last_time = datetime.fromisoformat(state["last_post_time"]).replace(tzinfo=PKT)
        diff_minutes = (now - last_time).total_seconds() / 60

        if diff_minutes >= 30:
            print(f"🕒 Post is {int(diff_minutes)} mins old. Posting your saved CTA comment...")
            if post_comment(state["last_post_urn"], user_urn, state["pending_comment"]):
                save_state(last_time, state["last_post_urn"], True, None)
                print(f"✅ Commented successfully.")
            return
        else:
            print(f"⏳ Waiting for 30-min window. Currently at {int(diff_minutes)} mins.")
            return

    # 2. LOGIC: SHOULD WE CREATE A NEW POST?
    # Check Hours (5 AM to 10 PM PKT)
    if not (5 <= now.hour <= 22):
        print(f"💤 Outside active hours (5am-10pm PKT). Sleeping.")
        return

    # Check Time Gap (20-40 hours)
    if state["last_post_time"]:
        last_post = datetime.fromisoformat(state["last_post_time"]).replace(tzinfo=PKT)
        hours_since = (now - last_post).total_seconds() / 3600

        if hours_since < 20:
            print(f"⏳ Only {hours_since:.1f} hours since last post. Min is 20.")
            return

        # If between 20-40 hours, randomize (15% chance per hour run)
        if hours_since < 40 and random.random() > 0.15:
            print(f"🎲 Randomness roll: Skipping this hour. ({hours_since:.1f}h since last)")
            return

    # If we reached here, time to generate and post!
    print("🚀 All conditions met. Generating your Architect post and CTA...")
    data = generate_content()

    new_urn = post_to_linkedin(data["main_post"], user_urn)
    if new_urn:
        print(f"✅ Posted to LinkedIn: {new_urn}")
        # Save the first_comment in the state file so we can post it 30 mins later
        save_state(now, new_urn, False, data["first_comment"])
    else:
        print("❌ Posting failed.")


if __name__ == "__main__":
    main()
