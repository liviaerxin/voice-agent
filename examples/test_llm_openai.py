from openai import OpenAI
from openai import AsyncOpenAI
import asyncio

model="gpt-4.1-mini"

def call_llm(user_input: str):
    client = OpenAI()
    
    completion = client.chat.completions.create(
        model=model,
        messages=[
            # {
            #     "role": "developer",
            #     "content": "Talk like a pirate."
            # },
            {
                "role": "user",
                "content": user_input
            }
        ]
    )
    
    answer = completion.choices[0].message.content
    print(answer, end="", flush=True)

    return answer

async def call_llm_async(user_input: str):
    client = AsyncOpenAI()
    
    answer = ""
    stream = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": user_input
            }
        ],
        stream=True,
    )
    
    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content is not None:
            answer += content
            print(content, end="", flush=True)
                    
    return answer

if __name__ == "__main__":
    # call_llm(user_input="Write a one-sentence bedtime story about a unicorn.")    
    asyncio.run(call_llm_async(user_input="Write a one-sentence bedtime story about a unicorn."))