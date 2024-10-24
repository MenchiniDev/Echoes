import genai

class GeminiAPIClient:
    def __init__(self, api_key):
        # Initialize the model with your API key
        self.model = genai.GenerativeModel("gemini-1.5-flash", api_key=api_key)

    def generate_content(self, prompt):
        # Generate content using the model
        response = self.model.generate_content(prompt)
        return response.text

# Example usage
if __name__ == "__main__":
    client = GeminiAPIClient(api_key="YOUR_API_KEY")
    response = client.generate_content("fai un hello world")
    print(response)
