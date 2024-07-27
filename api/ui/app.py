import streamlit as st
from api.dependencyinjector import global_injector
from api.server.ragchat.ragchat_service import RagChatService
import os
os.environ["OPENAI_API_KEY"] = "your_openai_api_key"
from streamlit_server_state import server_state, server_state_lock, no_rerun
from datetime import datetime
import hmac
import pandas as pd
import json
import time
import uuid


def get_service():
    return global_injector.get(RagChatService)

def update_server_state(key, value):
        with no_rerun:
            with server_state_lock[key]:
                server_state[key] = value

def setup_metadata(settings):
    try:
        if "app_title" not in server_state:
            update_server_state(
                "app_title",
                settings.ui.app_title,
            )
    except Exception as e:
        st.write(f"failed to set the metadata, please check the settings file: {e}")

def determine_availability():
    if "users_list" not in st.session_state:
        st.session_state["users_list"] = pd.read_csv("metadata/user_list.csv")
    if "in_use" not in server_state:
        update_server_state("in_use", False)
    if "first_boot" not in st.session_state:
        st.session_state["first_boot"] = True
    else:
        st.session_state["first_boot"] = False
    if server_state["in_use"] and st.session_state["first_boot"]:
        st.session_state["available"] = False
    else:
        st.session_state["available"] = True
    if "user_name" in st.session_state:
        if (
            f'{st.session_state["user_name"]}_count' in server_state
            and "count" in st.session_state
        ):
            if (
                server_state[f'{st.session_state["user_name"]}_count']
                != st.session_state["count"]
            ):
                st.error("You have logged in on another tab.")
                st.stop()
                
def check_password():
    if "last_used" not in server_state:
        update_server_state("last_used", datetime.now())
    if (datetime.now() - server_state["last_used"]).total_seconds() > 60:
        update_server_state("in_use", False)
    if not (st.session_state["available"]):
        st.error("The model is currently generating, try again in a few seconds.")
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if st.session_state.get("password_correct", False):
        if st.session_state["available"]:
            return True
    st.session_state["user_name"] = st.text_input(
        "User",
        value="",
        placeholder="Enter user name...",
    )
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("Password incorrect")
    return False

def ui_header(settings):
    st.title(settings.ui.app_title)
    if "per_user" not in st.session_state:
        st.session_state["per_user"] = (
            st.session_state["user_name"].lower().replace(" ", "_")
        )
    if f'{st.session_state["user_name"]}_count' not in server_state:
        update_server_state(f'{st.session_state["user_name"]}_count', 1)
        st.session_state["count"] = 1
    else:
        update_server_state(
            f'{st.session_state["user_name"]}_count',
            server_state[f'{st.session_state["user_name"]}_count'] + 1,
        )
        st.session_state["count"] = server_state[
            f'{st.session_state["user_name"]}_count'
        ]

def import_styles():
    with open("styles/style.css") as css:
        st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)
    st.session_state["user_avatar"] = "https://www.svgrepo.com/show/425248/users-avatar.svg"
    st.session_state[
        "assistant_avatar"
    ] = "https://www.svgrepo.com/show/416376/artificial-bot-intelligence.svg"
    st.session_state["sources_avatar"] = "https://www.svgrepo.com/show/365316/database-thin.svg"
    if "finalresponse" not in st.session_state:
        st.session_state["finalresponse"] = ""

def delete_chat_history(chat_id,user_id,my_service):
    if f'{st.session_state["user_name"]} messages' in server_state:
        del server_state[f'{st.session_state["user_name"]} messages']
    my_service.delete_session_history(chat_id,user_id)

def ui_display_chat_history(my_service):
    allmessages = my_service.get_aggregated_history_per_user(st.session_state['user_name'])
    for chat_index, chat in enumerate(allmessages, start=1):
        chat_label = f"Chat {chat_index}"
        with st.sidebar.expander(chat_label):
            parsed_messages = [json.loads(message) for message in chat["History"]]
            for message_index, message in enumerate(parsed_messages, start=1):
                st.write(message['data']['content'])
            if st.button(f"Delete Chat {chat_index}", key=f"delete_{chat_index}"):
                delete_chat_history(chat["_id"], chat["user_id"],my_service)
                st.rerun()

def export_chat_history():
    chat_history = f'*{st.session_state["user_name"]}\'s chat history from {str(datetime.now().date())}*\n\n'
    counter = 1
    for message in server_state[f'{st.session_state["user_name"]} messages']:
        if "source_string" not in message["content"]:
            role = message["role"]
            if role == "user":
                chat_history += f'### {[counter]} {st.session_state["user_name"]}\n\n'
            else:
                chat_history += f"### {[counter]} LLM\n\n"
            chat_history += f'{message["content"]}\n\n'
        # sources
        else:
            if message["content"] != "source_string:NA":
                source_content = message["content"].split("<br>")[0]
                source_content = (
                    source_content.replace("source_string:", "")
                    .replace("### Metadata:", "\n### Metadata:\n")
                    .replace("### Text:", "\n### Text:\n")
                    .replace(" ```", "```")
                    .replace("# Source", f"### {[counter]} Source")
                )
                chat_history += (
                    "_**Sources**_:\n" + "<br>" + message["content"].split("<br>")[1]
                )
                chat_history += "<details>\n"
                chat_history += source_content
                chat_history += "\n</details>\n\n"
            counter += 1
    return chat_history

def ui_export_chat_end_session():
    if f'{st.session_state["user_name"]} messages' in server_state:
        st.session_state["export_chat_button"] = st.sidebar.download_button(
            label="Export chat history",
            data=export_chat_history(),
            file_name="chat_history.MD",
            help="Export the current session's chat history to a formatted Markdown file.",
        )
    end_session = st.sidebar.button("End session", help="End your session.")
    if end_session:
        update_server_state(
            f'{st.session_state["user_name"]} messages', []
        )  
        st.session_state["password_correct"] = False
        st.session_state["user_name"] = ""
        update_server_state(f'{st.session_state["user_name"]}_session_id', "")
        st.session_state["alreadyinitiated"] = False
        st.rerun()

def populate_chat():
    st.session_state["message_box"] = st.empty()
    if f'{st.session_state["user_name"]} messages' in server_state:
        with st.session_state["message_box"].container():
            for message in server_state[f'{st.session_state["user_name"]} messages']:
                if message["role"] == "user":
                    avatar = st.session_state["user_avatar"]
                elif message["role"] == "sources_avatar":
                    avatar = st.session_state["sources_avatar"]
                else:
                    avatar = st.session_state["assistant_avatar"]
                with st.chat_message(message["role"], avatar=avatar):
                    if "source_string" not in message["content"]:
                        st.markdown(message["content"], unsafe_allow_html=True)
                    else:
                        st.markdown(
                            "Sources: "
                            + "<br>"
                            + message["content"].split("string:")[1].split("<br>")[1],
                            unsafe_allow_html=True,
                            help=message["content"]
                            .split("string:")[1]
                            .split("<br>")[0],
                        )

def generate_session_id():
    "generate a session id"
    update_server_state(f'{st.session_state["user_name"]}_session_id', str(uuid.uuid4()))

def format_docs(docs):
            return {
            'sources': [str(d.metadata.get('page', '')) + ' ' + str(d.metadata.get('source', '')) for d in docs]}

def streamed_response(streamer):
    "stream the LLM's response"
    with st.spinner("Thinking..."):
        for token in streamer:
            if 'answer' in token:
                yield token['answer']
                st.session_state["finalresponse"] += token['answer']
            if 'context' in token:
                st.session_state[f'{st.session_state["user_name"]} retriever_output'] = format_docs(token['context'])

def import_chat(my_service):

    if f'model_{st.session_state["per_user"]}' in server_state:
        if f'{st.session_state["user_name"]} messages' not in server_state:
            update_server_state(f'{st.session_state["user_name"]} messages', [])

        if not (
            f'model_{st.session_state["per_user"]}' not in server_state
        ):
            populate_chat()
        placeholder_text = (
                "Ask...'The monolith exposes APIs or interfaces. How do we break them down into microservices?'"
            )
        
        if prompt := st.chat_input(placeholder_text):
            prompt_time = f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
            with st.chat_message("user", avatar=st.session_state["user_avatar"]):
                st.markdown(prompt + prompt_time, unsafe_allow_html=True)
            update_server_state(
                f'{st.session_state["user_name"]} messages',
                server_state[f'{st.session_state["user_name"]} messages']
                + [{"role": "user", "content": prompt + prompt_time}],
            )

            # lock the model to perform requests sequentially
            if "in_use" not in server_state:
                update_server_state("in_use", False)
            if "last_used" not in server_state:
                update_server_state("last_used", datetime.now())

            if "exec_queue" not in server_state:
                update_server_state("exec_queue", [st.session_state["user_name"]])
            if len(server_state["exec_queue"]) == 0:
                update_server_state("exec_queue", [st.session_state["user_name"]])
            else:
                if st.session_state["user_name"] not in server_state["exec_queue"]:
                    # add to the queue
                    update_server_state(
                        "exec_queue",
                        server_state["exec_queue"] + [st.session_state["user_name"]],
                    )

            with st.spinner("Query queued..."):
                t = st.empty()
                while (
                    server_state["in_use"]
                    or server_state["exec_queue"][0] != st.session_state["user_name"]
                ):
                    # check if it hasn't been used in a while, potentially interrupted while executing
                    if (
                        datetime.now() - server_state["last_used"]
                    ).total_seconds() > 60:
                        if (
                            server_state["exec_queue"][1]
                            == st.session_state["user_name"]
                        ):  # only perform if first in the queue
                            update_server_state("in_use", False)
                            update_server_state(
                                "exec_queue", server_state["exec_queue"][1:]
                            ) # take out of the queue
                            update_server_state("last_used", datetime.now())

                    t.markdown(
                        f'You are place {server_state["exec_queue"].index(st.session_state["user_name"])} of {len(server_state["exec_queue"]) - 1}'
                    )
                    time.sleep(1)
                t.empty()

            # lock the model while generating
            update_server_state("in_use", True)
            update_server_state("last_used", datetime.now())

            # generate response
            try:
                if f'{st.session_state["user_name"]}_session_id' not in server_state:
                    generate_session_id()
                response = my_service.stream(server_state[f'{st.session_state["user_name"]} messages'][
                        -1
                    ]["content"][
                        : -(
                            len(
                                f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
                            )
                        )
                    ], server_state[f'{st.session_state["user_name"]}_session_id'], st.session_state["user_name"])
                chat_placeholder = st.empty()
                source_placeholder = st.empty()
                source_placeholder.empty()
                chat_placeholder.empty()
                with chat_placeholder.chat_message(
                    "assistant", avatar=st.session_state["assistant_avatar"]
                ):
                    with st.empty():
                        st.write_stream(streamed_response(response.response))
                
                with source_placeholder.chat_message(
                    "sources_avatar", avatar=st.session_state["sources_avatar"]
                ):
                        if f'{st.session_state["user_name"]} retriever_output' in st.session_state and "sources" in st.session_state[f'{st.session_state["user_name"]} retriever_output']: 
                            response_time = f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
                            source_string = ""
                            counter = 1
                            for source_path in st.session_state[f'{st.session_state["user_name"]} retriever_output']["sources"]:
                                parts = source_path.split(' ', 1)
                                page_info = parts[0]
                                path = parts[1]
                                file_name = path.split('/')[-1]
                                source_string += f"**Source {counter}**: Page {page_info} {file_name}\n\n"
                                counter += 1
                            st.markdown(
                                "Sources: " + response_time,
                                unsafe_allow_html=True,
                                help=f"{source_string}",
                            )
                            del st.session_state[f'{st.session_state["user_name"]} retriever_output']                    

                update_server_state("in_use", False)
                update_server_state(
                    "exec_queue", server_state["exec_queue"][1:]
                ) 

                update_server_state(
                    f'{st.session_state["user_name"]} messages',
                    server_state[f'{st.session_state["user_name"]} messages']
                    + [{"role": "assistant", "content": st.session_state["finalresponse"]}],
                )
                update_server_state(
                    f'{st.session_state["user_name"]} messages',
                    server_state[f'{st.session_state["user_name"]} messages']
                    + [
                        {
                            "role": "sources_avatar",
                            "content": f"source_string:{source_string}{response_time}",
                        }
                    ],
                )
                st.session_state["finalresponse"] = "" 
            except Exception as e:
                st.error(f"An error was encountered.: {e}")
                update_server_state("in_use", False)
                update_server_state(
                    "exec_queue", server_state["exec_queue"][1:]
                )



def main():
    my_service = get_service()
    settings = my_service.getsettings()
    setup_metadata(settings)
    determine_availability()

    if not check_password():
        st.stop()
    st.set_page_config(
        page_title=server_state["app_title"],
        page_icon="https://www.svgrepo.com/show/87025/female-assistant-of-a-call-center.svg",
    )
    ui_header(settings)
    update_server_state(f'model_{st.session_state["per_user"]}', my_service._with_message_history())
    import_styles()
    ui_display_chat_history(my_service)
    import_chat(my_service)
    ui_export_chat_end_session()


if __name__ == "__main__":
    main()