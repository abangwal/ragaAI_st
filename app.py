import streamlit as st
import requests
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    PrerecordedOptions,
    FileSource,
)
from io import BytesIO
import os
import warnings

# Page configuration
st.set_page_config(page_title="Market Brief Chat", page_icon="💬", layout="wide")
DG_API = os.getenv("DG_API")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "How can I help you today?"}
    ]
if "um" not in st.session_state:
    st.session_state.um = None

# Initialize other session state variables
if "is_recording" not in st.session_state:
    st.session_state.is_recording = False


def STT(buffer):

    config: DeepgramClientOptions = DeepgramClientOptions(api_key=DG_API)
    deepgram: DeepgramClient = DeepgramClient("", config)
    payload: FileSource = {
        "buffer": buffer,
    }
    # STEP 2: Configure Deepgram options for audio analysis
    options = PrerecordedOptions(
        model="nova-3",
        smart_format=True,
    )
    # STEP 3: Call the transcribe_file method with the text payload and options
    response = deepgram.listen.rest.v("1").transcribe_file(payload, options)

    data = response.to_json()
    warnings.warn(str(data))

    transcript = data["results"]["channels"][0]["alternatives"][0]["transcript"]

    return transcript


def TTS(text):
    DEEPGRAM_URL = "https://api.deepgram.com/v1/speak?model=aura-2-thalia-en"
    DEEPGRAM_API_KEY = DG_API

    payload = {"text": text}

    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json",
    }

    # Create a BytesIO buffer to store audio
    audio_buffer = BytesIO()

    response = requests.post(DEEPGRAM_URL, headers=headers, json=payload)

    audio_buffer.write(response.content)

    # Move cursor to the beginning of the buffer
    audio_buffer.seek(0)
    return audio_buffer


# App title
st.markdown("<h1>💬 Market Brief Chat</h1>", unsafe_allow_html=True)
st.markdown("---")


# Display chat history
chat_col, audio_col = st.columns([0.85, 0.15])
with chat_col:
    c = st.container(height=400, border=True)
    with c:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

with audio_col:
    # Voice input buttonif
    data = st.audio_input(label="🎤 Record")
    if data:
        st.session_state.um = STT(data)
    if st.button("🔊 listen"):
        text = st.session_state.messages[-1]["content"]
        buffer = TTS(text)
        st.audio(data=buffer)
        st.success("Playing")

# Voice input button (beside text input conceptually)
# Handle text input
user_input = st.chat_input("Ask me about market trends...")
st.session_state.um = user_input
if st.session_state.um:
    with c:
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append(
            {"role": "user", "content": st.session_state.um}
        )

        data = {"query": user_input, "history": st.session_state.messages[-5::]}
        or_response = requests.post(
            url="https://ashishbangwal-ragaai.hf.space/orchestrator/orchestrator_decision",
            json=data,
        )

        try:
            context = or_response.json()["response"]
        except:
            context = or_response.text

        print(or_response)

        agent_response = ""
        data = {
            "query": user_input,
            "context": context,
            "history": st.session_state.messages[-5::],
        }
        full_response = requests.post(
            url="https://ashishbangwal-ragaai.hf.space/orchestrator/final_response",
            json=data,
            stream=True,
        )
        with st.chat_message("assistant"):
            placeholder = st.empty()
            for chunk in full_response.iter_content(
                decode_unicode=True, chunk_size=None
            ):
                agent_response += chunk
                placeholder.markdown(agent_response + "▌")

        st.session_state.messages.append(
            {"role": "assistant", "content": agent_response}
        )
        st.session_state.um = None
        st.rerun()
