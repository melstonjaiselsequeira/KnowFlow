
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(".env", override=True)

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY not found in backend/.env")

client = OpenAI(api_key=api_key)

try:
    print("Testing gpt-4o-mini Chat Completions...")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: KnowFlow API working"
            }
        ],
        max_tokens=30
    )

    print("\nSUCCESS!")
    print("Response:", response.choices[0].message.content)

except Exception as error:
    print("\nAPI TEST FAILED")
    print("Error type:", type(error).__name__)
    print("Error:", error)
