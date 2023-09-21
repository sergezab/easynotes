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
import whisperx
import json
from datetime import timedelta

load_dotenv(find_dotenv())
HUGGINGFACEHUB_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")

# Preparing the Audio File

# load media
def load_media(input_file, output_file):

    #ffmpeg -i {repr(input_file)} -vn -acodec pcm_s16le -ar 16000 -ac 1 -y input.wav
    ffmpeg.input(input_file).output(output_file, acodec='pcm_s16le', ar=16000, ac=1, af='silenceremove=1:0:-50dB').run(overwrite_output=True)

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

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    diarize_model = whisperx.DiarizationPipeline(use_auth_token=(access_token) or True, device=device)

    audio = whisperx.load_audio(input_file)
    diarize_segments = diarize_model(audio)

    with open(output_file, "w") as text_file:
        text_file.write(diarize_segments.to_string(header=False,index=False, columns=[0, 1, "speaker"]))  

        #q save pandas dataframe as  string and includ   columns 1,2,3
        #text_file.write(diarize_segments.to_string(header=False,index=False, columns=[1,2,3]))

    #print(*list(diarize_segments.itertracks(yield_label = True))[:10], sep="\n")

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

    with st.expander("segments"):
        st.write(*groups, sep='\n')

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
        with st.expander("groups"):
            st.write(f"group {gidx}: {start}--{end}")

    return groups

# Whisper's Transcription

locale.getpreferredencoding = lambda: "UTF-8"

# Run whisper on all audio files. Whisper generates the transcription and writes it to a file.
def transcribe_x(groups, output_path, file_mask): 

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    batch_size = 16 # reduce if low on GPU mem
    compute_type = "float16" # change to "int8" if low on GPU mem (may reduce accuracy)

    model = whisperx.load_model("large-v2", "cuda", compute_type=compute_type)

    import json
    for i in range(len(groups)):
        audiof = os.path.join(output_path,  file_mask + str(i) + '.wav') 
        audio = whisperx.load_audio(audiof)
        #result = json.loads('{ "segments": [{ "text": "", "start": 0,"end": 0, "words": []}], "language": "en"}')
        result = json.loads('{ "text": "","segments": [],"language": "en"}')
        try:
            result = model.transcribe(audio, batch_size=batch_size, language='en')
            # 2. Align whisper output
            model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
            result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

        except Exception as e:
            st.error("Exception:" + str(e))
            pass  # or you could use 'continue

        with open(os.path.join(output_path, file_mask + str(i)+'.json'), "w") as outfile:
            json.dump(result, outfile, indent=4)

    return outfile


# Generating the HTML and/or txt file from the Transcriptions and the Diarization
def timeStr(t):
    return '{0:02d}:{1:02d}:{2:06.3f}'.format(round(t // 3600), round(t % 3600 // 60), t % 60)

def add_leading_space(str):
  if str is None or str == '':
      return str

  if str[0] != ' ':
    return ' ' + str
  else:
    return str

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
                    
                    if 'start' in w:
                        start = (shift + w['start']*1000.0) / 1000.0
                        #print(file_mask + str(gidx) + '.json: ' + str(w) + ' - start:' +str(start))
                    else:
                        start = shift / 1000.0   
                        st.info(file_mask + str(gidx) + '.json: ' + str(w))
                    #end = (shift + w['end']) / 1000.0   #time resolution ot youtube is Second.
                    html.append(f'<a href="#{timeStr(start)}" id="{"{:.1f}".format(round(start*5)/5)}" class="lt" onclick="jumptoTime({int(start)}, this.id)">{add_leading_space(w["word"])}</a><!--\n\t\t\t\t-->')
            #html.append('\n')
            html.append('</p>\n')
            html.append(f'</div>\n')

    html.append(postS)

    with open(os.path.join(output_path, "capspeaker"+file_mask+".txt"), "w", encoding='utf-8') as file:
        s = "".join(txt)
        file.write(s)

    if source_type == 'File':
        with st.expander ("transcript"):
            st.write(s)
        with open(os.path.join(output_path, "capspeaker_audio"+file_mask+".html"), "w", encoding='utf-8') as file:
            s = "".join(html)
            file.write(s)
            #print(s)
    elif source_type == 'Youtube':
        with open(os.path.join(output_path, "capspeaker_youtube"+file_mask+".html"), "w", encoding='utf-8') as file:    #TODO: proper html embed tag when video/audio from file
            s = "".join(html)
            file.write(s)
            #print(s)


#Main

def clean_dir(dir, mask):
    # Getting All Files List
    file_mask = os.path.abspath(dir) + '/' + mask
    st.info("Removing files:" + file_mask)
    fileList = glob.glob(file_mask, recursive=True)

    for item in fileList:
        os.remove(os.path.join(dir, item))
    

def main():

    app_path = os.getcwd()
    st.set_page_config(page_title="audio transcribe", page_icon="@")
    st.header("Turn audio into diadarized transcription")    
    uploaded_file = st.file_uploader("Choose an audio file...", type="mp3")
    audio_title = "Transcription of Conversation"
    source_type = 'File'
    spacermilli = 2000
    tmp_mask = 'splitX_'

    if uploaded_file is not None:
        st.info(uploaded_file)

        #q: remote special characteers except . and spaces from file name
        file_to_convert = re.sub('[^A-Za-z0-9]+', '', uploaded_file.name.split('.')[0])

        output_path = os.path.join(os.path.abspath(app_path), "output/" + file_to_convert.split('.')[0]  + "/")
        output_file = os.path.join(output_path, 'input.wav')
        input_file = os.path.join(output_path, uploaded_file.name) 

        st.info(input_file)

        if not os.path.exists(output_path): os.makedirs(output_path)

        bytes_data = uploaded_file.getvalue ()
        with open (input_file, "wb") as file:
            file.write(bytes_data)

        #0. === Clean Output Dir === 
        clean_dir(output_path, tmp_mask+"*.wav");
        clean_dir(output_path, tmp_mask+"*.json");
    
        #1. === Prepare Media === 
        ready_wav = load_media(input_file, output_file)
        #ready_wav = os.path.join(os.path.dirname(output_file), 'input_prep.wav')

        #2. === Add spacer at the beggining of the file ===
        ready_wav = append_spacer(output_file, spacermilli)
        st.info("ready_wav:" + ready_wav)

        #3. === Identify Speakers ===
        diarization_file = os.path.join(output_path, 'diarization.txt')
        diarize(HUGGINGFACEHUB_API_TOKEN, ready_wav, diarization_file)

        #4. === Split Input file based on speakers information ===
        groups = file_split(ready_wav, diarization_file, output_path, tmp_mask)

        #5. === Transcribe each split file ===
        transcribe_x(groups, output_path, tmp_mask)

        #Freeing up some memory
        # del   DEMO_FILE, pipeline, spacer,  audio, dz

        #6. === Generate output HTML ===
        gen_html(groups, source_type, audio_title, spacermilli, output_path, tmp_mask)
           

if __name__ == '__main__':
    main()