import streamlit as st
from streamlit_server_state import server_state, server_state_lock, no_rerun
import pandas as pd
from datetime import datetime
import hmac
import gc


def update_server_state(key, value):
    "update the server state variable"
    with no_rerun:
        with server_state_lock[key]:
            server_state[key] = value

def setup_metadata():
    try:
        if "db_info" not in st.session_state:
            st.session_state["db_info"] = pd.read_csv("metadata/settings.csv")

        if "mongodbURI" not in server_state:
            update_server_state(
                "mongodbURI",
                st.secrets["mongodbURI"]
            )

        if "mongo_db_name" not in server_state:
            update_server_state(
                "mongo_db_name",
                st.session_state["db_info"]
                .loc[lambda x: x.field == "mongo_db_name", "value"]
                .values[0],
            )

        if "app_title" not in server_state:
            update_server_state(
                "app_title",
                st.session_state["db_info"]
                .loc[lambda x: x.field == "app_title", "value"]
                .values[0],
            )

        if "inference_server_url" not in server_state:
            update_server_state(
                "inference_server_url",
                st.secrets["inference_server_url"]
            )
        
        if "qdrant_server_url" not in server_state:
            update_server_state(
                "qdrant_server_url",
                st.secrets["qdrant_server_url"]
            )

        if "qdrant_API_key" not in server_state:
            update_server_state(
                "qdrant_API_key",
                st.secrets["qdrant_API_key"]
            )

        if "vector_collectionname" not in server_state:
            update_server_state(
                "vector_collectionname",
                st.session_state["db_info"]
                .loc[lambda x: x.field == "vector_collectionname", "value"]
                .values[0],
            )

        if "embeddingmodelname" not in server_state:
            update_server_state(
                "embeddingmodelname",
                st.session_state["db_info"]
                .loc[lambda x: x.field == "embeddingmodelname", "value"]
                .values[0],
            )

        if "history_collectionname" not in server_state:
            update_server_state(
                "history_collectionname",
                st.session_state["db_info"]
                .loc[lambda x: x.field == "history_collectionname", "value"]
                .values[0],
            )
    except Exception as e:
        st.write(f"failed to get the metadata, please check the metadata file: {e}")

def clear_models():
    if f'model_{st.session_state["db_name"]}' in server_state:
        try:
            server_state[f'model_{st.session_state["db_name"]}'].close_connection()
        except:
            pass
        del server_state[f'model_{st.session_state["db_name"]}']
        gc.collect()

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

    # restart user if logging in again
    if "user_name" in st.session_state:
        if (
            f'{st.session_state["user_name"]}_count' in server_state
            and "count" in st.session_state
        ):
            if (
                server_state[f'{st.session_state["user_name"]}_count']
                != st.session_state["count"]
            ):
                # st.session_state["available"] = False
                st.error("You have logged in on another tab.")
                clear_models()
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
