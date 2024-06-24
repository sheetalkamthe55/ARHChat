import streamlit as st
from streamlit_server_state import server_state
from utils.user import update_server_state,clear_models
from datetime import datetime
import time
import uuid
from utils.model import get_session_history
import json

# MongoDB aggregation pipeline


def generate_session_id():
    "generate a session id"
    st.session_state["session_id"] = str(uuid.uuid4())

def ui_tab():
    "tab title and icon"
    st.set_page_config(
        page_title=server_state["app_title"],
        page_icon="https://www.svgrepo.com/show/375527/ai-platform.svg",
    )

def import_styles():
    "import styles sheet and determine avatars of users"
    with open("styles/style.css") as css:
        st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

    st.session_state["user_avatar"] = "https://www.svgrepo.com/show/425248/users-avatar.svg"
    st.session_state[
        "assistant_avatar"
    ] = "https://www.svgrepo.com/show/416376/artificial-bot-intelligence.svg"
    st.session_state["sources_avatar"] = "https://www.svgrepo.com/show/365316/database-thin.svg"

    if "finalresponse" not in st.session_state:
        st.session_state["finalresponse"] = ""


def streamed_response(streamer):
    "stream the LLM's response"
    with st.spinner("Thinking..."):
        for token in streamer:
            yield token
            st.session_state["finalresponse"] += token

def initial_placeholder():
    "initial placeholder upon first login"

    if f'model_{st.session_state["db_name"]}' not in server_state:
        st.markdown(
            """<div class="icon_text"><img width=50 src='https://www.svgrepo.com/show/375527/ai-platform.svg'></div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            """<div class="icon_text"<h4>What would you like to know?</h4></div>""",
            unsafe_allow_html=True,
        )


def ui_header():
    "UI header + setting some variables"
    st.title(server_state["app_title"])

    if "db_name" not in st.session_state:
        st.session_state["db_name"] = (
            st.session_state["user_name"].lower().replace(" ", "_")
        )

    # count which session of the user this is
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
        
def export_chat_history():
    "export chat history"
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

def ui_reset():
    "UI reset button"

    st.session_state["reset_memory"] = st.sidebar.button(
        "Reset model's memory",
        help="Reset the model's short-term memory to start with a fresh model",
    )

def delete_chat_history(chat_id,user_id):
    "delete chat history"
    if f'{st.session_state["user_name"]} messages' in server_state:
        del server_state[f'{st.session_state["user_name"]} messages']
    get_session_history(chat_id,user_id).clear()


def ui_display_chat_history():
    pipeline = [
    {
        '$match': {
            'UserId': st.session_state["user_name"]  # Filter documents by UserId
        }
    },
    {
        '$group': {
            '_id': '$SessionId',  # Group by SessionId
            'user_id': {'$first': '$UserId'},  # Example: Get the first UserId in each group
            'count': {'$sum': 1},  # Example: Count documents in each group
            'History': {'$push': '$History'}  # Example: Push History field into an array
        }
    },
    {
        '$sort': {'_id': 1}  # Optional: Sort by SessionId (ascending)
    }
    ]
    allmessages = get_session_history("","").getformatedmessage(pipeline)

    for chat_index, chat in enumerate(allmessages, start=1):
        chat_label = f"Chat {chat_index}"
        with st.sidebar.expander(chat_label):
            parsed_messages = [json.loads(message) for message in chat["History"]]
            for message_index, message in enumerate(parsed_messages, start=1):
                # message_label = f"{message['type'].capitalize()} {message_index}: {message['data']['content'][:50]}..."
                st.write(message['data']['content'])
            if st.button(f"Delete Chat {chat_index}", key=f"delete_{chat_index}"):
                delete_chat_history(chat["_id"], chat["user_id"])
                st.experimental_rerun()
    
def ui_export_chat_end_session():
    "UI elements, export chat end session and help contact"
    if f'{st.session_state["user_name"]} messages' in server_state:
        st.session_state["export_chat_button"] = st.sidebar.download_button(
            label="Export chat history",
            data=export_chat_history(),
            file_name="chat_history.MD",
            help="Export the current session's chat history to a formatted Markdown file. If you don't have a Markdown reader on your computer, post the contents to a [web app](http://editor.md.ipandao.com/en.html)",
        )

    # end session button
    end_session = st.sidebar.button("End session", help="End your session.")
    if end_session:
        clear_models()

        # reset parameters to defaults
        del server_state[f'{st.session_state["user_name"]}_selected_llm']
        
        update_server_state(
            f'{st.session_state["user_name"]} messages', []
        )  # reset user's message history
        st.session_state["password_correct"] = False
        st.session_state["user_name"] = ""
        st.session_state["session_id"] = ""
        st.rerun()
        st.stop()

def populate_chat():
    # Display chat messages from history on app rerun
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


def import_chat():
    "UI element and logic for chat interface"
    if f'model_{st.session_state["db_name"]}' in server_state:
        # Initialize chat history
        if f'{st.session_state["user_name"]} messages' not in server_state:
            update_server_state(f'{st.session_state["user_name"]} messages', [])

        # populate the chat, only if not reinitialized/reprocess, in that case done elsewhere
        if not (
            f'model_{st.session_state["db_name"]}' not in server_state
        ):
            populate_chat()
        
        # reset model's memory
        # if st.session_state["reset_memory"]:
        #     if (
        #         server_state[f'model_{st.session_state["db_name"]}'].chat_engine
        #         is not None
        #     ):
        #         with no_rerun:
        #             server_state[
        #                 f'model_{st.session_state["db_name"]}'
        #             ].chat_engine = None
        #     with st.chat_message(
        #         "assistant", avatar=st.session_state["assistant_avatar"]
        #     ):
        #         st.markdown("Model memory reset!")
        #     update_server_state(
        #         f'{st.session_state["user_name"]} messages',
        #         server_state[f'{st.session_state["user_name"]} messages']
        #         + [{"role": "assistant", "content": "Model memory reset!"}],
        #     )

        # Accept user input
        placeholder_text = (
                "Ask...'The monolith exposes APIs or interfaces. How do we break them down into microservices?'"
            )
        

        if prompt := st.chat_input(placeholder_text):
            # Display user message in chat message container
            prompt_time = f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
            with st.chat_message("user", avatar=st.session_state["user_avatar"]):
                st.markdown(prompt + prompt_time, unsafe_allow_html=True)
            # Add user message to chat history
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
                            )  # take the first person out of the queue
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
                if "session_id" not in st.session_state:
                    generate_session_id()
                response = server_state[
                    f'model_{st.session_state["db_name"]}'
                ].stream({"question": server_state[f'{st.session_state["user_name"]} messages'][
                        -1
                    ]["content"][
                        : -(
                            len(
                                f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
                            )
                        )
                    ]}, {"configurable": {"session_id": st.session_state["session_id"], "user_id": st.session_state["user_name"]}})

                # Display model response against the assistant icon
                with st.chat_message(
                    "assistant", avatar=st.session_state["assistant_avatar"]
                ):
                    st.write_stream(streamed_response(response))
                
                # adding sources
                with st.chat_message(
                    "sources_avatar", avatar=st.session_state["sources_avatar"]
                ):
                    if f'{st.session_state["user_name"]} retriever_output' in st.session_state and "context" in st.session_state[f'{st.session_state["user_name"]} retriever_output'] and "sources" in st.session_state[f'{st.session_state["user_name"]} retriever_output']["context"]:
                        response_time = f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
                        source_string = ""
                        counter = 1
                        for source_path in st.session_state[f'{st.session_state["user_name"]} retriever_output']["context"]["sources"]:
                            # Extracting the file name from the path
                            file_name = source_path.split('/')[-1]
                            # Adding the file name to the source_string with the desired formatting
                            source_string += f"**Source {counter}**: {file_name}\n\n"
                            counter += 1
                        st.markdown(
                            "Sources: " + response_time,
                            unsafe_allow_html=True,
                            help=f"{source_string}",
                        )
                        del st.session_state[f'{st.session_state["user_name"]} retriever_output']                    

                # unlock the model
                update_server_state("in_use", False)
                update_server_state(
                    "exec_queue", server_state["exec_queue"][1:]
                )  # take out of the queue

                # Add assistant response to chat history
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
                # unlock the model
                update_server_state("in_use", False)
                update_server_state(
                    "exec_queue", server_state["exec_queue"][1:]
                )  # take out of the queue
