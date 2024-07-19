# Architecture Refactoring AI Helper (ARAH)
Our tool aims to provide assistance to users in migrating from monolith architectures to microservices by querying a Large Language Model (LLM) which recommends relevant academic approaches for this transition. Briefly, before an LLM responds to your query, the tool first fetches relevant context to the query from the database of academic research papers (using semantic similarity) and responds to your query with this additonal context. This limits the LLM to an extent to not hallucinate and receive valid recommendations using language. This approach is called Retrieval Augmented Generation (RAG). 

## User Interface Information: 
Upon logging in, a chat window will appear. You can use this window to ask questions related to Microservices Architecture and the process of refactoring a monolith to a microservice architecture.

*Note on Context Length:
The Large Language Model (LLM) used in the application has a limited context length. If you encounter an error related to context length exceeding the limit, please click the `End Session` button on the left. Afterward, re-login to start a new chat session.*

## Deployment

### Prerequisites (For development)
- The app is tested with Python 3.9.6
- Install [pip](https://pip.pypa.io/en/stable/installation/)
- [MongoDB](https://www.mongodb.com/docs/manual/installation/) and [Qdrant](https://qdrant.tech/documentation/guides/installation/) to be installed on system 

### How to Setup

- Install requirements using 
   ```sh
   pip install -r requirements. txt
   ```
- Ingest your data
  - Run: `python embeddocs.py "/path/to/pdf/folder" "intfloat/e5-base-v2" "SampleCollection" --api_key "your_api_key_here"`

    This builds pdfs in the given path using intfloat/e5-base-v2 embedding model and Qdrant.
- In order to use a model hosted locally, we will use llama cpp.
  ```sh
  pip install 'llama-cpp-python[server]'
  ```
- Download the LLM (in .gguf format) in the e.g. `models/` directory 
  - (e.g., the Q5 quantization of Llama chat is available [here](https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q5_K_M.gguf?download=true)) 
  - Or using huggingface-cli `pip install -U "huggingface_hub[cli]"`
    ```sh
       huggingface-cli download bartowski/Meta-Llama-3-8B-Instruct-GGUF Meta-Llama-3-8B-Instruct-Q5_K_M.gguf --local-dir ~/models --local-dir-use-symlinks False
    ```
- Run the model on predefined port and IP
  ```sh
  python3 -m llama_cpp.server --model ~/models/Meta-Llama-3-8B-Instruct-Q5_K_M.gguf --port <PORT> --host <Insert IP> --n_ctx 8000 --chat_format chatml
  ```
- Running the Application
    ```sh
     streamlit run app.py
     ```
   Can use `nohup` to run streamlit as a background process
    ```sh
    nohup streamlit run app.py &
    ```


