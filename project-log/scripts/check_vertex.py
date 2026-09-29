"""After the ADC setup: check Vertex AI access and list Gemini Live models available
to the project. Uses ~/.config/gcloud/application_default_credentials.json; prints no
secrets. Usage: check_vertex.py [project] [location]"""
import sys
from google import genai

project = sys.argv[1] if len(sys.argv) > 1 else "hackathon-cinemahackathon"
location = sys.argv[2] if len(sys.argv) > 2 else "us-central1"
try:
    client = genai.Client(vertexai=True, project=project, location=location)
    names = [m.name.split("/")[-1] for m in client.models.list()]
except Exception as e:
    raise SystemExit(f"Vertex access FAILED ({location}): {type(e).__name__}: {str(e)[:300]}")
print(f"Vertex OK in {location}: {len(names)} models")
for n in sorted(names):
    if "live" in n or "native-audio" in n:
        print("  live model:", n)
