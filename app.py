#coding=utf-8
import mimetypes
from flask import Flask, url_for, redirect, render_template, jsonify, json, session, send_from_directory, flash, request, send_file, Response
from functools import wraps
import os, os.path, subprocess, random, time, re
import sqlite3
from werkzeug import secure_filename
import urllib

import em2moji

UPLOAD_FOLDER = u'uploads'
ALLOWED_EXTENSIONS = set([u'txt', u'pdf', u'png', u'jpg', u'jpeg', u'gif', u'html', u'md'])

app = Flask(__name__)



def make_response(status=200, content=None):
    """ Construct a response to an upload request.
    Success is indicated by a status of 200 and { "success": true }
    contained in the content.
    Also, content-type is text/plain by default since IE9 and below chokes
    on application/json. For CORS environments and IE9 and below, the
    content-type needs to be text/html.
    """
    return app.response_class(json.dumps(content,
        indent=None if request.is_xhr else 2), mimetype='text/plain')


# Allow partial media requests (for large video files)
@app.after_request
def after_request(response):
    response.headers.add('Accept-Ranges', 'bytes')
    return response

# Get rid of the weird bins.fcgi at the end of the URL
def strip_suffix(app, suffix):
    def wrapped_app(environ, start_response):
        if environ['SCRIPT_NAME'].endswith(suffix):
            environ['SCRIPT_NAME'] = environ['SCRIPT_NAME'][:-len(suffix)]
        return app(environ, start_response)
    return wrapped_app

app.wsgi_app = strip_suffix(app.wsgi_app, '/bins.fcgi')



app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#app.config["APPLICATION_ROOT"] = u"/bins/"

def authenticate(f):
    ''' Function used to decorate routes that require user login '''
    @wraps(f)
    def new_f(*args, **kwargs):
        if not logged_in():
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return new_f

def logged_in():
    #return True
    return session.has_key("loggedin") and session["loggedin"] == "yes";

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route("/info")
def info():
    return "<br>".join(dir(app))

@app.route("/favicon.ico")
def favicon():
    return send_from_directory("static", "favicon.ico")

@app.route("/")
def index():
    bins = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if not f.startswith(".") and os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'], f))];
    return render_template("index.html", bins=bins, logged_in=logged_in())

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        if request.form["password"] == "unicodemoji":
            session['loggedin'] = "yes"
            flash("Logged in!")
            return redirect(url_for("index"))
        else:
            flash("Wrong password!")
            return redirect(url_for("login"))

@app.route("/logout", methods=["GET"])
def logout():
    session['loggedin'] = "no"
    flash("Logged out!")
    return redirect(url_for("login"))
            
@app.route("/<bin>", methods=["GET"])
def show_bin(bin):
    bin = safer_filename(bin)

    # Generate list of files
    # files = [("xyz.png", "image"), ("something.md", "text"), ("abc.gif", "image")]
    filenames = [f for f in os.listdir(os.path.join(app.config['UPLOAD_FOLDER'], bin)) if not f.startswith(".")];
    files = []
    for f in filenames:
        if f.lower().endswith(".png") or f.lower().endswith(".gif") or f.lower().endswith(".jpg") or f.lower().endswith(".jpeg") or f.lower().endswith(".webp"):
            files.append((f, "#image"))
        elif f.lower().endswith(".mp4")or f.lower().endswith(".mov")or f.lower().endswith(".avi") or f.lower().endswith(".mkv") or \
           f.lower().endswith(".m4v") or f.lower().endswith(".flv") or f.lower().endswith(".asf") or f.lower().endswith(".mpg") or \
           f.lower().endswith(".mpeg") or f.lower().endswith(".ogg") or f.lower().endswith(".swf") or f.lower().endswith(".wmv"):
            thumbnail_file = os.path.join(app.config['UPLOAD_FOLDER'], bin, u"thumbnails", u"{}.jpg".format(f))
            thumbnail_url = url_for("get_thumbnail", bin=bin, file=u"{}.jpg".format(f))
            if not os.path.isfile(thumbnail_file):
                thumbnail_url = url_for("static", filename="thumbnail_pending.png")
            files.append((f, "#video", thumbnail_url))

        elif f.lower().endswith("pdf"):
            thumbnail_file = os.path.join(app.config['UPLOAD_FOLDER'], bin, u"thumbnails", u"{}.gif".format(f))
            thumbnail_url = url_for("get_thumbnail", bin=bin, file=u"{}.gif".format(f))
            if not os.path.isfile(thumbnail_file):
                thumbnail_url = url_for("static", filename="thumbnail_pending.png")
            files.append((f, "#video", thumbnail_url))

        elif f.endswith(".txt"):
            with open(os.path.join(app.config['UPLOAD_FOLDER'], bin, f)) as fp:
                files.append((f, fp.read().decode("utf8")))    
        elif f.endswith(".url"):
            with open(os.path.join(app.config['UPLOAD_FOLDER'], bin, f)) as fp:
                files.append((f, fp.read()))            
        elif os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'], bin, f)):
            pass # don't include subdirectories yet
        else:
            files.append((f, None))
            
    random.shuffle(files)
            
    return render_template("bin.html", bin=bin, files=files, logged_in=logged_in())

@app.route("/bins", methods=["POST"])
@authenticate
def create_bin():
    bin = safer_filename(request.form["bin_name"])
    os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], bin))
    os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], bin, "thumbnails"))
    return redirect(url_for("show_bin", bin=bin))

@app.route("/<bin>", methods=["POST"])
@authenticate
def add_to_bin(bin):
    bin = safer_filename(bin)
    if request.files:
        file = request.files['qqfile']
        if file: # and allowed_file(file.filename):
            filename = safer_filename(urllib.unquote(request.form["qqfilename"]))
            if filename == "image.jpg":
                filename = u"{}.jpg".format(em2moji.get_emoji(request.form["qquuid"]))
                print filename

            file_path = os.path.join(app.config['UPLOAD_FOLDER'], bin, filename)
            file.save(file_path)

            # Check if file is a video
            f = filename
            duration = subprocess.check_output(u"ffprobe -i '{0}' -show_format -v quiet | sed -n 's/duration=//p'".format(file_path.replace("'", "'\\''")), shell=True)
            if duration != '' and (f.lower().endswith(".mp4")or f.lower().endswith(".mov")or f.lower().endswith(".avi") or f.lower().endswith(".mkv") or \
                 f.lower().endswith(".m4v") or f.lower().endswith(".flv") or f.lower().endswith(".asf") or f.lower().endswith(".mpg") or \
                 f.lower().endswith(".mpeg") or f.lower().endswith(".ogg") or f.lower().endswith(".swf") or f.lower().endswith(".wmv")):
                # Create a thumbnail using a frame from the middle of the video
                thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], bin, u"thumbnails", u"{}.jpg".format(filename))
                timecode = float(duration) / 2
                timecode = min(10, float(duration))
                thumbnail_command = u"ffmpeg -y -itsoffset -{2} -i '{0}' -vcodec mjpeg -vframes 1 -an -f rawvideo -s 400x300 '{1}'".format(file_path.replace("'", "'\\''"), thumbnail_path.replace("'", "'\\''"), timecode)
                
                subprocess.Popen(thumbnail_command, shell=True)

            # Make animated gif 
            # Requires Ghostscript gs to perform pdf conversion
            elif f.lower().endswith("pdf"):
                thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], bin, u"thumbnails", u"{}.gif".format(filename))
                thumbnail_command = "convert -thumbnail 400 -delay 100 '{0}' '{1}'".format(file_path.replace("'", "'\\''"), thumbnail_path.replace("'", "'\\''"))
                print thumbnail_command
                subprocess.Popen(thumbnail_command, shell=True)
            # return redirect(url_for('show_bin',
            #                         bin=bin))
            return make_response(200, { "success": True })
    else:
        filename = safer_filename(urllib.unquote(request.form["name"]))
        if len(filename) == 0:
            filename = str(int(time.time()))
        if request.form.has_key("text"):
            if not filename.endswith(".txt"):
                filename += u".txt"
            with open(os.path.join(app.config["UPLOAD_FOLDER"], bin, filename), "w") as f:
                f.write(request.form["text"].encode("utf8"))
        
        elif request.form.has_key("url"):
            if not filename.endswith(".url"):
                filename += u".url"
            with open(os.path.join(app.config["UPLOAD_FOLDER"], bin, filename), "w") as f:
                f.write(request.form["url"])                

    return redirect(url_for('show_bin', bin=bin))

@app.route("/<bin>/<file>", methods=["GET"])
def get_file(bin, file):
    bin = safer_filename(bin)
    file = safer_filename(file)
    #return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], bin), file)
    return send_file_partial(os.path.join(app.config['UPLOAD_FOLDER'], bin, file))

@app.route("/<bin>/view/<file>", methods=["GET"])
def view_file(bin, file):
    bin = safer_filename(bin)
    file = safer_filename(file)
    if file.lower().endswith(".jpg") or file.lower().endswith(".png") or file.lower().endswith(".gif") or file.lower().endswith(".jpeg"):
        return render_template("image.html", bin=bin, file=file)
    else:
        return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], bin), file)

@app.route("/<bin>/thumbnails/<file>", methods=["GET"])
def get_thumbnail(bin, file):
    bin = safer_filename(bin)
    file = safer_filename(file)
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], bin, u"thumbnails", file))  

@app.route("/<bin>/delete/<file>", methods=["GET", "POST"])
@authenticate
def delete_file(bin, file):
    file = safer_filename(file)
    try:
        os.unlink(os.path.join(app.config['UPLOAD_FOLDER'], bin, file))
        success = True
    except:
        success = False
    if request.method == "GET":
        return redirect(url_for("show_bin", bin=bin))
    else:
        return success


@app.errorhandler(404)
def notfound(error):
    return redirect(url_for('index'))


# via http://blog.asgaard.co.uk/2012/08/03/http-206-partial-content-for-flask-python 
def send_file_partial(path):
    """ 
        Simple wrapper around send_file which handles HTTP 206 Partial Content
        (byte ranges)
        TODO: handle all send_file args, mirror send_file's error handling
        (if it has any)
    """
    range_header = request.headers.get('Range', None)
    if not range_header: return send_file(path)
    
    size = os.path.getsize(path)    
    byte1, byte2 = 0, None
    
    m = re.search('(\d+)-(\d*)', range_header)
    g = m.groups()
    
    if g[0]: byte1 = int(g[0])
    if g[1]: byte2 = int(g[1])

    length = size - byte1
    if byte2 is not None:
        length = byte2 - byte1
    
    data = None
    with open(path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    rv = Response(data, 
        206,
        mimetype=mimetypes.guess_type(path)[0], 
        direct_passthrough=True)
    rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(byte1, byte1 + length - 1, size))

    return rv   

def safer_filename(filename):
    """ Return a somewhat sanatized filename
        Just replace separators but preserve spaces
        TODO: Also preserve unicode (needs to be supported everywhere else)
    """
    # if isinstance(filename, str) or isinstance(filename, unicode):
    #     from unicodedata import normalize
    #     filename = normalize('NFKD', filename).encode('ascii', 'ignore')
    #     # if not PY2:
    #     #     filename = filename.decode('ascii')

    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, ' ') 
    return filename

app.secret_key = "the ambulance chasers of venture capital"
app.debug = True
if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True, port=2000)


