from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from PIL import Image
import pytesseract
import re
import io
from bson import ObjectId

# ✅ Path to Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ✅ Initialize Flask app
app = Flask(__name__)
CORS(app)

# ✅ MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["SecureKYC_DB"]
aadhaar_collection = db["aadhaar_data"]
pan_collection = db["pan_data"]

# ✅ Helper function to convert ObjectId to string
def convert_objectid(data):
    if isinstance(data, dict):
        return {k: convert_objectid(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_objectid(i) for i in data]
    elif isinstance(data, ObjectId):
        return str(data)
    return data


# -------------------------------
# 🧠 Aadhaar OCR Extraction API
# -------------------------------
@app.route("/extract_aadhaar", methods=["POST"])
def extract_aadhaar():
    try:
        if "aadhaar" not in request.files:
            return jsonify({"error": "No Aadhaar file uploaded"}), 400

        file = request.files["aadhaar"]
        image = Image.open(file.stream)

        text = pytesseract.image_to_string(image)
        print("📥 Aadhaar API hit!")
        print("🔍 Extracted Text:\n", text)

        name, dob, gender, aadhaar_number, address = None, None, None, None, None

        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if re.search(r"Name", line, re.IGNORECASE):
                name = line.split(":")[-1].strip()
            elif re.search(r"DOB", line, re.IGNORECASE):
                dob = line.split(":")[-1].strip()
            elif re.search(r"Male|Female|Others", line, re.IGNORECASE):
                gender = line.strip()
            elif re.search(r"\d{4}\s\d{4}\s\d{4}", line):
                aadhaar_number = line.strip()

        extracted_data = {
            "name": name,
            "dob": dob,
            "gender": gender,
            "aadhaar_number": aadhaar_number,
            "address": address,
        }

        inserted = aadhaar_collection.insert_one(extracted_data)
        print("✅ Aadhaar data inserted successfully into MongoDB!")

        response_data = {
            "message": "Aadhaar data extracted successfully!",
            "extracted_data": extracted_data,
            "inserted_id": str(inserted.inserted_id)
        }

        return jsonify(convert_objectid(response_data)), 200

    except Exception as e:
        print("❌ Error during Aadhaar extraction:", e)
        return jsonify({"error": str(e)}), 500


# -------------------------------
# 🧾 PAN Card OCR Extraction API
# -------------------------------
@app.route("/extract_pan", methods=["POST"])
def extract_pan():
    try:
        if "pan" not in request.files:
            return jsonify({"error": "No PAN file uploaded"}), 400

        file = request.files["pan"]
        image = Image.open(file.stream)

        text = pytesseract.image_to_string(image)
        print("📥 PAN API hit!")
        print("🔍 Extracted Text:\n", text)

        # ✅ Initialize extracted fields
        name, father_name, dob, pan_number = None, None, None, None

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines:
            # PAN number pattern (ABCDE1234F)
            if re.search(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", line):
                pan_number = re.search(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", line).group(0)
            elif re.search(r"DOB|Date of Birth", line, re.IGNORECASE):
                dob = re.sub(r"DOB|Date of Birth|:", "", line, flags=re.IGNORECASE).strip()
            elif name is None and re.search(r"[A-Z\s]+", line):
                name = line.strip()
            elif father_name is None and re.search(r"[A-Z\s]+", line):
                father_name = line.strip()

        extracted_data = {
            "name": name,
            "father_name": father_name,
            "dob": dob,
            "pan_number": pan_number
        }

        inserted = pan_collection.insert_one(extracted_data)
        print("✅ PAN data inserted successfully into MongoDB!")

        response_data = {
            "message": "PAN data extracted successfully!",
            "extracted_data": extracted_data,
            "inserted_id": str(inserted.inserted_id)
        }

        return jsonify(convert_objectid(response_data)), 200

    except Exception as e:
        print("❌ Error during PAN extraction:", e)
        return jsonify({"error": str(e)}), 500


# -------------------------------
# 🚀 Main Entry
# -------------------------------
if __name__ == "__main__":
    print("✅ Successfully connected to MongoDB: SecureKYC_DB")
    app.run(debug=True)
