import os
import requests
from openai import OpenAI

# 1. Load Secrets
LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY)


def get_linkedin_urn():
    """Fetches your unique LinkedIn ID using the OpenID Connect endpoint"""
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {'Authorization': f'Bearer {LINKEDIN_ACCESS_TOKEN}'}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch URN: {response.text}")

    # The 'sub' field contains your URN
    return response.json()['sub']


def generate_tech_post():
    """Generates the weekly LinkedIn post using GPT-4o"""
    system_prompt = (
        "You are Azm, a skilled Software Developer. Your communication style is professional, "
        "insightful, yet approachable. You write for other engineers and tech enthusiasts."
    )

    user_prompt = (
        "Write a 150-word LinkedIn post about a current, modern software development topic "
        "(e.g., Clean Code, API design, Cloud Architecture, or AI in dev tools). "
        "Include one specific technical insight, ask a question at the end to drive engagement, "
        "and include 3 relevant hashtags. Do NOT use emojis excessively. Format it cleanly with line breaks."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content


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
    print("Starting LinkedIn Automation...")
    urn = get_linkedin_urn()
    print(f"Found User URN: {urn}")

    post_content = generate_tech_post()
    print("Generated Content:\n", post_content)

    post_to_linkedin(post_content, urn)