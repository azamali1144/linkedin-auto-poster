import os
import json
import requests
import urllib.parse
import google.generativeai as genai

# 1. Load Secrets
LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Initialize Gemini Client
genai.configure(api_key=GEMINI_API_KEY)


def get_linkedin_urn():
    """Fetches your unique LinkedIn ID"""
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {'Authorization': f'Bearer {LINKEDIN_ACCESS_TOKEN}'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch URN: {response.text}")
    return response.json()['sub']


def generate_content():
    """Generates the main post AND the promotional comment using Gemini"""
    model = genai.GenerativeModel('gemini-2.5-flash')

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

    1. "main_post": A highly engaging, visually appealing 150-200 word educational LinkedIn post. 
    Randomly focus deeply on ONLY ONE of the core consulting services listed above. 

    CRITICAL FORMATTING RULES FOR main_post:
    - Start with a strong, attention-grabbing hook in the first line.
    - Use plenty of vertical spacing (insert blank lines/newlines between every concept).
    - Use emojis strategically but professionally (e.g., 🚀, 💡, ⚙️, 📊).
    - Use bullet points (•) for key takeaways or technical benefits.
    - DO NOT write a giant block of text. Break it up so it is easy to read on mobile.
    - End with 3-4 relevant hashtags.

    2. "first_comment": A short, confident comment (2-3 sentences) acting as a Call to Action (CTA). Mention your 10+ years of experience and state that you are open for contract/freelance work to help businesses build scalable infrastructure or integrate Agentic AI into their systems. Tell them to DM you to discuss their project. Include 1-2 emojis.

    Return ONLY valid JSON in this exact structure, with no markdown formatting around it:
    {
      "main_post": "...",
      "first_comment": "..."
    }
    """

    # Force the model to return JSON structure
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
    )

    return json.loads(response.text)


def post_to_linkedin(content, user_urn):
    """Publishes the generated content and returns the Post ID"""
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
        post_id = response.headers.get('X-RestLi-Id') or response.json().get('id')
        print(f"✅ Successfully posted to LinkedIn! Post ID: {post_id}")
        return post_id
    else:
        print(f"❌ Failed to post: {response.text}")
        return None


def add_first_comment(post_urn, comment_text, user_urn):
    """Adds a comment to the post we just created"""

    # FIX: We must URL-encode the URN because it contains colons (:) which breaks the URL path
    encoded_post_urn = urllib.parse.quote(post_urn)

    url = f"https://api.linkedin.com/v2/socialActions/{encoded_post_urn}/comments"
    headers = {
        'Authorization': f'Bearer {LINKEDIN_ACCESS_TOKEN}',
        'X-Restli-Protocol-Version': '2.0.0',
        'Content-Type': 'application/json'
    }

    payload = {
        "actor": f"urn:li:person:{user_urn}",
        "message": {
            "text": comment_text
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code in [200, 201]:
        print("✅ Successfully added the promotional first comment!")
    else:
        print(f"❌ Failed to add comment: {response.text}")


if __name__ == "__main__":
    print("Starting LinkedIn Automation: Consultant Edition...")

    try:
        urn = get_linkedin_urn()

        # 1. Generate both pieces of text
        ai_content = generate_content()
        main_post = ai_content["main_post"]
        first_comment = ai_content["first_comment"]

        print("Generated Main Post:\n", main_post)
        print("\nGenerated Comment:\n", first_comment)

        # 2. Publish the main post and grab its ID
        post_urn = post_to_linkedin(main_post, urn)

        # 3. If successful, immediately post the first comment to it
        if post_urn:
            add_first_comment(post_urn, first_comment, urn)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
