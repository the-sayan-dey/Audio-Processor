from flask import Flask, render_template, request, redirect, send_from_directory, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename 
from sqlalchemy import or_
from flask import send_file
from sqlalchemy import or_, ForeignKey
import os
import noisereduce as nr
import soundfile as sf
import numpy as np
import audioread
from pydub import AudioSegment


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1234@localhost/minor-project'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'media')







db = SQLAlchemy(app)

class UserData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    age = db.Column(db.Integer)
    location = db.Column(db.String(100))
    education = db.Column(db.String(100))
    gender = db.Column(db.String(10))
    audio_file = db.Column(db.String(255))



class FilteredData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_data_id = db.Column(db.Integer, ForeignKey('user_data.id'))
    audio_file = db.Column(db.String(255))


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/play/<filename>')
def play_audio(filename):
    # Assuming the audio files are stored in the UPLOAD_FOLDER
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(audio_path, as_attachment=False)

@app.route('/download/<filename>')
def download_file(filename):
    # Assuming the audio files are stored in the UPLOAD_FOLDER
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/tools')
def tools():
    # Get filter parameters from the request
    age_from = request.args.get('age_from')
    age_to = request.args.get('age_to')
    location = request.args.get('location')
    education = request.args.get('education')
    gender = request.args.get('gender')

    # Construct the base query
    query = UserData.query

    # Apply filters based on provided fields
    if age_from:
        query = query.filter(UserData.age >= age_from)
    if age_to:
        query = query.filter(UserData.age <= age_to)
    if location is not None:
        query = query.filter(UserData.location.ilike(f'%{location}%'))
    if education is not None:
        query = query.filter(UserData.education.ilike(f'%{education}%'))
    if gender:
        query = query.filter(UserData.gender == gender)

    # Execute the query
    filtered_data = query.all()

    print(filtered_data)

    return render_template('tools.html', data=filtered_data)


@app.route('/submit', methods=['POST'])
def submit():
    age = request.form['age']
    location = request.form['location']
    education = request.form['education']
    gender = request.form['gender']

    audio_file = request.files['audio_file']
    
    # Constructing a unique filename by concatenating user ID with the original filename
    user_id = UserData.query.count() + 1  # Get the next available user ID
    filename = f"user_{user_id}_{secure_filename(audio_file.filename)}"  # Appending user ID to the filename
    audio_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    audio_file.save(audio_file_path)  # Save the audio file to the media folder

    new_user_data = UserData(age=age, location=location, education=education, gender=gender, audio_file=filename)
    db.session.add(new_user_data)
    db.session.commit()

    return redirect(url_for('success'))




@app.route('/denoise/<filename>')
def denoise_audio(filename):
    # Construct absolute file path
    audio_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    print("File path:", audio_path)  # Debug statement

    # Check if file exists
    if not os.path.exists(audio_path):
        print("File not found:", audio_path)  # Debug statement
        return "File not found"

    # Read the audio file using Pydub
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    audio = AudioSegment.from_file(audio_path)

    # Convert to numpy array
    data = np.array(audio.get_array_of_samples())
    sample_rate = audio.frame_rate

    # Reduce noise
    reduced_noise = nr.reduce_noise(audio_clip=data, noise_clip=data)

    # Create denoised audio file path
    denoised_audio_path = os.path.join(app.config['FILTERED_AUDIO_FOLDER'], f"denoised_{filename}")

    # Write denoised audio to file
    audio = AudioSegment(
        reduced_noise.tobytes(),
        frame_rate=sample_rate,
        sample_width=reduced_noise.dtype.itemsize,
        channels=1  # Assuming mono audio
    )
    audio.export(denoised_audio_path, format="wav")

    return redirect(url_for('tools'))
def denoise_audio_file(audio_path):
    # Read the audio file
    data, sr = sf.read(audio_path)

    # Reduce noise
    reduced_noise = nr.reduce_noise(audio_clip=data, noise_clip=data)

    # Create denoised audio file path
    denoised_audio_path = audio_path.replace(app.config['UPLOAD_FOLDER'], app.config['FILTERED_AUDIO_FOLDER'])
    denoised_audio_path = denoised_audio_path.replace('.wav', '_denoised.wav')

    # Write denoised audio to file
    sf.write(denoised_audio_path, reduced_noise, sr)

    return denoised_audio_path




@app.route('/success')
def success():
    return 'Data submitted successfully!'

if __name__ == '__main__':
    app.run(debug=True)
