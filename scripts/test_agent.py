import sys
from src.agent import agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService

def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/voice-test/positive.wav"
    prompt_text = f"Please extract the tasks from the audio file located at {audio_path} using your tool."
    
    print(f"Running agent for audio: {audio_path}...")
    
    runner = Runner(agent=agent, session_service=InMemorySessionService(), app_name="test", auto_create_session=True)
    
    from google.genai import types
    new_message = types.Content(parts=[types.Part.from_text(text=prompt_text)], role="user")
    
    response_text = ""
    # Synchronous iteration over the runner
    for event in runner.run(user_id="test", session_id="test", new_message=new_message):
        print(f"Event: type={type(event).__name__}")
        if hasattr(event, "message"):
            try:
                # Based on types.Content
                if hasattr(event.message, "parts") and event.message.parts:
                    response_text += event.message.parts[0].text
                elif isinstance(event.message, str):
                    response_text += event.message
            except Exception as e:
                print(f"Error printing content: {e}")
    
    print("\n--- Agent Response ---")
    print(response_text)

if __name__ == "__main__":
    main()
