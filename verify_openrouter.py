import os
import sys
from dotenv import load_dotenv

# Try to load environment variables from .env.local
try:
    load_dotenv('.env.local')
except:
    print("No .env.local file found, using existing environment variables")

# Force the use of OpenRouter
os.environ["USE_OPENROUTER"] = "true"

# Import the llm module
sys.path.append('.')
from llm import analyze_with_openrouter, check_openrouter_status

def test_openrouter():
    """Test OpenRouter integration with a simple prompt"""
    print("Testing OpenRouter integration...")
    
    # First check if OpenRouter is properly configured
    status, message = check_openrouter_status()
    if not status:
        print(f"OpenRouter configuration issue: {message}")
        print("Please make sure OPENROUTER_API_KEY is set in your environment or .env.local file")
        return False
    
    print(f"OpenRouter status: {message}")
    
    # Test with Claude
    print("\nTesting with Claude via OpenRouter:")
    try:
        response = analyze_with_openrouter(
            "Summarize the key features of AI newsletter summary tools in 2-3 sentences.", 
            "claude"
        )
        print("Success! Response received:")
        print(response[:100] + "..." if len(response) > 100 else response)
    except Exception as e:
        print(f"Error testing Claude via OpenRouter: {str(e)}")
        return False
    
    # Test with OpenAI
    print("\nTesting with OpenAI via OpenRouter:")
    try:
        response = analyze_with_openrouter(
            "Summarize the key features of AI newsletter summary tools in 2-3 sentences.", 
            "openai"
        )
        print("Success! Response received:")
        print(response[:100] + "..." if len(response) > 100 else response)
    except Exception as e:
        print(f"Error testing OpenAI via OpenRouter: {str(e)}")
        return False
    
    print("\nAll tests passed successfully!")
    return True

if __name__ == "__main__":
    test_openrouter() 