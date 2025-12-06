from mira.models.gemini_client import generate_vision_content
import os

def test_gemini_vision():
    print("--- Testing Gemini Vision ---")
    
    # Check if we have an image to test
    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "data", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    # If no image, create a dummy one or fail gracefully
    # Actually, we can't create a real image easily without PIL.
    # Let's check for ANY file in uploads or just skip if empty.
    
    files = [f for f in os.listdir(uploads_dir) if f.lower().endswith(('.png', '.jpg'))]
    if not files:
        print("[WARN] No images found in data/uploads/ to test. Please upload one via the UI first.")
        return
        
    test_image = os.path.join(uploads_dir, files[0])
    print(f"Testing with: {test_image}")
    
    try:
        desc = generate_vision_content("Describe this image concisely.", test_image)
        print(f"Result: {desc}")
        if "Gemini Vision Error" not in desc:
            print("✅ Vision Model Output received.")
        else:
            print("❌ Vision Model Failed.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_gemini_vision()
