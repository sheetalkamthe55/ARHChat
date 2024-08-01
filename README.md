# Architecture Refactoring AI Helper (ARAH)
Our tool aims to provide assistance to users in migrating from monolith architectures to microservices by querying a Large Language Model (LLM) which recommends relevant academic approaches for this transition. Briefly, before an LLM responds to your query, the tool first fetches relevant context to the query from the database of academic research papers (using semantic similarity) and responds to your query with this additonal context. This limits the LLM to an extent to not hallucinate and receive valid recommendations using natural language. This approach is called Retrieval Augmented Generation (RAG). 

## User Interface Information: 
Upon logging in, a chat window will appear. You can use this window to ask questions related to Microservices Architecture and the process of refactoring a monolith to a microservice architecture.

*Note on Context Length:
The Large Language Model (LLM) used in the application has a limited context length. If you encounter an error related to context length exceeding the limit, please click the `End Session` button on the left. Afterward, re-login to start a new chat session.*

## Without Docker

### Prerequisites 
(For development if not using docker)
- The app is tested with Python 3.9.6
- Install [pip](https://pip.pypa.io/en/stable/installation/)
- [MongoDB](https://www.mongodb.com/docs/manual/installation/) and [Qdrant](https://qdrant.tech/documentation/guides/installation/) to be installed on system 

(Install docker to deploy using docker -> GOTO `With Docker` section)

### How to Setup

- Install requirements using 
   ```sh
   pip install -r requirements. txt
   ```
- Ingest your data
  ```sh
  cd scripts
  ```
  Commands with `--` are optional if default parameters are to be changed.
  ```sh
  python3 embeddocs.py "https://localhost:6333/" --collection_name "ARH_Tool" --api_key "yourkey" --chunksize 100 --chunkoverlap 10 --pdf_folder_path "your/path/topdfs"
  ```

  This embeds pdfs in the given path using `intfloat/e5-base-v2` embedding model into the Qdrant database.

- In order to use a model hosted locally(On GPU) (no performance on CPU), we will use llama cpp.
  Also refer to this [feature matrix](https://github.com/ggerganov/llama.cpp/wiki/Feature-matrix) to understand the performance of diff quantized models vs accelerators
  ```sh
  CMAKE_ARGS="-DLLAMA_CUBLAS=on" 
  pip3 install 'llama-cpp-python[server]==0.2.76'
  ```
- Download the LLM (in .gguf format) in e.g. `models/` directory 

    **To download manualy**

      - (e.g., the Q5 quantization of Llama chat is available [here](https://huggingface.co/bartowski/    Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q5_K_M.gguf?download=true))

      - Or using huggingface-cli `pip install -U "huggingface_hub[cli]"`

        ```sh
           huggingface-cli download bartowski/Meta-Llama-3-8B-Instruct-GGUF Meta-Llama-3-8B-Instruct-Q5_K_M.gguf --local-dir ~/models --local-dir-use-symlinks False
        ```

      - Run the model on predefined port and IP

        ```sh
           python3 -m llama_cpp.server --model ~/models/Meta-Llama-3-8B-Instruct-Q5_K_M.gguf --port <PORT> --host <Insert IP>  --n_gpu_layers 33 --n_ctx 8000 --chat_format chatml
        ```

    **Use Make to download model in `models/` directory**

      ```sh
        mkdir models
      ```
      ```sh
        make llama-3-8b
      ```
- Files to update
   **Create Secrets file Configuration Directory**
  Create a `.streamlit` directory which will contain the password for all users in ``api\ui\metadata\user_list.scv` in a `secrets.toml` file.
   ```sh
   mkdir .streamlit
   touch secrets.toml
   nano secrets.toml
   ```
   The `secrets.toml` file will include the following parameter :
   ```sh
    password = "password"
   ```

   **Update the seetings.yaml file**
   Following fields to be updated if llamacpp, mongo, qdrant is hosted other than the localhost 

   mongodb:
      url: "mongodb://localhost:27017"
   qdrant:
      url: "http://localhost:6333"
   llm:
      inference_server_url: "http://localhost:8009/v1"


- Running the Application
    
    ```sh
     cd api/ui
     export PYTHONPATH="your/path/to/project:$PYTHONPATH"
     streamlit run app.py
     ```
   Can use `nohup` to run streamlit as a background process
    ```sh
    cd api/ui
    nohup streamlit run app.py &
    ```

- If you want to host only the API , can follow the steps in the *ARAH Chat API* section

### With Docker
## Prerequisites

Before you begin, ensure you have the following installed:
- Git
- Make utility
- A text editor (e.g., Nano, Vim, or any GUI-based text editor)
- Docker

## Setup Steps

1. **Clone the Repository**

   Start by cloning the project repository to your local machine. 

   ```
    cd arah
   ```

2. **Create a Models Folder**

   After cloning the repository, navigate into the project directory and create a folder named `models` where model files will be stored.
   ```sh
   mkdir models
   ```

3. **Create Streamlit Configuration Directory**

   Create a `.streamlit` directory which will contain the password for all users in ``api\ui\metadata\user_list.scv` in a `secrets.toml` file.
   ```sh
   cd api/ui
   mkdir .streamlit
   touch secrets.toml
   nano secrets.toml
   ```
   The `secrets.toml` file will include the following parameters :
   ```sh
   password = "password"
   ```

4. **Update the seetings.yaml file**
   
   (docker uses the service names of each container to communicate whereas each of the services are accessible from outside the container using localhost)
   
   mongodb:
      url: "mongodb://mongo:27017"
   qdrant:
      url: "http://llama_cpp_server:6333"
   llm:
      inference_server_url: "http://qdrant:8009/v1"
  

4. **Download LLaMA-3-8b**

   The application uses a LLaMA-3-8b model, therefore to download the model
   use `make` command:
   ```sh
   make llama-3-8b
   ```

5. **Compose docker**

   Also following points to be checked in `docker-compose.gpu.yml` or `docker-compose.yml`
   
   For `llama_cpp_server` service, this hosts the LLama 3 model on mentioned port , therefore adjust the port if needed or `8009` is the default port.

   For `arahui` service, correct volumes are to be mapped

   Can remove `arahapi` service from docker compose if we do not need the API for integration.

   To build the images and start the container use the following command:
   ```sh
   make up
   ```
   This will check if NVIDIA GPU exists and accordingly use the docker compose files

6. **Insert documents in Vector Database**
   Script checks for duplicates, by using similarity search and insert only unique chunks.
   Script to insert documnets is in scripts directory. The script accepts several command line arguments, below is description of each:
    * `url`: Required. The URL of the Vector Database.
    * `--reset`: Optional. Use this flag to reset the database.
    * `--pdf_folder_path`: Optional. Path to the folder containing PDFs to be processed. By default it takes the        absolute path as `Content` directory
    * `--model_name`: Optional. The name of the model to use for embedding. Default is 'intfloat/e5-base-v2'.
    * `--collection_name`: Optional. The name of the collection in the Vector Database. Default is 'ARH_Tool'.
    * `--chunksize`: Optional. The chunk size for splitting text. Default is 512.
    * `--chunkoverlap`: Optional. The chunk overlap for splitting text. Default is 100.
    * `--api_key`: Optional. API key for authentication with the Vector Database. Default is None.
   
   Execute following command (for default configuration):

   ```sh
   cd scripts
   ```
   ```sh
    python3 embeddocs.py "http://localhost:6333/" 
   ```
   Example usage:
   ```sh
    python script.py "http://vectordb.example.com" --reset --pdf_folder_path "/path/to/pdfs" --model_name "intfloat/e5-base-v2" --collection_name "ARH_Tool" --chunksize 512 --chunkoverlap 100 --api_key "your_api_key"
   ```

**The app will be available on "http://localhost:8503/"**

### ARAH Chat API

API which supports streaming and non streaming response
*Input schema:*
{
  "message": "string",
  "stream": false,
  "session_id": "string",
  "user_id": "string"
}

Media-type for streaming - `text/event-stream`
Media-type for non streaming - `application/json`

 ```sh
  cd api
 ```
 ```sh
  uvicorn main:app --port 8505
 ```

 The swagger document can be accessed on `http://127.0.0.1:8505/docs`

 ![alt text](/images/SwaggerAPI.png)


 ## Embed the app directly into a an existing webpage

   ```html
      <!DOCTYPE html>
      <html>
      <body>
      
      <iframe src="<streamlit app address>" width="600" height="600">
        <p>Your browser does not support iframes.</p>
      </iframe>

      </body>
      </html>
  ```

  To remove the chrome margins, can add a parameter `?embed=true`.

PS: 
I used Langsmith developer platform to monitor and evaluate the application. It helps significantly track response time of each service call. It can be enabled by creating an API key by logging into langsmith and setting up a project here. 
And then it is enabled by setting environment variables:

```sh
  export LANGCHAIN_TRACING_V2=true
  export LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
  export LANGCHAIN_API_KEY=your-key
  export LANGCHAIN_PROJECT=callback-experiments (or any chosen name)
```





