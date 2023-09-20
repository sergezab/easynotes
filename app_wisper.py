from dotenv import find_dotenv, load_dotenv
import requests, os, glob
from htmlTemplates import getSpeakersTemplate, getHtmlTemplate
import streamlit as st
import ffmpeg
import re
from pydub import AudioSegment
from huggingface_hub import login, logout
from pyannote.audio import Pipeline
import locale, torch
import whisper
import json
from datetime import timedelta

load_dotenv(find_dotenv())
HUGGINGFACEHUB_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")

# Preparing the Audio File

# load media
def load_media(input_file, output_file):

    #ffmpeg -i {repr(input_file)} -vn -acodec pcm_s16le -ar 16000 -ac 1 -y input.wav
    ffmpeg.input(input_file).output(output_file, acodec='pcm_s16le', ar=16000, ac=1).run(overwrite_output=True)

    print(output_file)
    return output_file

#Prepending a spacer
#--> pyannote.audio seems to miss the first 0.5 seconds of the audio, and, therefore, we prepend a spcacer.
def append_spacer(url, spacermilli):
    spacer = AudioSegment.silent(duration=spacermilli)
    audio = AudioSegment.from_wav(url)
    audio = spacer.append(audio, crossfade=0)
    output_file = os.path.join(os.path.dirname(url), 'input_prep.wav') 
    audio.export(output_file, format='wav')

    return output_file

#Pyannote's Diarization

def diarize(access_token, input_file, output_file):
    
    if (access_token):
        login(access_token)
    else:
        login()

    pipeline = Pipeline.from_pretrained('pyannote/speaker-diarization', use_auth_token= (access_token) or True )
    DEMO_FILE = {'uri': 'blabla', 'audio': input_file}
    dz = pipeline(DEMO_FILE)  

    with open(output_file, "w") as text_file:
        text_file.write(str(dz))  

    print(*list(dz.itertracks(yield_label = True))[:10], sep="\n")

    return 


#Preparing audio files according to the diarization¶
def millisec(timeStr):
  spl = timeStr.split(":")
  s = (int)((int(spl[0]) * 60 * 60 + int(spl[1]) * 60 + float(spl[2]) )* 1000)
  return s


def file_split(input_file, diarization_file, output_path, file_mask):

    # Grouping the diarization segments according to the speaker.
    dzs = open(diarization_file).read().splitlines()

    groups = []
    g = []
    lastend = 0

    for d in dzs:
        if g and (g[0].split()[-1] != d.split()[-1]):      #same speaker
            groups.append(g)
            g = []

        g.append(d)

        end = re.findall('[0-9]+:[0-9]+:[0-9]+\.[0-9]+', string=d)[1]
        end = millisec(end)
        if (lastend > end):       #segment engulfed by a previous segment
            groups.append(g)
            g = []
        else:
            lastend = end

    if g:
        groups.append(g)

    #print(*groups, sep='\n')

    # Save the audio part corresponding to each diarization group.
    audio = AudioSegment.from_wav(input_file)
    gidx = -1

    for g in groups:
        start = re.findall('[0-9]+:[0-9]+:[0-9]+\.[0-9]+', string=g[0])[0]
        end = re.findall('[0-9]+:[0-9]+:[0-9]+\.[0-9]+', string=g[-1])[1]
        start = millisec(start) #- spacermilli
        end = millisec(end)  #- spacermilli
        gidx += 1
        audio[start:end].export(output_path + file_mask + str(gidx) + '.wav', format='wav')
        print(f"group {gidx}: {start}--{end}")

    return groups

# Whisper's Transcription

locale.getpreferredencoding = lambda: "UTF-8"

# Run whisper on all audio files. Whisper generates the transcription and writes it to a file.
def transcribe(groups, output_path, file_mask): 

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = whisper.load_model('large', device = device)

    import json
    for i in range(len(groups)):
        audiof = os.path.join(output_path, file_mask + str(i) + '.wav') 
        result = model.transcribe(audio=audiof, language='en', word_timestamps=True)#, initial_prompt=result.get('text', ""))
        with open(os.path.join(output_path, file_mask + str(i)+'.json'), "w") as outfile:
            json.dump(result, outfile, indent=4)

    return outfile

# Generating the HTML and/or txt file from the Transcriptions and the Diarization
def timeStr(t):
    return '{0:02d}:{1:02d}:{2:06.3f}'.format(round(t // 3600), round(t % 3600 // 60), t % 60)

def gen_html(groups, source_type, audio_title, spacermilli, output_path, file_mask):
    speakers = getSpeakersTemplate()
    def_boxclr = 'white'
    def_spkrclr = 'orange'
    preS = getHtmlTemplate(audio_title)
    postS = '\t</body>\n</html>'
    html = list(preS)
    txt = list("")
    gidx = -1

    for g in groups:
        shift = re.findall('[0-9]+:[0-9]+:[0-9]+\.[0-9]+', string=g[0])[0]
        shift = millisec(shift) - spacermilli #the start time in the original video
        shift=max(shift, 0)

        gidx += 1

        captions = json.load(open(os.path.join(output_path, file_mask + str(gidx) + '.json')))['segments']

        if captions:
            speaker = g[0].split()[-1]
            boxclr = def_boxclr
            spkrclr = def_spkrclr
            if speaker in speakers:
                speaker, boxclr, spkrclr = speakers[speaker]

            html.append(f'<div class="e" style="background-color: {boxclr}">\n');
            html.append('<p  style="margin:0;padding: 5px 10px 10px 10px;word-wrap:normal;white-space:normal;">\n')
            html.append(f'<span style="color:{spkrclr};font-weight: bold;">{speaker}</span><br>\n\t\t\t\t')

            for c in captions:
                start = shift + c['start'] * 1000.0
                start = start / 1000.0   #time resolution ot youtube is Second.
                end = (shift + c['end'] * 1000.0) / 1000.0
                txt.append(f'[{timeStr(start)} --> {timeStr(end)}] [{speaker}] {c["text"]}\n')

                for i, w in enumerate(c['words']):
                    if w == "":
                        continue
                    start = (shift + w['start']*1000.0) / 1000.0
                    #end = (shift + w['end']) / 1000.0   #time resolution ot youtube is Second.
                    html.append(f'<a href="#{timeStr(start)}" id="{"{:.1f}".format(round(start*5)/5)}" class="lt" onclick="jumptoTime({int(start)}, this.id)">{w["word"]}</a><!--\n\t\t\t\t-->')
            #html.append('\n')
            html.append('</p>\n')
            html.append(f'</div>\n')

    html.append(postS)

    with open(os.path.join(output_path, "capspeaker"+file_mask+".txt"), "w", encoding='utf-8') as file:
        s = "".join(txt)
        file.write(s)

    if source_type == 'File':
        print(s)
        with open(os.path.join(output_path, "capspeaker_audio"+file_mask+".html"), "w", encoding='utf-8') as file:
            s = "".join(html)
            file.write(s)
            print(s)
    elif source_type == 'Youtube':
        with open(os.path.join(output_path, "capspeaker_youtube"+file_mask+".html"), "w", encoding='utf-8') as file:    #TODO: proper html embed tag when video/audio from file
            s = "".join(html)
            file.write(s)
            print(s)


#Main

def clean_dir(dir, mask):
    # Getting All Files List
    file_mask = os.path.abspath(dir) + '/' + mask
    print("Removing files:" + file_mask)
    fileList = glob.glob(file_mask, recursive=True)

    for item in fileList:
        os.remove(os.path.join(dir, item))
    

def main():
    file_to_convert = "AppRecording-20230915-1004.mp3"
    app_path = os.getcwd()

    output_path = os.path.join(os.path.abspath(app_path), "output/" + file_to_convert.split('.')[0]  + "/")
    input_path = os.path.join(os.path.abspath(app_path), "input/")
    input_file = os.path.join(input_path, file_to_convert)
    output_file = os.path.join(output_path, 'input.wav')
    diarization_file = os.path.join(output_path, 'diarization.txt')
    audio_title = "Transcription of Conversation"
    source_type = 'File'
    spacermilli = 2000
    tmp_mask = 'split_'


    print("app_path: " + app_path)
    print("input_path: " + input_path)
    print("input-file: " + input_file)
    print("output_path: " + output_path)
    print("output_file: " + output_file)

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    #0. === Clean Output Dir === 
    clean_dir(output_path, tmp_mask+"*.wav");
    #clean_dir(output_path, tmp_mask+"*.json");

    #1. === Prepare Media === 
    #load_media(input_file, output_file)
    ready_wav = os.path.join(os.path.dirname(output_file), 'input_prep.wav')
   
    #2. === Add spacer at the beggining of the file ===
    #ready_wav = append_spacer(output_file, spacermilli)
    print("ready_wav:" + ready_wav)

    #3. === Identify Speakers ===
    #diarize(HUGGINGFACEHUB_API_TOKEN, ready_wav, diarization_file)

    #4. === Split Input file based on speakers information ===
    groups = file_split(ready_wav, diarization_file, output_path, tmp_mask)

    #5. === Transcribe each split file ===
    #transcribe(groups, output_path, tmp_mask)

    #Freeing up some memory
    # del   DEMO_FILE, pipeline, spacer,  audio, dz

    #6. === Generate output HTML ===
    gen_html(groups, source_type, audio_title, spacermilli, output_path, tmp_mask)

if __name__ == '__main__':
    main()