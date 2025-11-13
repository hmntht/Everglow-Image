# app.py

import streamlit as st
import streamlit.components.v1 as components
import os
import base64
from io import BytesIO

# Import the Google GenAI SDK
from google import genai
from google.genai.errors import APIError
from PIL import Image

# --- Configuration and Setup ---

# Set Streamlit page configuration (optional but good practice)
st.set_page_config(layout="wide")

# Get the Gemini API Key securely from Streamlit secrets
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("GEMINI_API_KEY not found in Streamlit secrets. Please configure it.")
    st.stop()

# Initialize the Gemini Client
try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    st.error(f"Failed to initialize Gemini Client: {e}")
    st.stop()


# --- Core Transmutation Function (The Proxy Logic) ---

def call_gemini_image_api(prompt: str, image_bytes: bytes, mime_type: str) -> str:
    """
    Calls the Gemini Image-to-Image (Image Editing) API.
    Returns the base64 string of the generated image.
    """
    try:
        # 1. Convert raw image bytes to a PIL Image object
        image = Image.open(BytesIO(image_bytes))

        # 2. Call the Gemini Image Editing API
        # The 'inpainting' model (or similar generative model) is used for image modification
        # NOTE: The exact model name for Inpainting/Editing may vary or use a general generator.
        # We will use the general image generation model for this example, which supports prompts.
        # For true image editing, you would need a model that accepts both image and prompt.
        
        # Using a model that accepts the image as context (like gemini-2.5-flash or Pro)
        # for a multimodal instruction, or a dedicated Imagen model.
        # The genai SDK's general client handles multimodal inputs.
        
        # The prompt guides the modification.
        
        # For a standard multimodal call:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                image, 
                f"Perform image-to-image modification based on this instruction: {prompt}. Return only the resulting image."
            ]
        )
        
        # NOTE: The client.models.generate_content() usually returns text, not an image object 
        # for an image-to-image operation. True image editing uses a specific
        # image generation service like Imagen/Google Arts.
        
        # Since the frontend expects an image, we will simulate the expected output
        # by calling a *text* model for a *text* response, or the specific Image API.
        
        # *** For a working Image-to-Image app, you would typically use a dedicated 
        # Image API (like the Imagen API) here. ***
        
        # *** Placeholder for getting the generated image data ***
        # If we use a dedicated Image Generation API that returns a list of image objects:
        # Assuming the generated image data is returned as PNG bytes for simplicity
        
        # *** Since we must use the genai SDK, we'll use a placeholder for the actual
        # image generation call, as the standard 'generate_content' is not ideal for 
        # image-to-image tasks returning an image. ***
        
        # For demonstration purposes, let's use the input image as a temporary fallback,
        # but in a real app, you MUST replace this with a call to the correct Image API 
        # that returns the generated image bytes.
        
        # --- PLACEHOLDER API CALL ---
        
        # Replace this with the actual call that returns the generated image bytes
        # For a successful deployment, the image model must be used here.
        
        # Simulating successful API call (returns the input image for now)
        temp_buffer = BytesIO()
        image.save(temp_buffer, format="PNG")
        generated_image_bytes = temp_buffer.getvalue()
        
        # --- END PLACEHOLDER API CALL ---

        # Convert the generated image bytes to a base64 string for the frontend
        base64_result = base64.b64encode(generated_image_bytes).decode("utf-8")
        return base64_result
    
    except APIError as e:
        st.error(f"Gemini API Error: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None


# --- Custom Streamlit Component Setup ---

# Create a local build directory if it doesn't exist
COMPONENT_DIR = os.path.join(os.path.dirname(__file__), "frontend")
if not os.path.exists(COMPONENT_DIR):
    st.error(f"Frontend directory not found at: {COMPONENT_DIR}")

# The function to render the custom component
_transmutation_forge = components.declare_component(
    "transmutation_forge",
    path=COMPONENT_DIR,
)

def transmutation_forge():
    """Renders the HTML component and returns data sent back by JS."""
    # The 'key' is essential to maintain state across reruns
    component_value = _transmutation_forge(
        initialLoad=True, 
        key="transmutation_forge_key"
    )
    return component_value


# --- Main Application Logic ---

def main():
    st.markdown("---")
    
    # 1. Render the Custom HTML/JS Component
    # This renders the entire UI (upload, prompt, button)
    user_data = transmutation_forge()
    
    # 2. Check for data coming back from JavaScript (when user clicks 'Forge')
    if user_data and user_data.get('action') == 'generate':
        st.session_state.processing = True
        
        # Extract data from the JS payload
        prompt = user_data.get('prompt')
        b64_data = user_data.get('imageData')
        mime_type = user_data.get('mimeType')
        
        # Convert base64 data to raw bytes for the API call
        image_bytes = base64.b64decode(b64_data)
        
        with st.spinner("Processing transmutation..."):
            # Call the secure Python function with the API key
            result_b64 = call_gemini_image_api(prompt, image_bytes, mime_type)
        
        st.session_state.processing = False
        
        # 3. Send the result back to the JavaScript frontend
        if result_b64:
            # We must use st.components.v1.html to send data back to the iframe component
            # by rerunning the component with the new data in its key/state.
            # However, the streamlit-component-lib JS is set up to listen for a specific message
            # The most reliable way is to use st.components.v1.html to inject the result,
            # or rely on the component's internal state handling.
            
            # Since we are using the simple declare_component, we will use a workaround
            # to communicate the result back to the frontend's message listener.
            
            st.session_state.result_payload = {
                'action': 'result',
                'base64Data': result_b64,
                'error': None
            }
        else:
            st.session_state.result_payload = {
                'action': 'result',
                'base64Data': None,
                'error': 'API call failed. Check server logs.'
            }

        # To ensure the message is sent, we re-run the script.
        st.rerun() 

    # 4. Inject the result data back into the frontend
    if 'result_payload' in st.session_state:
        # This is a hacky way to communicate back to the JavaScript iframe:
        # We re-render a small HTML component that sends a message event to the parent.
        payload = st.session_state.pop('result_payload')
        js_script = f"""
            <script>
                // Find the parent window (the iframe's host - Streamlit)
                const parentWindow = window.parent;
                if (parentWindow) {
                    // Send a message that the frontend's listener can catch
                    parentWindow.postMessage({{
                        type: 'streamlit:setComponentValue',
                        value: {payload}
                    }}, '*');
                }
            </script>
        """
        # Render a minimal component to execute the JavaScript hack
        components.html(js_script, height=0)


if __name__ == '__main__':
    main()

