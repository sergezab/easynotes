from dotenv import find_dotenv, load_dotenv
import requests, os
import streamlit as st

load_dotenv(find_dotenv())
HUGGINGFACEHUB_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")

# load media
def loadmedia(url)
    text = url

    //ffmpeg -i {repr(video_path)} -vn -acodec pcm_s16le -ar 16000 -ac 1 -y input.wav
    print(text)
    return text

#