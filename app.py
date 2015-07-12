#coding=utf-8
from flask import Flask, request, url_for, redirect, render_template, jsonify, json, session, send_from_directory, flash
from functools import wraps
import os, subprocess, random, time
import sqlite3
from werkzeug import secure_filename

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'html', 'md'])

app = Flask(__name__)

# Get rid of the weird bins.fcgi at the end of the URL
def strip_suffix(app, suffix):
    def wrapped_app(environ, start_response):
        if environ['SCRIPT_NAME'].endswith(suffix):
            environ['SCRIPT_NAME'] = environ['SCRIPT_NAME'][:-len(suffix)]
        return app(environ, start_response)
    return wrapped_app

app.wsgi_app = strip_suffix(app.wsgi_app, '/bins.fcgi')



app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config["APPLICATION_ROOT"] = "/bins/"

def authenticate(f):
    ''' Function used to decorate routes that require user login '''
    @wraps(f)
    def new_f(*args, **kwargs):
        if not logged_in():
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return new_f

def logged_in():
    return session.has_key("loggedin") and session["loggedin"] == "yes";

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route("/info")
def info():
    return "<br>".join(dir(app))

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
    bin = secure_filename(bin)

    # Generate list of files
    # files = [("xyz.png", "image"), ("something.md", "text"), ("abc.gif", "image")]
    filenames = [f for f in os.listdir(os.path.join(app.config['UPLOAD_FOLDER'], bin)) if not f.startswith(".")];
    files = []
    for f in filenames:
        if f.endswith(".png") or f.endswith(".gif") or f.endswith(".jpg") or f.endswith(".jpeg") or f.endswith(".webp") or \
           f.endswith(".PNG") or f.endswith(".GIF") or f.endswith(".JPG") or f.endswith(".JPEG") or f.endswith(".WEBP"):
            files.append((f, "#image"))
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
    bin = secure_filename(request.form["bin_name"])
    os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], bin))
    return redirect(url_for("show_bin", bin=bin))

@app.route("/<bin>", methods=["POST"])
@authenticate
def add_to_bin(bin):
    bin = secure_filename(bin)
    if request.files:
        file = request.files['file']
        if file: # and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], bin, filename))
            return redirect(url_for('show_bin',
                                    bin=bin))
    else:
        filename = secure_filename(request.form["name"])
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
    bin = secure_filename(bin)
    file = secure_filename(file)
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], bin), file)

@app.route("/<bin>/view/<file>", methods=["GET"])
def view_file(bin, file):
    bin = secure_filename(bin)
    file = secure_filename(file)
    if file.lower().endswith(".jpg") or file.lower().endswith(".png") or file.lower().endswith(".gif") or file.lower().endswith(".jpeg"):
        return render_template("image.html", bin=bin, file=file)
    else:
        return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], bin), file)

@app.route("/<bin>/delete/<file>", methods=["GET", "POST"])
@authenticate
def delete_file(bin, file):
    file = secure_filename(file)
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

app.secret_key = "the ambulance chasers of venture capital"
app.debug = True
if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True, port=2000)


