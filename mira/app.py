# -*- coding: utf-8 -*-
"""Mira Web Interface (Streamlit)."""
import streamlit as st
import time
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mira.core.router import process_message
from mira.voice import generate_audio

st.set_page_config(page_title="Mira AI", page_icon="🦋", layout="wide")

# Custom CSS for chat style
st.markdown("""
<style>
.user-msg {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 10px;
    margin-bottom: 0.5rem;
    text-align: right;
}
.mira-msg {
    background-color: #e8f0fe;
    padding: 1rem;
    border-radius: 10px;
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

st.title("🦋 Mira")
st.markdown("*Your Local AI Companion*")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add welcome message
    st.session_state.messages.append({"role": "assistant", "content": "Hej! I'm listening. What's on your mind?"})

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
# Sidebar for inputs
with st.sidebar:
    st.header("Inputs")
    uploaded_file = st.file_uploader("Upload an Image", type=['png', 'jpg', 'jpeg'])
    
image_context = ""
if uploaded_file is not None:
    # Save file
    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "data", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"Loaded: {uploaded_file.name}")
    image_context = f"\n[IMAGE UPLOADED: {os.path.abspath(file_path)}]\n"

# User Input
if prompt := st.chat_input("Type your message..."):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Check for commands first
            from mira.core.commands import handle_command
            
            # Combine image context with prompt for processing logic (but not display)
            full_prompt = prompt + image_context
            is_cmd, cmd_resp = handle_command(prompt)
            
            if is_cmd:
                response_text = cmd_resp
            else:
                response_text = process_message(full_prompt)
            
            st.markdown(response_text)
            
            # save to state
            st.session_state.messages.append({"role": "assistant", "content": response_text})

            # Voice Generation
            audio_file = generate_audio(response_text)
            if audio_file:
                st.audio(audio_file, format="audio/mp3", autoplay=True)
                # Note: autoplay might be blocked by browsers, but we try.
