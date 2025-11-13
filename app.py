import streamlit as st
import os
import requests
import json
import base64
from PIL import Image
import io

# --- Streamlit Page Configuration ---
st.set_page_config(layout="centered")

# --- Security Check ---
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    st.error("Error: GEMINI_API_KEY environment variable not set. Please set it in Streamlit Cloud secrets.")
    st.stop()

# --- Gemini API Configuration ---
MODEL_NAME = "gemini-2.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

# --- Core Function to Call Gemini API ---
def call_gemini_api(base64_image_data, prompt):
    """Sends the image and prompt to the Gemini API."""
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg", 
                            "data": base64_image_data
                        }
                    }
                ]
            }
        ],
        "config": {
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "object",
                "properties": {
                    "image_data_base64": {"type": "string"},
                    "description": {"type": "string"}
                }
            }
        }
    }
    
    try:
        response = requests.post(API_URL, headers={"Content-Type": "application/json"}, json=payload)
        response.raise_for_status() 

        response_json = response.json()
        model_output_text = response_json['candidates'][0]['content']['parts'][0]['text']
        model_output = json.loads(model_output_text)
        edited_image_base64 = model_output.get("image_data_base64")
        
        return edited_image_base64
        
    except requests.exceptions.HTTPError as e:
        st.error(f"API Error: Could not reach the Gemini API. Details: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

# --- Callback Function for File Uploader ---
def handle_upload():
    """Converts uploaded file to Base64 and stores it in session state."""
    uploaded_file = st.session_state.file_uploader
    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        base64_data = base64.b64encode(file_bytes).decode('utf-8')
        
        # Store data in Session State
        st.session_state.base64_data = base64_data
        st.session_state.filename = uploaded_file.name
    else:
        # Clear data if file is cleared
        st.session_state.base64_data = ""
        st.session_state.filename = "Awaiting Source Image"


# --- Streamlit Interaction Logic ---

# Initialize session state keys
if 'base64_data' not in st.session_state:
    st.session_state.base64_data = ""
if 'filename' not in st.session_state:
    st.session_state.filename = "Awaiting Source Image"


# 1. Place the Native Streamlit File Uploader
# Use a key and the callback function for state management
uploaded_file_widget = st.file_uploader(
    "Upload Source Image (Max 20MB)", 
    type=['png', 'jpg', 'jpeg'],
    key="file_uploader", # Key to access the widget value
    on_change=handle_upload, # Function to run when file changes
    help="Use the native Streamlit uploader for reliable file handling."
)


# 2. Check for External API Call (Triggered by HTML Button)
if st.query_params.get('action') == ['generate']:
    img_data_list = st.query_params.get('imageData')
    prompt_list = st.query_params.get('prompt')
    
    if img_data_list and prompt_list:
        base64_image = img_data_list[0]
        user_prompt = prompt_list[0]
        
        result_base64 = call_gemini_api(base64_image, user_prompt)
        
        if result_base64:
            # Pass the result back to the HTML
            st.code(f"RESULT_IMAGE_BASE64:{result_base64}", language="")
            
        st.query_params.clear()
        
    st.stop()


# 3. Pass Session State Data to Custom HTML
base64_data_for_html = st.session_state.base64_data
filename = st.session_state.filename

# Use an st.code block to pass the file data and name to the custom HTML
st.code(f"UPLOADED_BASE64:{base64_data_for_html}\nUPLOADED_FILENAME:{filename}", language="")


# 4. Load and render the custom HTML/CSS
try:
    with open("index_for_streamlit.html", "r", encoding="utf-8") as f:
        html_code = f.read()
except FileNotFoundError:
    st.error("Error: 'index_for_streamlit.html' not found.")
    st.stop()

# Render the HTML using the Streamlit component
st.html(html_code)
