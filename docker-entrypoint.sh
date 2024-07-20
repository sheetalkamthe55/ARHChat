#!/bin/sh

set -eu

# download model if specified as argument and exit
if [ "$#" -eq 1 ]; then
    if [ "$1" = "llama-2-13b" ]; then
        MODEL_URL="https://huggingface.co/TheBloke/Llama-2-13B-chat-GGUF/resolve/main/llama-2-13b-chat.Q5_K_M.gguf"
        MODEL_SHA256="ef36e090240040f97325758c1ad8e23f3801466a8eece3a9eac2d22d942f548a"
    elif [ "$1" = "mistral-7b" ]; then
        MODEL_URL="https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q5_K_M.gguf"
        MODEL_SHA256="b85cdd596ddd76f3194047b9108a73c74d77ba04bef49255a50fc0cfbda83d32"
    elif [ "$1" = "llama-3-8b" ]; then
        MODEL_URL="https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q5_K_M.gguf"
        MODEL_SHA256="16d824ee771e0e33b762bb3dc3232b972ac8dce4d2d449128fca5081962a1a9e"
    else
        echo "$0 [llama-2-13b|mistral-7b|llama-3-8b]"
        exit 1
    fi
    MODEL_NAME=$(basename "$MODEL_URL")
    curl -LO "$MODEL_URL"
    # echo "$MODEL_SHA256  $MODEL_NAME" | sha256sum -c -
    # echo "$MODEL_SHA256 $MODEL_NAME" | shasum -a 256 -c -
    printf "%s  %s" "$MODEL_SHA256" "$MODEL_NAME" | shasum -a 256 -c -
    exit 0
fi

# set default environment variables if not set
if [ -z ${LLAMA_HOST+x} ]; then
    export LLAMA_HOST="0.0.0.0"
fi
if [ -z ${LLAMA_MODEL+x} ]; then
    export LLAMA_MODEL="/models/llama-2-13b-chat.Q5_K_M.gguf"
fi

# convert LLAMA_ environment variables to llama-server arguments
LLAMA_ARGS=$(env | grep LLAMA_ | awk '{
    # for each environment variable
    for (n = 1; n <= NF; n++) {
        # replace LLAMA_ prefix with --
        sub("^LLAMA_", "--", $n)
        # find first = and split into argument name and value
        eq = index($n, "=")
        s1 = tolower(substr($n, 1, eq - 1))
        s2 = substr($n, eq + 1)
        # replace _ with - in argument name
        gsub("_", "-", s1)
        # print argument name and value
        print s1 " " s2
    }
}')

set -x
llama-server $LLAMA_ARGS