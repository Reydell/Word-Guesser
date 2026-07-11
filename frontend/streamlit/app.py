import requests
import streamlit as st


API_BASE_URL = "http://localhost:8000"


st.markdown(
    """
    <style>
    div[data-testid="stChatInput"] textarea {
        overflow: hidden !important;
    }

    div[data-testid="stChatInput"] textarea::-webkit-scrollbar {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Word Guessing Game")

if "game_id" not in st.session_state:
    st.session_state.game_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

def start_new_game():
    response = requests.post(f"{API_BASE_URL}/games/", timeout=10)
    response.raise_for_status()

    data = response.json()

    st.session_state.game_id = data["game_id"]
    st.session_state.messages = [
        {"role": "assistant", "content": data["message"]}
    ]

def send_message_to_backend(message: str) -> str:
    game_id = st.session_state.game_id

    response = requests.post(
        f"{API_BASE_URL}/games/{game_id}/messages",
        json={"message": message},
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    return data["message"]


if st.button("New game"):
    start_new_game()

if st.button("Print logs"):
    try:
        game_id = st.session_state.game_id
        response = requests.post(f"{API_BASE_URL}/games/{game_id}/logs", timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        st.error(f"Backend error: {error}")

if st.session_state.game_id is None:
    st.info("Click 'New game' to start.")
else:
    st.caption(f"Game ID: {st.session_state.game_id}")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if st.session_state.game_id is not None:
    user_message = st.chat_input("Ask a question or make a guess")

    if user_message:
        st.session_state.messages.append(
            {"role": "user", "content": user_message}
        )

        with st.chat_message("user"):
            st.write(user_message)

        try:
            assistant_message = send_message_to_backend(user_message)
        except requests.RequestException as error:
            assistant_message = f"Backend error: {error}"

        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_message}
        )

        with st.chat_message("assistant"):
            st.write(assistant_message)
