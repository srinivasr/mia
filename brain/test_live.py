import asyncio
from google import genai
from google.genai import types
from memory.config_manager import get_gemini_key

MODEL = "models/gemini-3.1-flash-live-preview"

async def test_conn():
    client = genai.Client(
        api_key=get_gemini_key(),
        http_options={"api_version": "v1beta"}
    )
    config = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
    )
    print(f"Testing {MODEL}...")
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print(f"Connected!")
            await session.send_realtime_input(text="Say hello")
            async for response in session.receive():
                if response.server_content:
                    if response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if part.inline_data:
                                print(f"Audio: {len(part.inline_data.data)} bytes")
                    if response.server_content.turn_complete:
                        break
            print("Done!")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())
