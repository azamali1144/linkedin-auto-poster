import os
import requests
import google.generativeai as genai

# 1. Load Secrets
LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Gemini Client
genai.configure(api_key=GEMINI_API_KEY)


def get_linkedin_urn():
    """Fetches your unique LinkedIn ID using the OpenID Connect endpoint"""
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {'Authorization': f'Bearer {LINKEDIN_ACCESS_TOKEN}'}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch URN: {response.text}")

    return response.json()['sub']


def generate_tech_post():
    """Generates the weekly LinkedIn post using Gemini 1.5 Flash"""
    # Use the flash model (fastest and free)
    model = genai.GenerativeModel('gemini-pro')

    prompt = (
        "You are Azm, a skilled Software Developer. Your communication style is professional, "
        "insightful, yet approachable. You write for other engineers and tech enthusiasts.\n\n"
        "Write a 150-word LinkedIn post about a current, modern software development topic "
        "(e.g., Clean Code, API design, Cloud Architecture, or AI in dev tools). "
        "Include one specific technical insight, ask a question at the end to drive engagement, "
        "and include 3 relevant hashtags. Do NOT use emojis excessively. Format it cleanly with line breaks."
    )

    response = model.generate_content(prompt)
    return response.text.strip()


def post_to_linkedin(content, user_urn):
    """Publishes the generated content to your LinkedIn Profile"""
    url = 'https://api.linkedin.com/v2/ugcPosts'
    headers = {
        'Authorization': f'Bearer {LINKEDIN_ACCESS_TOKEN}',
        'X-Restli-Protocol-Version': '2.0.0',
        'Content-Type': 'application/json'
    }

    payload = {
        "author": f"urn:li:person:{user_urn}",
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
        print("✅ Successfully posted to LinkedIn!")
    else:
        print(f"❌ Failed to post: {response.text}")


if __name__ == "__main__":
    print("Starting LinkedIn Automation (Gemini Edition)...")

    urn = get_linkedin_urn()
    print(f"Found User URN: {urn}")

    post_content = generate_tech_post()
    print("Generated Content:\n", post_content)

    post_to_linkedin(post_content, urn)