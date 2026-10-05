from google import genai

client_gemini = genai.Client(api_key="AQ.Ab8RN6JCUSZ-g9x_S_hzYCkelgZ5Np_w4LpthQZOw0LULsE6Rg")

response = client_gemini.models.generate_content(
    model="gemini-2.5-flash",
    contents="say hi in one word"
)

print(response.text)