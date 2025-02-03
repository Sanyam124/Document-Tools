from flask import Flask, render_template, url_for, request, session, redirect
from pymongo import MongoClient
import hashlib, os, pytesseract,io
from PIL import Image

# For PDF OCR
from pdf2image import convert_from_path
import tempfile

# Initialize MongoDB client
client = MongoClient('localhost', 27017)
db = client['mydatabase']
collection = db['logincredentials']

app = Flask(__name__)

# Set a secret key for session encryption (use a random string)
app.secret_key = os.urandom(24)

# Function to hash passwords using MD5 (for demonstration purposes)
def hash_password(password):
    return hashlib.md5(password.encode('utf-8')).hexdigest()

# Function to check if the provided password matches the stored hash
def check_password(stored_password, input_password):
    return stored_password == hashlib.md5(input_password.encode('utf-8')).hexdigest()

@app.route('/')
def home():
    return render_template('SignUp.html')

@app.route('/SignUp', methods=['GET', 'POST'])
def SignUp():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        
        if collection.find_one({'username': username}):
            return render_template('SignUp.html', error='Username already exists')
        
        hashed_password = hash_password(password)
        collection.insert_one({'name': name, 'username': username, 'password': hashed_password})
        return redirect(url_for('login'))
    return render_template('SignUp.html')

@app.route('/index')
def index():
    if 'username' in session:
        return render_template('index.html', name=session['username'])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = collection.find_one({'username': username})
        if user and check_password(user['password'], password):
            session['username'] = username
            return redirect(url_for('index'))
        
        return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Route for Image OCR
@app.route('/ocr', methods=['GET', 'POST'])
def ocr():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    extracted_text = None
    error = None
    
    if request.method == "POST":
        if "image" not in request.files:
            error = "No file part"
            return render_template("ocr.html", error=error)
        
        file = request.files["image"]
        
        if file.filename == "":
            error = "No file selected"
            return render_template("ocr.html", error=error)
        
        try:
            image = Image.open(file.stream)
            extracted_text = pytesseract.image_to_string(image)
        except Exception as e:
            error = f"Error processing image: {e}"

        if extracted_text:
            return render_template("ocr.html", extracted_text=extracted_text)
    
    return render_template("ocr.html", extracted_text=extracted_text, error=error)

# Route for PDF OCR
@app.route('/pdf', methods=['GET', 'POST'])
def pdf():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    extracted_text = None
    error = None

    if request.method == "POST":
        if "pdf" not in request.files:
            error = "No file part"
            return render_template("pdf.html", error=error)
        
        file = request.files["pdf"]
        
        if file.filename == "":
            error = "No file selected"
            return render_template("pdf.html", error=error)
        
        if not file.filename.lower().endswith('.pdf'):
            error = "Uploaded file is not a PDF"
            return render_template("pdf.html", error=error)
        
        try:
            # Save the uploaded PDF to a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            file.save(temp_file.name)
            temp_file.close()

            # Convert PDF pages to images
            pages = convert_from_path(temp_file.name)
            all_text = ""
            for page in pages:
                text = pytesseract.image_to_string(page)
                all_text += text + "\n"
            extracted_text = all_text

            # Remove temporary file
            os.remove(temp_file.name)
        except Exception as e:
            error = f"Error processing PDF: {e}"

    return render_template("pdf.html", extracted_text=extracted_text, error=error)

if __name__ == '__main__':
    app.run(debug=True)
