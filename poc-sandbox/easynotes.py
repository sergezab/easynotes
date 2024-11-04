from dotenv import find_dotenv, load_dotenv
import requests, os, glob
from htmlTemplates import getHtmlTemplate, getHtmlStreamlitTemplate, getSpeakersTemplate
from streamlit_download_button import download_button
import ffmpeg
import re
from pydub import AudioSegment
from huggingface_hub import login, logout
from pyannote.audio import Pipeline
import locale, torch
import whisperx
import json
from datetime import timedelta
import argparse

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

    #with st.expander("segments"):
    #  st.write(*groups)

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
        ## with st.expander("groups"):
        ##    st.write(f"group {gidx}: {start}--{end}")

    return groups

# Whisper's Transcription

locale.getpreferredencoding = lambda: "UTF-8"

# Run whisper on all audio files. Whisper generates the transcription and writes it to a file.
def transcribe_x(groups, output_path, file_mask): 

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    batch_size = 16 # reduce if low on GPU mem
    compute_type = "float16" # change to "int8" if low on GPU mem (may reduce accuracy)

    model = whisperx.load_model("large-v2", "cuda", compute_type=compute_type)

    

    progress_text = "Operation in progress. Please wait."
    percent_complete = 0

    printProgressBar(0, len(groups), prefix = 'Progress:', suffix = 'Complete', length = 50)


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
            print("Exception:" + str(e))
            pass  # or you could use 'continue

        with open(os.path.join(output_path, file_mask + str(i)+'.json'), "w") as outfile:
            json.dump(result, outfile, indent=4)
        
        percent_complete = round((i+1) * 100 / len(groups))
        #print("Complete " + str(i+1) + " out of " + str(len(groups)))

        printProgressBar(i + 1, len(groups), prefix = 'Progress:', suffix = 'Complete', length = 50)
        #st.write("Step i:" + str(i) + "...")
        #st.write("Complete " + str(percent_complete) + "%...")
        
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

def gen_html(groups, source_type, audio_title, audio_file_name, spacermilli, output_path, file_mask, self_hosted):
    speakers = getSpeakersTemplate()
    def_boxclr = 'white'
    def_spkrclr = 'orange'
    
    preS = getHtmlTemplate(audio_title, audio_file_name)
    if not self_hosted:
        preS = getHtmlStreamlitTemplate(audio_title)

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
                        #st.info(file_mask + str(gidx) + '.json: ' + str(w))
                    #end = (shift + w['end']) / 1000.0   #time resolution ot youtube is Second.
                    html.append(f'<a href="#{timeStr(start)}" id="{"{:.1f}".format(round(start*5)/5)}" class="lt" onclick="jumptoTime({int(start)}, this.id, event)">{add_leading_space(w["word"])}</a><!--\n\t\t\t\t-->')
            #html.append('\n')
            html.append('</p>\n')
            html.append(f'</div>\n')

    if self_hosted: 
        html.append(postS)
    else: 
        html.append('\t</body>')

    out_file = ""
    file_prefix = ""
    if not self_hosted:
        file_prefix = "SLT"

    with open(os.path.join(output_path, audio_file_name.split('.')[0]+".txt"), "w", encoding='utf-8') as file:
        s = "".join(txt)
        file.write(s)
        out_file = file.name

    if source_type == 'File':
        with open(os.path.join(output_path, audio_file_name.split('.')[0]+".html"), "w", encoding='utf-8') as file:
            s = "".join(html)
            file.write(s)
            out_file = file.name
            #print(s)
    elif source_type == 'Youtube':
        with open(os.path.join(output_path, audio_file_name.split('.')[0]+".html"), "w", encoding='utf-8') as file:    #TODO: proper html embed tag when video/audio from file
            s = "".join(html)
            file.write(s)
            out_file = file.name
            #print(s)

    return out_file

#Main

def clean_dir(dir, mask):
    # Getting All Files List
    file_mask = os.path.abspath(dir) + '/' + mask
    #st.info("Removing files:" + file_mask)
    fileList = glob.glob(file_mask, recursive=True)

    for item in fileList:
        os.remove(os.path.join(dir, item))


# Print iterations progress
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()

    

def main():

 
    parser = argparse.ArgumentParser(description="Just an example",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-a", "--archive", action="store_true", help="archive mode")
    parser.add_argument("-v", "--verbose", action="store_true", help="increase verbosity")
    parser.add_argument("-r", "--remove", default=False, action="store_true", help="clean output folder")
    parser.add_argument("-B", "--block-size", help="checksum blocksize")
    parser.add_argument("--ignore-existing", action="store_true", help="skip files that exist")
    parser.add_argument("--exclude", help="files to exclude")
    parser.add_argument("src", default="", help="Source location")
    parser.add_argument("dest", default="", help="Destination location")
    args = parser.parse_args()
    config = vars(args)
    print(config)


    # Set up parameters
    input_file = str(args.src)
    dest_path = str(args.dest) 
    clean_output_path = args.remove

    app_path = os.getcwd()   

    audio_title = "Transcription of Conversation"
    source_type = 'File'
    spacermilli = 2000
    tmp_mask = 'splitX_'
    embeded_html_prefix = "SLT"

    if os.path.isfile(input_file):

        #q: remote special characteers except . and spaces from file name
        #file_to_convert = re.sub('[^A-Za-z0-9]+', '', input_file.split('.')[0])

        file_to_convert = os.path.basename(input_file)

        print("file_to_convert: " + file_to_convert) 

        if dest_path == "":
            output_path = os.path.join(os.path.abspath(app_path), "output/" + file_to_convert.split('.')[0]  + "/")
        else:    
            output_path = os.path.abspath(dest_path) + "/" + file_to_convert.split('.')[0]  + "/"
        output_file_name = file_to_convert.split('.')[0] + '.wav'
        output_file = os.path.join(output_path, output_file_name)

        diarization_file = os.path.join(output_path, 'diarization.txt')

        print("app_path: " + app_path)
        print("input-file: " + input_file)
        print("output_path: " + output_path)
        print("output_file: " + output_file)

        
    
        if not os.path.exists(output_path): os.makedirs(output_path)

        #0. === Clean Output Dir === 
        if clean_output_path:
            print("Clean work folder...")
            clean_dir(output_path, tmp_mask+"*.wav");
            clean_dir(output_path, tmp_mask+"*.json");
    

        #1. === Prepare Media === 
        print("Convert media to wav file...")
        ready_wav = load_media(input_file, output_file)
        #ready_wav = os.path.join(os.path.dirname(output_file), 'input_prep.wav')

        #2. === Add spacer at the beggining of the file ===
        print("Add spacer ...")
        ready_wav = append_spacer(output_file, spacermilli)
        print("ready_wav:" + ready_wav)

        #3. === Identify Speakers ===
        print("Diarize with pyannote/speaker-diarization model...")
        diarize(HUGGINGFACEHUB_API_TOKEN, ready_wav, diarization_file)

        #4. === Split Input file based on speakers information ===
        print("Split Input file per speakers...")
        groups = file_split(ready_wav, diarization_file, output_path, tmp_mask)

        #5. === Transcribe each split file ===
        print("Transcribe each split file...")
        transcribe_x(groups, output_path, tmp_mask)
    
        #Freeing up some memory
        # del   DEMO_FILE, pipeline, spacer,  audio, dz

        #6. === Generate output HTML ===
        print("Generate output HTML..." + dest_path)
        html_file = gen_html(groups, source_type, audio_title, file_to_convert, spacermilli, output_path, tmp_mask, True)

        os.rename(html_file, dest_path + os.path.basename(html_file))

           

if __name__ == '__main__':
    main()