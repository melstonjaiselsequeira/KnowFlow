
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY not found in .env")

client = OpenAI(api_key=api_key)

print("Checking OpenAI API access...")

try:
    models = client.models.list()

    available_models = [
        model.id for model in models.data
        if "gpt" in model.id.lower()
    ]

    print("\nModels visible to your API key:")

    for model in available_models:
        print("-", model)

    if "gpt-4o-mini" in available_models:
        print("\ngpt-4o-mini is visible.")
    else:
        print("\ngpt-4o-mini is not visible to this API key.")

except Exception as error:
    print("\nAPI access check failed:")
    print(type(error).__name__, str(error))
