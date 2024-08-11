from loguru import logger
from services.ava_service import AvaService, ContactInfo
from ava.ava import ChatMessage
import streamlit as st

# initialize Ava service
if ["ava_service"] not in st.session_state:
    st.session_state["ava_service"] = AvaService()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

ava_service:AvaService = st.session_state.ava_service

dummy_contact_tayler = {
    "id": "3fnq8LpXHRtBvMzS5Ykd",
    "full_name": "Taylor Johnson",
    "first_name": "Taylor",
    "last_name": "Johnson",
    "address": "1472 Prairie Lane, Springfield, IL, 62701, United States",
    "city": "Springfield",
    "state": "IL",
    "timezone": None,
    "lead_state": None,
    "phone_number": "217-555-0164",
    "email": "test@pragmaticai.com",
    "pre_qualification_qa": {
        "roof_age": "5_to_10_years",
        "credit_score": "680_to_719",
        "average_monthly_electric_bill": "$100_to_$150",
        "annual_household_income": "$60,000_to_$80,000",
        "homeowner": "yes",
    },
}

dummy_contact_karan = {
    "id": "3fnq8LpXHRtBvMzS5Ykd",
    "full_name": "Karan Singh",
    "first_name": "Karan",
    "last_name": "Singh",
    "address": "1922 south wells st, chicago, IL, United States",
    "city": "Chicago",
    "state": "IL",
    "timezone": None,
    "lead_state": None,
    "phone_number": "217-555-0164",
    "email": "test@pragmaticai.com",
    "pre_qualification_qa": {
        "roof_age": "5_to_10_years",
        "credit_score": "more than 650",
        "average_monthly_electric_bill": "$200_to_$300",
        "annual_household_income": "$60,000_to_$80,000",
        "homeowner": "yes",
    },
}
dummy_contact = ContactInfo(**dummy_contact_karan)

st.title("AVA Solicia")

def get_message_history():
    return st.session_state.messages

def add_message_to_history(role, content, generated=None):
    st.session_state.messages.append({"role": role, "content": content, generated: generated})

def convert_st_chat_message(st_chat_messages):
    messages = []
    for message in st_chat_messages:
        messages.append(ChatMessage(role=message["role"], content=message["content"]))
    
    return messages

def respond_to_user():
    prompt = st.session_state.chat_input
    
    if prompt is None or prompt.strip() == "":
        logger.warning("User input is empty, no message will be generated.")
        return
    add_message_to_history("user", prompt)
    generate_response()

def generate_response():
    # generate ava response
    st_chat_messages = get_message_history()
    logger.info(f"Chat history: {st_chat_messages}")
    messages = convert_st_chat_message(st_chat_messages)
    generated, response = ava_service.respond(dummy_contact, messages)
    add_message_to_history("assistant", response, generated)


# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("generated") is not None and message["generated"]:
            st.markdown(f"notification to user: {message['generated']}")
        else:
            st.write(message["content"])


# Create a container with a border
container = st.container(border=True)

# Create two columns within the container
col1, col2 = container.columns(2)

# Add buttons to each column
col1.button("Clear chat history", on_click=lambda: st.session_state.pop("messages", None), use_container_width=True)
col2.button(
    "Generate AVA message", on_click=generate_response, use_container_width=True
)

# React to user input
st.chat_input("your response here...", on_submit=respond_to_user, key="chat_input")
