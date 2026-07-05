import os
import asyncio
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner

async def test_model(model_name):
    """Test if a model works by creating an agent and running a simple query."""
    try:
        agent = LlmAgent(
            model=model_name,
            name="test_agent",
            description="Testing model availability",
            instruction="You are a test assistant. Respond briefly."
        )
        
        runner = InMemoryRunner(agent=agent)
        response = await runner.run_debug("Say 'ok' if you can hear me")
        
        return True, "Success"
    except Exception as e:
        return False, str(e)

async def main():
    load_dotenv()
    
    # List of models to test
    models_to_test = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-pro-exp",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-pro",
        "gemini-flash",
    ]
    
    print("Testing Gemini models...\n")
    print("-" * 80)
    
    working_models = []
    failed_models = []
    
    for model_name in models_to_test:
        print(f"Testing: {model_name}...", end=" ")
        success, message = await test_model(model_name)
        
        if success:
            print("✓ WORKS")
            working_models.append(model_name)
        else:
            print(f"✗ FAILED")
            print(f"  Error: {message[:100]}")
            failed_models.append((model_name, message))
    
    print("\n" + "-" * 80)
    print("\nSUMMARY:")
    print(f"\nWorking models ({len(working_models)}):")
    for model in working_models:
        print(f"  ✓ {model}")
    
    print(f"\nFailed models ({len(failed_models)}):")
    for model, error in failed_models:
        print(f"  ✗ {model}")

if __name__ == "__main__":
    asyncio.run(main())
