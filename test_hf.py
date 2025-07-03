import time
import requests

HF_TOKEN = "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"


# API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-small"
# headers = {"Authorization": f"Bearer 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"}

# def query(payload):
#     response = requests.post(API_URL, headers=headers, json=payload)
#     print(f"Status Code: {response.status_code}")
#     print(f"Response Text: {response.text}")
#     try:
#         return response.json()
#     except Exception as e:
#         print("Error decoding JSON:", e)
#         return None

# output = query({"inputs": "I love Hugging Face!"})
# print(output)



# from huggingface_hub import InferenceClient
# client = InferenceClient("tiiuae/falcon-rw-1b", token=HF_TOKEN)

# output = client.text_generation(
#     "Write a short reply: Can you add this task?",
#     max_new_tokens=50
# )

# print(output)

# API_URL = "https://api-inference.huggingface.co/models/bigscience/bloomz-560m"
# headers = {"Authorization": "Bearer "+HF_TOKEN}

# def hf_query(inputs):
#     for _ in range(3):  # retry up to 3 times
#         response = requests.post(API_URL, headers=headers, json={"inputs": inputs})
#         if response.status_code == 200:
#             return response.json()
#         elif response.status_code == 503:
#             print("Model loading… retrying in 10s.")
#             time.sleep(10)
#         else:
#             print(response.status_code, response.text)
#             return None
#     return None

# result = hf_query("Write a short reply: Can you add this task?")
# print(result)


# import os
# from huggingface_hub import InferenceClient
# import time

# client = InferenceClient(token=HF_TOKEN, provider="hf-inference")

# def ask(messages):
#     try:
#         return client.chat_completion(
#             model="deepseek-ai/DeepSeek-V3-0324",
#             messages=messages,
#             temperature=0.7,
#             # max_new_tokens=150
#         ).choices[0].message["content"]
#     except Exception as e:
#         print("Error during call:", e)
#         time.sleep(5)
#         return None

# if __name__ == "__main__":
#     msgs = [
#         {"role": "system", "content": "You are a friendly to-do assistant."},
#         {"role": "user", "content": "Add 'Call Anna at 5 PM' to my list."}
#     ]
#     reply = ask(msgs)
#     print("Assistant:", reply)




# import os
# from huggingface_hub import InferenceClient

# client = InferenceClient(
#     provider="novita",
#     api_key=HF_TOKEN,
# )

# completion = client.chat.completions.create(
#     model="deepseek-ai/DeepSeek-V3-0324",
#     messages=[
#         {
#             "role": "user",
#             "content": "What is the capital of France?"
#         }
#     ],
# )

# print(completion.choices[0].message)


# import os
# from huggingface_hub import InferenceClient

# client = InferenceClient(
#     provider="hf-inference",
#     api_key=HF_TOKEN,
# )

# completion = client.chat.completions.create(
#     model="meta-llama/Llama-3.2-11B-Vision-Instruct",
#     messages=[
#         {
#             "role": "user",
#             "content": [
#                 {
#                     "type": "text",
#                     "text": "Describe this image in one sentence."
#                 },
#                 {
#                     "type": "image_url",
#                     "image_url": {
#                         "url": "https://cdn.britannica.com/61/93061-050-99147DCE/Statue-of-Liberty-Island-New-York-Bay.jpg"
#                     }
#                 }
#             ]
#         }
#     ],
# )

# print(completion.choices[0].message)


import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    provider="fal-ai",
    api_key=HF_TOKEN,
)

# output is a PIL.Image object
image = client.text_to_image(
    "Astronaut riding a horse",
    model="stabilityai/stable-diffusion-3.5-large",
)
print(image)

