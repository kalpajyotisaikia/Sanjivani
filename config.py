import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'data.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
SECRET_KEY = 'please-change-this-in-production'
ALLOWED_EXTENSIONS = {'pdf','png','jpg','jpeg'}