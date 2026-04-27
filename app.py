from flask import Flask, render_template, request, redirect, session, send_from_directory
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- CONFIG ----------------
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- MONGODB ----------------
client = MongoClient("mongodb://localhost:27017/")
db = client["securevault"]

users_collection = db["users"]
vaults_collection = db["vaults"]

# ---------------- ROUTES ----------------

@app.route('/')
def home():
    return render_template("welcome.html")

# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        users_collection.insert_one({
            "username": request.form['username'],
            "password": request.form['password']
        })
        return redirect('/login')

    return render_template("signup.html")

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users_collection.find_one({
            "username": request.form['username'],
            "password": request.form['password']
        })

        if user:
            session['user_id'] = str(user['_id'])
            return redirect('/dashboard')
        else:
            return "Invalid Credentials ❌"

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template("dashboard.html")

# ---------------- CREATE VAULT ----------------
@app.route('/create_vault', methods=['GET', 'POST'])
def create_vault():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['vault_name']
        password = request.form['vault_password']
        confirm = request.form['confirm_password']

        if password != confirm:
            return "Passwords do not match ❌"

        vault = vaults_collection.insert_one({
            "user_id": session['user_id'],
            "vault_name": name,
            "vault_password": password
        })

        vault_id = str(vault.inserted_id)

        # create folder like sqlite version
        vault_path = os.path.join(app.config["UPLOAD_FOLDER"], vault_id)
        os.makedirs(vault_path, exist_ok=True)

        return redirect('/open_vault')   # ✅ SAME FLOW

    return render_template("create_vault.html")

# ---------------- OPEN VAULT LIST ----------------
@app.route('/open_vault')
def open_vault():
    if 'user_id' not in session:
        return redirect('/login')

    vaults = vaults_collection.find({
        "user_id": session['user_id']
    })

    return render_template("open_vault.html", vaults=vaults)

# ---------------- ACCESS VAULT ----------------
@app.route('/open_vault/<vault_id>', methods=['GET', 'POST'])
def access_vault(vault_id):
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        password = request.form['vault_password']

        vault = vaults_collection.find_one({
            "_id": ObjectId(vault_id),
            "user_id": session['user_id'],
            "vault_password": password
        })

        if vault:
            vault_path = os.path.join(app.config["UPLOAD_FOLDER"], vault_id)
            os.makedirs(vault_path, exist_ok=True)

            files = os.listdir(vault_path)

            return render_template(
                "vault.html",
                vault=vault,
                files=files,
                vault_id=vault_id
            )
        else:
            return "Wrong Password ❌"

    return render_template("enter_password.html", vault_id=vault_id)

# ---------------- UPLOAD FILE ----------------
@app.route('/upload/<vault_id>', methods=['POST'])
def upload_file(vault_id):
    if 'user_id' not in session:
        return redirect('/login')

    file = request.files['file']

    if file:
        filename = secure_filename(file.filename)

        vault_path = os.path.join(app.config["UPLOAD_FOLDER"], vault_id)
        os.makedirs(vault_path, exist_ok=True)

        file.save(os.path.join(vault_path, filename))

    return redirect(f"/open_vault/{vault_id}")

# ---------------- VIEW FILE ----------------
@app.route('/view/<vault_id>/<filename>')
def view_file(vault_id, filename):
    if 'user_id' not in session:
        return redirect('/login')

    vault_path = os.path.join(app.config["UPLOAD_FOLDER"], vault_id)
    return send_from_directory(vault_path, filename)

# ---------------- DOWNLOAD FILE ----------------
@app.route('/download/<vault_id>/<filename>')
def download_file(vault_id, filename):
    if 'user_id' not in session:
        return redirect('/login')

    vault_path = os.path.join(app.config["UPLOAD_FOLDER"], vault_id)
    return send_from_directory(vault_path, filename, as_attachment=True)

# ---------------- DELETE FILE ----------------
@app.route('/delete/<vault_id>/<filename>')
def delete_file(vault_id, filename):
    if 'user_id' not in session:
        return redirect('/login')

    vault_path = os.path.join(app.config["UPLOAD_FOLDER"], vault_id)
    file_path = os.path.join(vault_path, filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    return redirect(f"/open_vault/{vault_id}")

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)