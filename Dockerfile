FROM python

WORKDIR /app

# install python
RUN apt-get update
RUN apt-get install -y curl git python3-pip python3-dev python-is-python3
RUN rm -rf /var/lib/apt/lists/*

# clone streamlit app
RUN git clone https://github.com/sheetalkamthe55/ARHChat.git
RUN curl -s https://raw.githubusercontent.com/sheetalkamthe55/ARHChat/main/requirements.txt?token=GHSAT0AAAAAACTVPEVXMSJSPWCKUYTKAIBCZTZUUDQ | xargs pip install