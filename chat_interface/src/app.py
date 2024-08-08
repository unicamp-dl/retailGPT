import streamlit as st
from chatbot import get_chatbot_response, reset_chatbot_conversation
from PIL import Image
from utils.data_utils import chat_to_word, generate_conversation_id

# Set page title
im = Image.open("./images/neuralmind.png")
st.set_page_config(page_title="Retail-GPT prototype demo", page_icon=im)

# Hide default Streamlit footer and menu
hide_default_format = """
       <style>
       #MainMenu {visibility: hidden; }
       footer {visibility: hidden;}
       </style>
       """
st.markdown(hide_default_format, unsafe_allow_html=True)

if "conversation_id" not in st.session_state:
    st.session_state["conversation_id"] = generate_conversation_id()

# If there are no messages, start new conversation and chatbot
if "messages" not in st.session_state:
    st.session_state["messages"] = []

st.title("💬 Retail-GPT prototype demonstration")


def process_reset_button_click() -> None:
    """Resets the chatbot conversation."""
    st.session_state.pop("messages", None)
    reset_chatbot_conversation(st.session_state["conversation_id"])


with st.sidebar:
    st.write("Use this interface to interact with Retail-GPT and place orders at an fictional Foo convenience store.")
    st.button("Restart conversation", on_click=process_reset_button_click)
    st.write(
        "👇 You can download the current conversation as a Word document by clicking the button below."
    )
    conversation_docx = chat_to_word(st.session_state.messages)
    st.download_button(
        "Download conversation as Word file",
        conversation_docx,
        file_name="conversation_history.docx",
    )
    st.header("Usage Instructions")
    st.write(
        "**Read the instructions below for better testing the chatbot.**"
    )
    st.write(
        "Send a message to start a conversation. The chatbot will guide you through the ordering process and can perform the following actions:"
    )
    st.write("- Check the availability of desired products")
    st.write("- Provide recommendations based on your needs")
    st.write("- Add and remove products from your cart")
    st.write("- Finalize the order when you show interest.")
    st.write("Actions other than these are not supported in this version.")
    st.write(
        "Feel free to send messages with typos, slang, or abbreviations, simulating a real user."
    )
    st.write(
        "Try requesting more than one product or operation at a time to explore the chatbot's potential."
    )
    st.subheader("ZIP Code Conventions:")
    st.write(
        "We will use your ZIP code to simulate your purchase history. Therefore, consider the following conventions for ZIP codes:"
    )
    st.write(
        "- **ZIP codes ending in 0 - 3:** For each case, the user will have a different purchase history, so the chatbot can process messages like 'I want the same as yesterday'."
    )
    st.write(
        "- **ZIP codes ending in 4 - 9:** The user has no purchase history."
    )
    st.write(
        "For cases with purchase history, consider that the chatbot only knows about purchases on days relative to the current day, like 'yesterday', '10 days ago', or 'last month'. In other words, it is not yet able to process absolute dates."
    )
    st.subheader("Catalog and product search:")
    st.write(
        "During the conversation, a fictitious catalog with 50 products based on what is commonly found in convenience stores will be used. Not every real product is present in the fictitious catalog."
    )
    st.write(
        "For testing purposes, some of the various products available in the complete catalog, for ZIP codes starting with 1 - 8, are:"
    )
    st.write("- Guaraná Antarctica 350ml")
    st.write("- Budweiser 600ml")
    st.write("- Vinho Branco Seco Relevos 750ml")
    st.write("- Vodka Absolut Original 1L")
    st.write("- Whisky Jack Daniels 1L")
    st.write(
        "The recommendation and product search system used was developed for this demonstration and does not necessarily reflect the performance of a real search mechanism."
    )


def process_button_click(value, title) -> None:
    """Processes button click and adds the user message to the state."""
    st.session_state.messages.append({"role": "user", "content": title})
    process_message(value)
    # The user message (button reply) and the response are added to the state
    # The button click action refreshes the page, rerunning the display_messages function
    # Therefore, there is no need to call display_messages again here


def display_textual_message(message: dict) -> None:
    """Displays textual messages in the chat window."""

    role = message["role"]
    content = message["content"].replace("\n\n", "\n")

    st.chat_message(role).write(content)


def display_messages(messages=st.session_state.messages) -> None:
    """Displays messages in the chat window."""

    for msg in messages:
        if msg["role"] == "assistant" or msg["role"] == "user":
            display_textual_message(msg)

    # Do not render buttons in the middle of the conversation, only at the end of it:
    if messages and messages[-1]["role"] == "button_pair":
        for button in messages[-1]["content"]:
            title = button["title"]
            value = button["payload"]
            st.button(
                title,
                on_click=lambda value=value, title=title: process_button_click(
                    value, title
                ),
            )


def process_message(user_message: str) -> None:
    """Receives user message and processes it."""
    with st.spinner("Please wait while your message is processed..."):
        bot_responses = get_chatbot_response(
            user_message, st.session_state["conversation_id"]
        )
        for bot_response in bot_responses:
            if "text" in bot_response:
                # Escape $ character to avoid LaTeX rendering:
                content = bot_response["text"].replace("$", "\\$")
                response_dict = {"role": "assistant", "content": content}
                st.session_state.messages.append(response_dict)
            if "buttons" in bot_response:
                # Considering that the buttons come in pairs for positive and negative answers:
                response_dict = {
                    "role": "button_pair",
                    "content": bot_response["buttons"],
                }
                st.session_state.messages.append(response_dict)


display_messages()

if user_message := st.chat_input(placeholder="Type your message here..."):
    st.session_state.messages.append({"role": "user", "content": user_message})
    st.chat_message("user").write(user_message)
    process_message(user_message)

    # Rerun the app to display the messages and mount an updated download button
    # Streamlit roadmap plans (in May - July 2024) a feature to mount the
    # download button content dynamically, without the need to rerun the app
    # If such feature is added, we could just display the processed message here and
    # mount the download button dynamically
    st.rerun()
