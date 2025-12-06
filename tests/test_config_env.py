from mira.config import GEMINI_API_KEY, PROVIDER

def verify_env():
    print(f"Provider: {PROVIDER}")
    if GEMINI_API_KEY and GEMINI_API_KEY.startswith("AIza"):
        print("✅ GEMINI_API_KEY loaded successfully from .env")
    else:
        print(f"❌ GEMINI_API_KEY missing or invalid: {GEMINI_API_KEY}")

if __name__ == "__main__":
    verify_env()
