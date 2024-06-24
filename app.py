import streamlit as st
from utils.user import setup_metadata, determine_availability, check_password
setup_metadata()
from utils.ui import ui_tab, ui_header,import_styles,import_chat,ui_export_chat_end_session,ui_display_chat_history
from utils.model import initialize_rag_chain


determine_availability()
if not check_password():
    st.stop()

ui_tab()
ui_header()
import_styles()
ui_display_chat_history()
initialize_rag_chain()

import_chat()

ui_export_chat_end_session()




