import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
import asyncio
from tools.read_files import read_file, read_directory_files
from tools.read_github_repository import read_github_repository, cleanup_temp_directory
from tools.lint_code import get_linting_score


async def initialize_adk_model():
    """Initializes the Google ADK LLM agent with Gemini model."""
    load_dotenv()  # Load environment variables from .env file
    api_key = os.getenv("GOOGLE_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    os.environ["GOOGLE_API_KEY"] = api_key  # This keeps the compatibility with how ADK might expect the API key internally
    os.environ["GITHUB_TOKEN"] = github_token
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable not set.")


    # Assuming Gemini model can be initialized directly with an API key or it's handled internally by ADK
    # Based on the notebook, it seems the API key is set as an environment variable.
    agent = LlmAgent(
        name="helpful_assistant",
        model="gemini-2.0-flash",  # Changed to gemini-1.5-pro as it's more robust, user can change to flash-lite if preferred.
        description="An agent specialized in generating analyses and description for the code.",
        instruction="""you are an expert high level programmer that can improve code quality and suggest expansions for descriptions and scores 
        of a code module or a complete project, mainly the suggestions are in the following:
            - functionality 
            - feature integration 
            - resource optimization
        and highlight the major weaknesses in the scores and descriptions you are receiving
            """,

        tools=[
            FunctionTool(read_file),
            FunctionTool(read_directory_files),
            FunctionTool(read_github_repository),
            FunctionTool(get_linting_score),
            FunctionTool(cleanup_temp_directory),
        ],
    )
    
    return agent


async def generate_adk_response(prompt: str) -> str:
    """
    Generates a response from the Google ADK LLM agent based on the given prompt.

    Args:
        prompt: The input prompt for the model.

    Returns:
        The generated text response.
    """
    agent = await initialize_adk_model()
    runner = InMemoryRunner(agent=agent)
    response = await runner.run_debug(prompt)
    
    return response  # Assuming the output is directly accessible via .output


async def main():
    # Example usage:
    print("Initializing Google ADK LLM agent...")
    try:
        # Ensure GEMINI_API_KEY is set in your environment variables
        # For example: export GEMINI_API_KEY="YOUR_API_KEY"
        # response_text = await generate_adk_response(
        #     "Tell me a very short story about a brave knight."
        # )
        # print(response_text)

        response_text = await generate_adk_response("""then provide a for the repository at: https://github.com/Samir-atra/Emotion_estimation_from_video_footage_with_LSTM_ML_algorithm"""
        )
        # print(response_text)

    except ValueError as e:
        print(f"Error: {e}")
        print("Please set the GEMINI_API_KEY environment variable.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
