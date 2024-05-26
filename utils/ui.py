import streamlit as st
from streamlit_server_state import server_state, no_rerun
from utils.user import update_server_state
import pandas as pd
from datetime import datetime
import time

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


def streamed_response(streamer):
    "stream the LLM's response"
    with st.spinner("Thinking..."):
        for token in streamer.response_gen:
            yield token

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


def populate_chat():
    # Display chat messages from history on app rerun
    st.session_state["message_box"] = st.empty()

    if f'{st.session_state["user_name"]} messages' in server_state:
        with st.session_state["message_box"].container():
            for message in server_state[f'{st.session_state["user_name"]} messages']:
                avatar = (
                    st.session_state["user_avatar"]
                    if message["role"] == "user"
                    else st.session_state["assistant_avatar"]
                )
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
                "Query not contextualized"
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
                st.write(server_state[f'model_{st.session_state["db_name"]}'])
                response = server_state[
                    f'model_{st.session_state["db_name"]}'
                ].invoke({"question": server_state[f'{st.session_state["user_name"]} messages'][
                        -1
                    ]["content"][
                        : -(
                            len(
                                f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
                            )
                        )
                    ]}, {"configurable": {"session_id": st.session_state["user_name"]}})

                # Display assistant response in chat message container
                with st.chat_message(
                    "assistant", avatar=st.session_state["assistant_avatar"]
                ):
                    st.markdown(response, unsafe_allow_html=True)
                    # st.write_stream(streamed_response(response["response"]))

                # adding sources
                response_time = f"""<br> <sub><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup></sub>"""
                with st.chat_message(
                    "assistant", avatar=st.session_state["assistant_avatar"]
                ):
                    if len(response.keys()) > 1:  # only do if RAG
                        # markdown help way
                        source_string = ""
                        counter = 1
                        for j in list(
                            pd.Series(list(response.keys()))[
                                pd.Series(list(response.keys())) != "response"
                            ]
                        ):
                            # source_string += f"**Source {counter}**:\n\n \t\t{response[j]}\n\n\n\n"
                            metadata_dict = eval(
                                response[j]
                                .split("| source text:")[0]
                                .replace("metadata: ", "")
                            )
                            metadata_string = ""
                            for key, value in metadata_dict.items():
                                if key != "is_csv":
                                    metadata_string += f"'{key}': '{value}'\n"

                            source_string += f"""# Source {counter}\n ### Metadata:\n ```{metadata_string}```\n ### Text:\n{response[j].split("| source text:")[1]}\n\n"""
                            counter += 1
                    else:
                        source_string = "NA"

                    # adding model information
                    source_string += "\n# Model parameters\n"
                    
                    st.markdown(
                        "Sources: " + response_time,
                        unsafe_allow_html=True,
                        help=f"{source_string}",
                    )

                # unlock the model
                update_server_state("in_use", False)
                update_server_state(
                    "exec_queue", server_state["exec_queue"][1:]
                )  # take out of the queue

                # Add assistant response to chat history
                update_server_state(
                    f'{st.session_state["user_name"]} messages',
                    server_state[f'{st.session_state["user_name"]} messages']
                    + [{"role": "assistant", "content": response["response"].response}],
                )
                update_server_state(
                    f'{st.session_state["user_name"]} messages',
                    server_state[f'{st.session_state["user_name"]} messages']
                    + [
                        {
                            "role": "assistant",
                            "content": f"source_string:{source_string}{response_time}",
                        }
                    ],
                )
            except:
                st.error(
                    "An error was encountered."
                )
                # unlock the model
                update_server_state("in_use", False)
                update_server_state(
                    "exec_queue", server_state["exec_queue"][1:]
                )  # take out of the queue
