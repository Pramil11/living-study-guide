
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ["MINDROUTER_API_KEY"],
    base_url=os.getenv(
        "MINDROUTER_BASE_URL",
        "https://mindrouter.uidaho.edu/v1"
    ),
    timeout=120.0
)

print("Connecting to MindRouter...")

models = client.models.list()

print("\nAvailable Qwen models:")
for model in models.data:
    if "qwen" in model.id.lower():
        print("-", model.id)

model_name = os.getenv(
    "MINDROUTER_MODEL",
    "qwen/qwen3.5-122b"
)

print(f"\nTesting model: {model_name}")

response = client.chat.completions.create(
    model=model_name,
    messages=[
        {
            "role": "system",
            "content": "You are a helpful study assistant."
        },
        {
            "role": "user",
            "content": (
                "Explain machine learning in two simple sentences."
            )
        }
    ],
    temperature=0.2,
    max_tokens=300
)

print("\nAI Response:")
print(response.choices[0].message.content)
