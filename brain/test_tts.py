import asyncio
import edge_tts
import io
import base64

async def test_tts():
    text = "تذكرة رقم واحد"
    voice = "ar-SA-ZariyahNeural"
    communicate = edge_tts.Communicate(text, voice)
    audio_fp = io.BytesIO()
    
    print(f"Starting TTS for: {text}")
    try:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_fp.write(chunk["data"])
        
        audio_data = audio_fp.getvalue()
        print(f"Generated audio size: {len(audio_data)} bytes")
        if len(audio_data) > 0:
            print("SUCCESS")
        else:
            print("FAILED: Empty audio")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_tts())
