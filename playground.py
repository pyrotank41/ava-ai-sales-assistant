import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv(".env")

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

deployment_name = os.getenv(
    "AZURE_OPENAI_DEPLOYMENT_NAME"
)  

response = client.chat.completions.create(
    model=deployment_name,
    messages=[
        {"role": "system", "content": },
        {"role": "user", "content": "Does Azure OpenAI support customer managed keys?"},
        {
            "role": "assistant",
            "content": "Yes, customer managed keys are supported by Azure OpenAI.",
        },
        {"role": "user", "content": "Do other Azure AI services support this too?"},
    ],
)

print(response.json())
