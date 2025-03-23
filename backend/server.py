from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import cv2
from ultralytics import YOLO
import google.generativeai as genai
import PIL.Image

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains

# Define folders
UPLOAD_FOLDER = "static/upload/"
PREDICT_FOLDER = "static/predict/"
ROI_FOLDER = "static/roi/"

# Ensure directories exist
for folder in [UPLOAD_FOLDER, PREDICT_FOLDER, ROI_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Load YOLO model
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "best.pt")  # Ensure the correct model path
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file not found at: {MODEL_PATH}")

model = YOLO(MODEL_PATH)

# Configure Gemini API
genai.configure(api_key="AIzaSyAPF-G0aBiJRshWF_9nxgf5HrAHLu-ewZU")  # Replace with your actual API key
gemini_model = genai.GenerativeModel('gemini-2.0-pro-exp-02-05')  # Use the correct model name

@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "OCR API is running"}), 200

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = file.filename
    img_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(img_path)

    try:
        # Run YOLO model
        results = model(img_path, conf=0.25, save=True, save_txt=True)
        if not results:
            return jsonify({"error": "No detections from YOLO model"}), 500

        output_dir = results[0].save_dir  # ✅ Get YOLO output directory
        print(f"YOLO results saved at: {output_dir}")

        # File paths
        pred_img_path = os.path.join(output_dir, filename)
        label_path = os.path.join(output_dir, "labels", filename.replace('.jpg', '.txt'))
        
        detected_objects = []
        unique_plates = set()  # ✅ Track unique detections

        if os.path.exists(label_path):
            image = cv2.imread(pred_img_path)
            if image is None:
                return jsonify({"error": "Failed to load processed image"}), 500

            h, w, _ = image.shape  # Get image dimensions

            with open(label_path, "r") as f:
                lines = f.readlines()

            for line in lines:
                class_id, x_center, y_center, width, height = map(float, line.split())

                # Convert YOLO format to pixel values
                xmin = int((x_center - width / 2) * w)
                ymin = int((y_center - height / 2) * h)
                xmax = int((x_center + width / 2) * w)
                ymax = int((y_center + height / 2) * h)

                # Crop the detected license plate
                cropped_plate = image[ymin:ymax, xmin:xmax]
                cropped_filename = f"plate_{filename}"
                cropped_path = os.path.join(ROI_FOLDER, cropped_filename)

                # Ensure uniqueness before saving
                if cropped_filename not in unique_plates:
                    unique_plates.add(cropped_filename)
                    cv2.imwrite(cropped_path, cropped_plate)

                    # Preprocess the cropped plate for Gemini API
                    gray = cv2.cvtColor(cropped_plate, cv2.COLOR_BGR2GRAY)
                    resized = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                    filtered = cv2.bilateralFilter(resized, 11, 17, 17)
                    _, binary = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    preprocessed_img = PIL.Image.fromarray(binary)

                    prompt = '''The Image holds sensitive information; please be careful with your response. The Image I am providing you is an Indian License Plate. 
                    I want to extract the text from the license plate. Do not change your response again and again I want a confident answer from you. 
                    The License plate number should be displayed as; Example- License Number: *EXTRACTED TEXT*. When Multiple License plates detected, 
                    The License plate number should be displayed as; Example- License Number 1: *EXTRACTED TEXT 1*\nLicense Number n: *EXTRACTED TEXT n*.
                    If the image seems to be a stylized, handwritten word, then respond as; Example- License Number: *Cannot Extract Text*.'''
                    response = gemini_model.generate_content([prompt, preprocessed_img])

                    detected_objects.append({
                        "cropped_plate": cropped_filename,
                        "extracted_text": response.text
                    })

        # Move processed image to static/predict
        processed_filename = f"pred_{filename}"
        processed_path = os.path.join(PREDICT_FOLDER, processed_filename)
        if os.path.exists(pred_img_path):
            pred_img = cv2.imread(pred_img_path)
            if pred_img is not None:
                cv2.imwrite(processed_path, pred_img)

        return jsonify({
            "uploaded_image": filename,
            "processed_image": processed_filename,
            "detections": detected_objects
        })
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

# Routes to serve images
@app.route('/uploads/<filename>')
def serve_uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/predict/<filename>')
def serve_predict(filename):
    return send_from_directory(PREDICT_FOLDER, filename)

@app.route('/roi/<filename>')
def serve_roi(filename):
    return send_from_directory(ROI_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True)