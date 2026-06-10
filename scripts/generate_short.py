import os
import base64
import requests
import ffmpeg
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ---------------------------------------------------------
# 1. Hämta miljövariabler (från GitHub Secrets)
# ---------------------------------------------------------
HF_TOKEN = os.getenv("HF_TOKEN")
YT_CLIENT_ID = os.getenv("YT_CLIENT_ID")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET")
YT_REFRESH_TOKEN = os.getenv("YT_REFRESH_TOKEN")

# ---------------------------------------------------------
# 2. Generera manus med Phi-3-mini-4k-instruct
# ---------------------------------------------------------
def generate_script():
    prompt = """
    Skriv ett extremt kort, 10-sekunders manus om en rolig eller märklig fakta om en dryck.
    Max 2 meningar. Skriv på svenska.
    """

    response = requests.post(
        "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct",
        headers={"Authorization": f"Bearer {HF_TOKEN}"},
        json={"inputs": prompt}
    )

    text = response.json()
    if isinstance(text, list):
        return text[0]["generated_text"]
    return str(text)

# ---------------------------------------------------------
# 3. Generera bild med Stable Diffusion XL
# ---------------------------------------------------------
def generate_image(prompt_text):
    response = requests.post(
        "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
        headers={"Authorization": f"Bearer {HF_TOKEN}"},
        json={"inputs": prompt_text}
    )

    image_bytes = base64.b64decode(response.json()["image_base64"])
    with open("image.png", "wb") as f:
        f.write(image_bytes)

    return "image.png"

# ---------------------------------------------------------
# 4. Bygg video med FFmpeg
# ---------------------------------------------------------
def build_video(image_path, script_text):
    # Spara manus som text-overlay
    with open("script.txt", "w") as f:
        f.write(script_text)

    (
        ffmpeg
        .input(image_path, loop=1, t=10)
        .filter("scale", 1080, 1920)
        .output("output.mp4", vcodec="libx264", pix_fmt="yuv420p", r=30)
        .overwrite_output()
        .run()
    )

    return "output.mp4"

# ---------------------------------------------------------
# 5. Ladda upp videon till YouTube Shorts
# ---------------------------------------------------------
def upload_to_youtube(video_path, title):
    creds = Credentials(
        None,
        refresh_token=YT_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )

    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": "Automatiskt genererad Short om dryckesfakta.",
                "tags": ["shorts", "dryck", "fakta", "AI"],
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "public",
                "madeForKids": False
            }
        },
        media_body=video_path
    )

    response = request.execute()
    print("YouTube upload response:", response)

# ---------------------------------------------------------
# 6. Kör hela pipelinen
# ---------------------------------------------------------
def main():
    print("Genererar manus…")
    script = generate_script()

    print("Genererar bild…")
    image = generate_image(script)

    print("Bygger video…")
    video = build_video(image, script)

    print("Laddar upp till YouTube…")
    upload_to_youtube(video, "Dagens dryckesfakta")

    print("Klar!")

if __name__ == "__main__":
    main()
