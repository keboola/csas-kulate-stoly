import streamlit as st
import base64
import os

def get_image_base64(image_path: str):
    """Get base64 representation of an image.
    Args:
        image_path (str): Path to the image.
    Returns:
        str: Base64 representation of the image.
    """
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def display_header(text: str = ''):
    # Adjust the logo path and base64 encoding
    image_path = os.path.join(os.path.dirname(__file__), './static/logo.png')
    LOGO = get_image_base64(image_path)
    LABEL = "Kulaté stoly"
    
    # Custom CSS for the header
    st.markdown("""
        <style>
        .header-container {
            background-color: #2870ed;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 0.5rem;
            padding: 0.5em 1em;
            margin-bottom: 1em;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .header-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: nowrap;
            width: 100%;
        }
        .header-text {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        }
        .header-title {
            color: #FFFFFF;
            font-size: 20px;
            margin: 0;
            font-weight: 600;
        }
        .header-subtitle {
            color: rgba(255, 255, 255, 0.7);
            font-size: 12px;
            margin: 0;
        }
        .header-logo {
            height: 60px;
            max-width: 100%;
            margin-left: auto;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header HTML
    st.markdown(f"""
        <div class="header-container">
            <div class="header-content">
                <div class="header-text">
                    <p class="header-title">{LABEL}</p>
                    <p class="header-subtitle">{text}</p>
                </div>
                <img src="data:image/png;base64,{LOGO}" alt="Logo" class="header-logo">
            </div>
        </div>
    """, unsafe_allow_html=True)
