import streamlit as st
import os
import requests
import json
from PIL import Image
import io

# --- Streamlit Page Configuration ---
# This configuration is required for using the st.html function
st.set_page_config(layout="centered")

# --- Security Check ---
# The API key MUST be set as an environment variable in your Streamlit secrets.
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    st.error("Error: GEMINI_API_KEY environment variable not set.")
    st.stop()

# --- Gemini API Configuration ---
MODEL_NAME = "gemini-2.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

# --- Core Function to Call Gemini API ---
def call_gemini_api(base64_image_data, prompt):
    """Sends the image and prompt to the Gemini API."""
    
    # Construct the JSON payload with both the text prompt and the image part
    payload = {
        "contents": [
            {
                "parts": [
                    # The text prompt part
                    {"text": prompt},
                    # The image part (using the base64 data)
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",  # Assuming jpeg/png, API can handle both
                            "data": base64_image_data
                        }
                    }
                ]
            }
        ],
        "config": {
            # Ensure the response is in JSON format, which often helps with structured output
            "response_mime_type": "application/json",
            # The model is designed to return a structured JSON response for image tasks
            "response_schema": {
                "type": "object",
                "properties": {
                    "image_data_base64": {
                        "type": "string",
                        "description": "The base64 encoded PNG or JPEG string of the edited image."
                    },
                    "description": {
                        "type": "string",
                        "description": "A short description of the editing result."
                    }
                }
            }
        }
    }
    
    try:
        # Make the API request
        response = requests.post(API_URL, headers={"Content-Type": "application/json"}, json=payload)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # Parse the response and extract the necessary JSON content
        response_json = response.json()
        
        # Extract the text part which contains the structured JSON output from the model
        model_output_text = response_json['candidates'][0]['content']['parts'][0]['text']
        
        # The model output is a JSON string, so we need to parse it again
        model_output = json.loads(model_output_text)
        
        # The edited image is in the 'image_data_base64' field
        edited_image_base64 = model_output.get("image_data_base64")
        
        return edited_image_base64
        
    except requests.exceptions.HTTPError as e:
        # Handle API key issues, rate limits, etc.
        st.error(f"API Error: Could not reach the Gemini API. Check your key and permissions. Details: {e}")
        return None
    except Exception as e:
        # Handle parsing errors or other unexpected issues
        st.error(f"An unexpected error occurred: {e}")
        return None

# --- Streamlit Interaction Logic ---

# Check if an API call was triggered by the front-end JavaScript
if st.query_params.get('action') == ['generate']:
    
    # Get the image data and prompt from the hidden form fields passed via query parameters
    img_data_list = st.query_params.get('imageData')
    prompt_list = st.query_params.get('prompt')
    
    if img_data_list and prompt_list:
        base64_image = img_data_list[0]
        user_prompt = prompt_list[0]
        
        # Call the core function
        result_base64 = call_gemini_api(base64_image, user_prompt)
        
        if result_base64:
            # If successful, print the result base64 string to the Streamlit app.
            # The client-side JavaScript is listening for this output to update the image.
            st.code(f"RESULT_IMAGE_BASE64:{result_base64}", language="")
            
        # Clear the query parameters to prevent re-execution on refresh
        st.query_params.clear()
        
    # Stop the Python script to prevent rendering the default Streamlit UI
    st.stop()


# --- Main HTML Frontend Rendering ---
# If no action is triggered, render the custom HTML interface.

# Load the custom HTML and JS from the separate file
try:
    with open("index_for_streamlit.html", "r", encoding="utf-8") as f:
        html_code = f.read()
except FileNotFoundError:
    st.error("Error: 'index_for_streamlit.html' not found. Please ensure both files are in the same folder.")
    st.stop()

# Render the HTML using the Streamlit component
st.html(html_code)
