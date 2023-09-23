def getHtmlTemplate(audio_title, audio_file_name):
    preS = """\n<!DOCTYPE html>\n
        <html lang="en">\n\n
        <head>\n\t
            <meta charset="UTF-8">\n\t
            <meta name="viewport" content="whtmlidth=device-width, initial-scale=1.0">\n\t<meta http-equiv="X-UA-Compatible" content="ie=edge">\n\t
            <title>Transcript: {}}</title>\n\t<style>\n\t\t
                body {\n\t\t\tfont-family: sans-serif;\n\t\t\tfont-size: 14px;\n\t\t\tcolor: #111;\n\t\t\tpadding: 0 0 1em 0;\n\t\t\tbackground-color: #efe7dd;\n\t\t}\n\n\t\t
                table {\n\t\t\tborder-spacing: 10px;\n\t\t}\n\n\t\tth {\n\t\t\ttext-align: left;\n\t\t}\n\n\t\t.lt {\n\t\t\tcolor: inherit;\n\t\t\ttext-decoration: inherit;\n\t\t}\n\n\t\t
                .l {\n\t\t\tcolor: #050;\n\t\t}\n\n\t\t
                .s {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t
                .c {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t
                .e {\n\t\t\t/*background-color: white; Changing background color */\n\t\t\tborder-radius: 10px;\n\t\t\t
                /* Making border radius */\n\t\t\twidth: 50%;\n\t\t\t
                /* Making auto-sizable width */\n\t\t\tpadding: 0 0 0 0;\n\t\t\t
                /* Making space around letters */\n\t\t\tfont-size: 14px;\n\t\t\t
                /* Changing font size */\n\t\t\tmargin-bottom: 0;\n\t\t}\n\n\t\t
                .t {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t
                #player-div {\n\t\t\tposition: sticky;\n\t\t\ttop: 20px;\n\t\t\tfloat: right;\n\t\t\twidth: 40%\n\t\t}\n\n\t\t
                #player {\n\t\t\taspect-ratio: 16 / 9;\n\t\t\twidth: 100%;\n\t\t\theight: auto;\n\t\t}\n\n\t\t
                a {\n\t\t\tdisplay: inline;\n\t\t}\n\t
            </style>';
    """
    preS += """\n\t<script>\n\t
            window.onload = function () {\n\t\t\t
                var player = document.getElementById("audio_player");\n\t\t\t
                var player;\n\t\t\tvar lastword = null;\n\n\t\t\t
                // So we can compare against new updates.\n\t\t\tvar lastTimeUpdate = "-1";\n\n\t\t\t
                setInterval(function () {\n\t\t\t\t
                // currentTime is checked very frequently (1 millisecond),\n\t\t\t\t
                // but we only care about whole second changes.\n\t\t\t\t
                var ts = (player.currentTime).toFixed(1).toString();\n\t\t\t\t
                ts = (Math.round((player.currentTime) * 5) / 5).toFixed(1);\n\t\t\t\t
                ts = ts.toString();\n\t\t\t\tconsole.log(ts);\n\t\t\t\t
                if (ts !== lastTimeUpdate) {\n\t\t\t\t\t
                lastTimeUpdate = ts;\n\n\t\t\t\t\t
                // Its now up to you to format the time.\n\t\t\t\t\t
                word = document.getElementById(ts)\n\t\t\t\t\t
                if (word) {\n\t\t\t\t\t\tif (lastword) {\n\t\t\t\t\t\t\t
                lastword.style.fontWeight = "normal";\n\t\t\t\t\t\t}\n\t\t\t\t\t\t
                lastword = word;\n\t\t\t\t\t\t
                //word.style.textDecoration = "underline";\n\t\t\t\t\t\t
                word.style.fontWeight = "bold";\n\n\t\t\t\t\t\t
                let toggle = document.getElementById("autoscroll");\n\t\t\t\t\t\t
                if (toggle.checked) {\n\t\t\t\t\t\t\t
                let position = word.offsetTop - 10;\n\t\t\t\t\t\t\t
                window.scrollTo({\n\t\t\t\t\t\t\t\ttop: position,\n\t\t\t\t\t\t\t\tbehavior: "smooth"\n\t\t\t\t\t\t\t});\n\t\t\t\t\t\t
                }\n\t\t\t\t\t
                }\n\t\t\t\t
                }\n\t\t\t
                }, 0.1);\n\t\t
            }\n\n\t\t
            function jumptoTime(timepoint, id, event) {\n\t\t\t
                var player = document.getElementById("audio_player");\n\t\t\t
                history.pushState(null, null, "#" + id);\n\t\t\t
                player.pause();\n\t\t\t
                player.currentTime = timepoint;\n\t\t\t
                player.play();\n\t\t
                }\n\t\t
        </script>\n\t
        </head>';
    """
    preS += '\n\n<body>\n\t<h2>' + audio_title + '</h2>\n\t' + """
        <i>Click on a part of the transcription, to jump to its portion of audio, and get an anchor to it in the address\n\t\tbar<br><br></i>\n\t
        <div id="player-div">\n\t\t
            <div id="player">\n\t\t\t
                <audio controls="controls" id="audio_player">\n\t\t\t\
                    """ +'<source src="' + audio_file_name + '" />\n\t\t\t</audio>\n\t\t' + """
                </div>\n\t\t<div>
                <label for="autoscroll">auto-scroll: </label>\n\t\t\t
                <input type="checkbox" id="autoscroll" checked>\n\t\t
            </div>\n\t
        </div>\n';
    """
    return preS

def getHtmlStreamlitTemplate(audio_title):
    preS = """\n
    <head>\n\t<meta charset="UTF-8">\n\t<meta name="viewport" content="whtmlidth=device-width, initial-scale=1.0">\n\t
        <meta http-equiv="X-UA-Compatible" content="ie=edge">\n\t
        <title>Transcript: {}}</title>\n\t
        <style>\n\t\t
            body {\n\t\t\t
                font-family: sans-serif;\n\t\t\tfont-size: 14px;\n\t\t\tcolor: #111;\n\t\t\tpadding: 0 0 1em 0;\n\t\t\tbackground-color: #efe7dd;\n\t\t
            }\n\n\t\t
            table {\n\t\t\tborder-spacing: 10px;\n\t\t}\n\n\t\t
            th {\n\t\t\ttext-align: left;\n\t\t}\n\n\t\t
            .lt {\n\t\t\tcolor: inherit;\n\t\t\ttext-decoration: inherit;\n\t\t}\n\n\t\t
            .l {\n\t\t\tcolor: #050;\n\t\t}\n\n\t\t
            .s {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t
            .c {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t
            .e {\n\t\t\t
                background-color: white; /* Changing background color */\n\t\t\t
                border-radius: 10px;\n\t\t\t/* Making border radius */\n\t\t\t
                width: 80%;\n\t\t\t/* Making auto-sizable width */\n\t\t\t
                padding: 0 0 0 0;\n\t\t\t/* Making space around letters */\n\t\t\t
                font-size: 14px;\n\t\t\t/* Changing font size */\n\t\t\t
                margin-bottom: 0;\n\t\t
            }\n\n\t\t
            .t {\n\t\t\tdisplay: inline-block;\n\t\t}\n\n\t\t
            .as {\n\t\t\tmargin-left: 30%;\n\t\t}\n\n\t\t
            #player-div {\n\t\t\tposition: sticky;\n\t\t\ttop: 20px;\n\t\t\tfloat: right;\n\t\t\twidth: 20%\n\t\t}\n\n\t\t
            #player {\n\t\t\taspect-ratio: 16 / 9;\n\t\t\twidth: 100%;\n\t\t\theight: auto;\n\t\t}\n\n\t\ta {\n\t\t\tdisplay: inline;\n\t\t}\n\t
        </style>';
    """
    preS += """\n\t
        <script>\n\t
            window.onload = function () {\n\t\t\t
                var player = parent.document.getElementById("audio");\n\t\t\t
                var player;\n\t\t\t
                var lastword = null;\n\n\t\t\t
                // So we can compare against new updates.\n\t\t\t
                var lastTimeUpdate = "-1";\n\n\t\t\t
                setInterval(function () {\n\t\t\t\t
                    // currentTime is checked very frequently (1 millisecond),\n\t\t\t\t
                    // but we only care about whole second changes.\n\t\t\t\t
                    var ts = (player.currentTime).toFixed(1).toString();\n\t\t\t\t
                    ts = (Math.round((player.currentTime) * 5) / 5).toFixed(1);\n\t\t\t\t
                    ts = ts.toString();\n\t\t\t\tconsole.log(ts);\n\t\t\t\t
                    if (ts !== lastTimeUpdate) {\n\t\t\t\t\t
                        lastTimeUpdate = ts;\n\n\t\t\t\t\t
                        // Its now up to you to format the time.\n\t\t\t\t\t
                        word = document.getElementById(ts)\n\t\t\t\t\t
                        if (word) {\n\t\t\t\t\t\t
                            if (lastword) {\n\t\t\t\t\t\t\t
                                lastword.style.fontWeight = "normal";\n\t\t\t\t\t\t
                            }\n\t\t\t\t\t\t
                        lastword = word;\n\t\t\t\t\t\t
                        //word.style.textDecoration = "underline";\n\t\t\t\t\t\t
                        word.style.fontWeight = "bold";\n\n\t\t\t\t\t\t
                        let toggle = document.getElementById("autoscroll");\n\t\t\t\t\t\t
                        if (toggle.checked) {\n\t\t\t\t\t\t\t
                        let position = word.offsetTop - 10;\n\t\t\t\t\t\t\t
                        window.scrollTo({\n\t\t\t\t\t\t\t\t
                            top: position,\n\t\t\t\t\t\t\t\t
                            behavior: "smooth"\n\t\t\t\t\t\t\t
                        });\n\t\t\t\t\t\t
                    }\n\t\t\t\t\t
                }\n\t\t\t\t
            }\n\t\t\t
            }, 0.1);\n\t\t
            }\n\n\t\t
            function jumptoTime(timepoint, id, event) {\n\t\t\t
                var player = parent.document.getElementById("audio");\n\t\t\t
                //history.pushState(null, null, "#" + id);\n\t\t\t
                player.pause();\n\t\t\t
                player.currentTime = timepoint;\n\t\t\t
                player.play();\n\t\t
                event.stopPropagation();\n\t\t
                event.preventDefault();\n\t\t
            }\n\t\t
        </script>\n\t</head>';
    """
    preS += '\n\n<body>\n\t<h2>' + audio_title + """</h2>\n\t
        <i>Click on a part of the transcription, to jump to its portion of audio, and get an anchor to it in the address\n\t\tbar<br><br></i>\n\t
        <div id="player-div">\n\t\t
            <div id="player" >\n\t</div>\n\t\t
            <div class="as">
                <label for="autoscroll">auto-scroll: </label>\n\t\t\t
                <input type="checkbox" id="autoscroll" checked>\n\t\t
            </div>\n\t
        </div>\n
    """;

    return preS


def getSpeakersTemplate():
    speakers = {'SPEAKER_00':('Agent 1', '#e1ffc7', 'darkgreen'), 'SPEAKER_01':('Agent 2', 'white', 'darkorange'), 'SPEAKER_02':('Agent 3', 'PapayaWhip', 'darkred'), 'SPEAKER_03':('Agent 4', 'LightCyan', 'DarkSlateBlue'), 'SPEAKER_04':('Agent 5', 'PaleGreen', 'DarkSeaGreen'), 'SPEAKER_05':('Agent 6', 'Cornsilk', 'Gold'), 'SPEAKER_06':('Agent 7', 'Lavender', 'RebeccaPurple') }

    return speakers

#const doc = window.parent.document;

def getHtmlTest():
    html = """
     <script>
        const doc = window.parent.document.querySelectorAll('iframe')[0].contentWindow.document;
        console.log(doc)
        const inputs = doc.querySelectorAll('a');
        console.log("custom script loaded")
        console.log(inputs)
        inputs.forEach(input => {
            input.addEventListener('click', function(event) {
                event.stopPropagation();
                event.preventDefault();
                console.log("lost focus")
            });
        });
    </script>
        <p><a href='#' id='Link1' class='myobject'>First link</a></p>
        <p><a href='#' id='Link2' class='myobject'>Second link</a></p>
        <a href='#' id='Image1' ><img width='20%' src='https://images.unsplash.com/photo-1565130838609-c3a86655db61?w=200'></a>
        <a href='#' id='Image2' ><img width='20%' src='https://images.unsplash.com/photo-1565372195458-9de0b320ef04?w=200'></a>
    """
    return html