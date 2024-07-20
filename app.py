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
if not st.session_state.get('alreadyinitiated', False):
    with st.spinner("Initializing..."):
        ui_display_chat_history()
        initialize_rag_chain()
        st.session_state['alreadyinitiated'] = True
else:
    ui_display_chat_history()
import_chat()
ui_export_chat_end_session()




