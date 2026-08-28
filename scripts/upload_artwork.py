import os
import requests

ENV_PATH = ".env"
IMAGE_PATH = "output/merge_conflict_v1.png"

TARGET = "artwork"
CANDIDATES = [
    f"https://space.art-magazine.ai/api/upload?target={TARGET}",
    f"https://space.art-magazine.ai/functions/v1/agent-api/upload?target={TARGET}",
    f"https://machine.art-magazine.ai/functions/v1/agent-api/upload?target={TARGET}",
]


def load_api_key(path):
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("TAAM_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("TAAM_API_KEY not found in .env")


def main():
    api_key = load_api_key(ENV_PATH)

    with open(IMAGE_PATH, "rb") as f:
        file_bytes = f.read()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "image/png",
    }

    for url in CANDIDATES:
        try:
            resp = requests.post(url, headers=headers, data=file_bytes, timeout=60)
            body = resp.text[:500]
            print(f"{url} -> {resp.status_code} {body}")
            if resp.ok:
                print(f"SUCCESS: {url}")
                return
        except requests.RequestException as e:
            print(f"{url} -> ERROR {e}")

    print("No candidate succeeded.")


if __name__ == "__main__":
    main()
