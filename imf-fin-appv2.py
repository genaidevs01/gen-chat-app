import streamlit as st
import os
import pandas as pd
import time
from datetime import datetime
from typing import Dict, Any
from openai import OpenAI
import truststore
import warnings
warnings.filterwarnings("ignore")




# Streamlit App UI
st.set_page_config(page_title="RCA Assistant", layout="wide")
# Inject system trust store
truststore.inject_into_ssl()

# Initialize OpenAI client


# --- Step 1: Prompt user for OpenAI API Key ---
api_key = st.text_input("Enter your OpenAI API Key", type="password")

if not api_key:
    st.warning("🔐 Please enter your OpenAI API key to access the app.")
    st.stop()
else:
    client = OpenAI(api_key=api_key)
    st.success("✅ API Key Confirmed")

# --- Rest of the app runs only after key is provided ---




# Assistant IDs
assistant_ids = {
    'intent_classifier': 'asst_3nJmmwEE7SAgjYVCC3N1Wn7t',
    'agent1': 'asst_xR3QVv3jzntRMD7pLeiUphtE',
    'agent2': 'asst_WZT3SL1fCbALbR3OvhRnQnbk',
    'agent3': 'asst_Y7smtsNhDmWn4FXiDQsZQS0D',
    'agent4': 'asst_mAqTXiLu8N2zDFH2TUoeDKma'
}



# Logo
logo_path = "C:/Users/US765HN/OneDrive - EY/Documents/RCA Chatbot/StreamlitRCABOT/ey-logo-black.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=150)

st.title("Root Cause Analysis Assistant")


# data = {
#     "Category": ["MEDICAL SUPPLIES", "HOUSE CARE"],
#     "Actuals": [3074, 2223],
#     "prediction_xgb": [2803, 2656.78],
#     "FA": [91.1841, 80.4867],
#     "FB": [9.6682, -16.3273]
# }

# df = pd.DataFrame(data)
# st.table(df)



data = {
    "Category": ["MEDICAL SUPPLIES", "HOUSE CARE"],
    "Actuals": [3074, 2223],
    "Predictions": [2803, 2656.78],
    "FA": [91.1841, 80.4867],
    "FB": [9.6682, -16.3273]
}
df = pd.DataFrame(data)

# Heading
st.markdown("## 📊 ScoreCard")

# HTML Table
styled_table = df.to_html(index=False, justify='right', classes='custom-table')

# CSS Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible&display=swap');

.custom-table {
    border-collapse: collapse;
    width: 100%;
    font-family: 'ATOS', 'Atkinson Hyperlegible', sans-serif;
    font-size: 15px;
}
.custom-table th {
    background-color: #FFD700; /* Yellow */
    color: black;
    padding: 12px 10px;
    border: 1px solid #ddd;
    text-align: right;
}
.custom-table td {
    background-color: #000;
    color: white;
    padding: 10px 10px;
    border: 1px solid #444;
    text-align: right;
}
</style>
""", unsafe_allow_html=True)

# Render Table
st.markdown(styled_table, unsafe_allow_html=True)
global fb 











# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def call_assistant(assistant_id: str, messages: list) -> Dict[str, Any]:
    thread = client.beta.threads.create()
    for message in messages:
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role=message["role"],
            content=message["content"]
        )
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status == "completed":
            break
        elif run_status.status == "failed":
            raise Exception("Run failed.")
        time.sleep(0.5)

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    text_output = ""
    image_file_id = None

    for message in messages.data:
        if message.role == "assistant":
            for part in message.content:
                if part.type == "text":
                    text_output += part.text.value.strip() + "\n"
                elif part.type == "image_file":
                    image_file_id = part.image_file.file_id
            break

    image_path = None
    if image_file_id:
        image_response = client.files.content(image_file_id)
        image_bytes = image_response.read()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("images", exist_ok=True)
        image_path = os.path.join("images", f"graph_{timestamp}.png")
        with open(image_path, "wb") as f:
            f.write(image_bytes)

    return {
        "text": text_output.strip(),
        "image_path": image_path
    }

def detect_intent_openai(query: str) -> Dict[str, bool]:
    prompt = (
        "Given the user query below, return a JSON with these keys:\n"
        "only_graph, only_key, wants_reason, wants_graph, full_rca.\n"
        "Return only the JSON.\n\n"
        f"User query: {query}"
    )
    result = call_assistant(
        assistant_ids["intent_classifier"],
        [{"role": "user", "content": prompt}]
    )
    try:
        return eval(result["text"])
    except:
        raise ValueError("Failed to parse intent JSON from assistant output:\n" + result["text"])

def master_router(user_query: str) -> Dict[str, Any]:
    intent = detect_intent_openai(user_query)
    response_log = {}
    image_path = None
    print(intent)

    if intent["only_graph"]:
        a4_result = call_assistant(assistant_ids["agent4"], [{"role": "user", "content": user_query}])
        response_log["A4"] = a4_result["text"]
        image_path = a4_result.get("image_path")

    elif intent["only_key"]:
        a1_result = call_assistant(assistant_ids["agent1"], [{"role": "user", "content": user_query}])
        response_log["A1"] = a1_result["text"]

    elif intent["full_rca"]:
        a1_result = call_assistant(assistant_ids["agent1"], [{"role": "user", "content": user_query}])
        response_log["A1"] = a1_result["text"]

        a2_prompt = f"User query: {user_query}\nAgent 1 response: {a1_result['text']}"
        a2_result = call_assistant(assistant_ids["agent2"], [{"role": "user", "content": a2_prompt}])
        response_log["A2"] = a2_result["text"]

        a3_prompt = f"{a2_prompt}\nAgent 2 response: {a2_result['text']}"
        a3_result = call_assistant(assistant_ids["agent3"], [{"role": "user", "content": a3_prompt}])
        response_log["A3"] = a3_result["text"]

        a4_prompt = f"{a3_prompt}\nAgent 3 response: {a3_result['text']}"
        a4_result = call_assistant(assistant_ids["agent4"], [{"role": "user", "content": a4_prompt}])
        response_log["A4"] = a3_result["text"]
        image_path = a4_result.get("image_path")

    else:
        a1_result = call_assistant(assistant_ids["agent1"], [{"role": "user", "content": user_query}])
        response_log["A1"] = a1_result["text"]

        a2_prompt = f"User query: {user_query}\nAgent 1 response: {a1_result['text']}"
        a2_result = call_assistant(assistant_ids["agent2"], [{"role": "user", "content": a2_prompt}])
        response_log["A2"] = a2_result["text"]

        escalate_to_a3 = len(a2_result["text"]) < 100 or intent["wants_reason"]
        if escalate_to_a3:
            a3_prompt = f"{a2_prompt}\nAgent 2 response: {a2_result['text']}"
            a3_result = call_assistant(assistant_ids["agent3"], [{"role": "user", "content": a3_prompt}])
            response_log["A3"] = a3_result["text"]
            fb = a3_result["text"]

        if intent["wants_graph"]:
            last_text = response_log.get("A3") or response_log.get("A2")
            a4_prompt = f"{a2_prompt}\nGraph needed.\nRCA Response: {last_text}"
            a4_result = call_assistant(assistant_ids["agent4"], [{"role": "user", "content": a4_prompt}])
            response_log["A4"] = a3_result["text"]
            image_path = a4_result.get("image_path")
            

    return {
        "final_output": response_log.get("A4") or response_log.get("A3") or response_log.get("A2") or response_log.get("A1"),
        "image_path": image_path
    }

# User Input
user_query = st.text_input("Enter your query:", placeholder="e.g., Generate a graph for Dressing Category")

if st.button("Submit") and user_query:
    with st.spinner("Processing..."):
        result = master_router(user_query)
        st.session_state.chat_history.append((user_query, result["final_output"], result.get("image_path")))

# Display chat history
for q, r, img in reversed(st.session_state.chat_history):
    st.markdown(f"**You:** {q}")
    st.markdown(f"**Assistant:** {r}")
    if img and os.path.exists(img):
        st.image(img, caption="Generated Graph", use_column_width=True)
    st.markdown("---")
