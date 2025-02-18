import streamlit as st
import base64
import os
from streamlit_extras.stylable_container import stylable_container

    
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
    
    # Stylable container with smaller padding and adjusted CSS
    with stylable_container(
        key="container_with_border",
        css_styles="""
            {
                background-color: #2870ed;
                border: 1px solid rgba(49, 51, 63, 0.2);
                border-radius: 0.5rem;
                padding: 0.1em;
                width: 100%;  /* Full width for blue box */
                min-height: 70px;  /* Ensures enough height for logo and text */
            }
        """,
    ):
        with st.container():
            st.markdown(f"""
                <div class="compact-header-container" style="
                    display: flex; 
                    align-items: center; 
                    justify-content: space-between; 
                    padding: 0px 20px;  
                    flex-wrap: nowrap;  /* Prevents line breaks */
                    width: 100%;
                ">
                    <div style="
                        display: flex; 
                        flex-direction: column;
                        align-items: flex-start;
                    ">
                        <p style="
                            color: #FFFFFF;
                            font-size: 20px;
                            margin: 0;
                        ">{LABEL}</p>
                        <p style="
                            color: lightGrey;
                            font-size: 12px;  
                            margin: 0;
                            padding-bottom: 0px;
                        ">{text}</p>
                    </div>
                    <img src="data:image/png;base64,{LOGO}" alt="Logo" style="
                        height: 60px; 
                        max-width: 100%;
                        margin-left: auto;  /* Pushes logo to the right */
                        padding-top: 0;
                    ">
                </div>
                """, unsafe_allow_html=True
            )



            
