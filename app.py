import os
import json
import uuid
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
import fitz  # PyMuPDF
from ocr import get_ocr_results
from PIL import Image

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "data", "pdf")

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def upload_pdf():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'pdf_file' not in request.files:
            return render_template('upload.html', error='No file part')
        file = request.files['pdf_file']
        # If user does not select file, browser may submit an empty part without filename
        if file.filename == '':
            return render_template('upload.html', error='No selected file')
        if file and file.filename.lower().endswith('.pdf'):
            # Save the uploaded PDF
            pdf_id = str(uuid.uuid4())
            filename = f"{pdf_id}_{file.filename}"
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(pdf_path)
            return redirect(url_for('index', pdf_id=pdf_id))
        else:
            return render_template('index.html', error='Invalid file type. Please upload a PDF.')
    return render_template('index.html')

@app.route('/viewer/<pdf_id>')
def index(pdf_id):
    # Find the PDF file corresponding to the pdf_id
    pdf_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.startswith(pdf_id)]
    if not pdf_files:
        return "PDF not found", 404
    pdf_filename = pdf_files[0]
    pdf_name = os.path.splitext(pdf_filename)[0]
    pdf_input = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
    pdf_document = fitz.open(pdf_input)
    page_count = pdf_document.page_count

    # Define save directory for this PDF
    save_directory = os.path.join(os.getcwd(), "data", "instance", pdf_name)
    os.makedirs(save_directory, exist_ok=True)

    # Path for the JSON file that will store extraction data
    json_path = os.path.join(save_directory, "extracted_data.json")

    # Load existing data from the JSON file or initialize an empty structure
    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            extracted_data = json.load(json_file)
    else:
        extracted_data = {pdf_name: {}}

    # Store in session or pass necessary data to templates
    return render_template('upload.html', page_count=page_count, pdf_name=pdf_name, pdf_id=pdf_id)

@app.route('/get_page/<pdf_id>/<int:page_num>')
def get_page(pdf_id, page_num):
    # Find the PDF file corresponding to the pdf_id
    pdf_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.startswith(pdf_id)]
    if not pdf_files:
        return jsonify({'error': 'PDF not found'}), 404
    pdf_filename = pdf_files[0]
    pdf_input = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
    pdf_document = fitz.open(pdf_input)
    if 1 <= page_num <= pdf_document.page_count:
        page = pdf_document.load_page(page_num - 1)
        svg_image = page.get_svg_image()
        return jsonify({'svg_data': svg_image})
    else:
        return jsonify({'error': 'Page not found'}), 404

@app.route('/extract_bbox/<pdf_id>/<int:page_num>', methods=['POST'])
def extract_bbox(pdf_id, page_num):
    # Similar logic as before, adjusted to use pdf_id
    # Find the PDF file
    pdf_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.startswith(pdf_id)]
    if not pdf_files:
        return jsonify({'error': 'PDF not found'}), 404
    pdf_filename = pdf_files[0]
    pdf_name = os.path.splitext(pdf_filename)[0]
    pdf_input = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
    pdf_document = fitz.open(pdf_input)

    # Define save directory for this PDF
    save_directory = os.path.join(os.getcwd(), "data", "instance", pdf_name)
    os.makedirs(save_directory, exist_ok=True)

    # Path for the JSON file that will store extraction data
    json_path = os.path.join(save_directory, "extracted_data.json")

    # Load existing data from the JSON file or initialize an empty structure
    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            extracted_data = json.load(json_file)
    else:
        extracted_data = {pdf_name: {}}

    if 1 <= page_num <= pdf_document.page_count:
        data = request.get_json()
        try:
            x = float(data['x'])
            y = float(data['y'])
            width = float(data['width'])
            height = float(data['height'])
        except (TypeError, ValueError, KeyError):
            return jsonify({'error': 'Invalid coordinates'}), 400

        # Load the page and extract the specified region
        page = pdf_document.load_page(page_num - 1)
        bbox = fitz.Rect(x, y, x + width, y + height)
        pix = page.get_pixmap(clip=bbox)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doubled_size = (img.width * 2, img.height * 2)
        resized_img = img.resize(doubled_size, Image.LANCZOS)

        # Save the extracted image as a PNG
        img_filename = f"extracted_page{page_num}_{x}_{y}.png"
        img_path = os.path.join(save_directory, img_filename)
        resized_img.save(img_path)

        # Format the page key as "Page {number}"
        page_key = f"Page {page_num}"

        # Update the extracted data dictionary without OCR text
        if page_key not in extracted_data[pdf_name]:
            extracted_data[pdf_name][page_key] = []
        line_item_number = len(extracted_data[pdf_name][page_key]) + 1
        extracted_data[pdf_name][page_key].append({
            "line_item": line_item_number,
            "coordinates": {"x": x, "y": y, "width": width, "height": height},
            "img_path": img_filename,  # Store only the filename
            # Initialize metadata as an empty dictionary
            "metadata": {}
        })

        # Save updated data back to the JSON file
        with open(json_path, 'w') as json_file:
            json.dump(extracted_data, json_file, indent=4)

        return jsonify({'message': f'BBox contents saved as {img_path}', 'page': page_key, 'line_item': line_item_number})
    else:
        return jsonify({'error': 'Page not found'}), 404

@app.route('/get_image/<pdf_name>/<filename>')
def get_image(pdf_name, filename):
    # Serve images from the instance directory
    save_directory = os.path.join(os.getcwd(), "data", "instance", pdf_name)
    return send_from_directory(save_directory, filename)

@app.route('/perform_ocr', methods=['POST'])
def perform_ocr():
    data = request.get_json()
    try:
        pdf_name = data.get('pdfName')
        page_num = int(data.get('pageNum'))
        line_item = int(data.get('lineItem'))
        x = int(float(data.get('x')))
        y = int(float(data.get('y')))
        width = int(float(data.get('width')))
        height = int(float(data.get('height')))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid input parameters'}), 400

    save_directory = os.path.join(os.getcwd(), "data", "instance", pdf_name)
    json_path = os.path.join(save_directory, "extracted_data.json")

    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            extracted_data = json.load(json_file)
    else:
        return jsonify({'success': False, 'message': 'No extracted data found'}), 404

    page_key = f"Page {page_num}"

    if page_key in extracted_data[pdf_name]:
        line_items = extracted_data[pdf_name][page_key]
        # Find the line item in the list
        item = next((item for item in line_items if item["line_item"] == line_item), None)
        if item:
            # Load the image associated with the line item
            img_filename = item['img_path']
            img_path = os.path.join(save_directory, img_filename)
            if os.path.exists(img_path):
                img = Image.open(img_path)

                # Crop the image according to the bounding box
                bbox = (x, y, x + width, y + height)
                cropped_img = img.crop(bbox)

                # Perform OCR on the cropped image
                # Save the cropped image temporarily
                cropped_img_path = os.path.join(save_directory, f"cropped_{img_filename}")
                cropped_img.save(cropped_img_path)

                ocr_text = get_ocr_results(cropped_img_path)

                # Remove the temporary cropped image
                os.remove(cropped_img_path)

                # Return the OCR text to the client
                return jsonify({'success': True, 'ocr_text': ocr_text}), 200
            else:
                return jsonify({'success': False, 'message': 'Image file not found'}), 404
        else:
            return jsonify({'success': False, 'message': 'Line item not found'}), 404
    else:
        return jsonify({'success': False, 'message': 'Page not found'}), 404

@app.route('/get_line_item', methods=['POST'])
def get_line_item():
    data = request.get_json()
    try:
        pdf_name = data.get('pdfName')
        page_num = int(data.get('pageNum'))
        line_item = int(data.get('lineItem'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid page number or line item'}), 400

    save_directory = os.path.join(os.getcwd(), "data", "instance", pdf_name)
    json_path = os.path.join(save_directory, "extracted_data.json")

    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            extracted_data = json.load(json_file)
    else:
        return jsonify({'success': False, 'message': 'No extracted data found'}), 404

    page_key = f"Page {page_num}"

    if page_key in extracted_data[pdf_name]:
        line_items = extracted_data[pdf_name][page_key]
        item = next((item for item in line_items if item["line_item"] == line_item), None)
        if item:
            # Return the line item data, including img_path
            return jsonify({'success': True, 'line_item_data': item, 'pdf_name': pdf_name}), 200
        else:
            return jsonify({'success': False, 'message': 'Line item not found'}), 404
    else:
        return jsonify({'success': False, 'message': 'Page not found'}), 404

@app.route('/submit_metadata', methods=['POST'])
def submit_metadata():
    data = request.get_json()
    try:
        pdf_name = data.get('pdfName')
        page_num = int(data.get('pageNum'))
        line_item = int(data.get('lineItem'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid page number or line item'}), 400

    save_directory = os.path.join(os.getcwd(), "data", "instance", pdf_name)
    json_path = os.path.join(save_directory, "extracted_data.json")

    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            extracted_data = json.load(json_file)
    else:
        return jsonify({'success': False, 'message': 'No extracted data found'}), 404

    page_key = f"Page {page_num}"

    if page_key in extracted_data[pdf_name]:
        line_items = extracted_data[pdf_name][page_key]
        # Find the line item in the list
        item = next((item for item in line_items if item["line_item"] == line_item), None)
        if item:
            # Update the metadata fields (fields are optional)
            item['metadata'] = {
                'lengthField': data.get('lengthField', '') if data.get('lengthField') is not None else '',
                'breadthField': data.get('breadthField', '') if data.get('breadthField') is not None else '',
                'heightField': data.get('heightField', '') if data.get('heightField') is not None else '',
                'paintCostField': data.get('paintCostField', '') if data.get('paintCostField') is not None else '',
                'noteField': data.get('noteField', '') if data.get('noteField') is not None else ''
                # Add more fields as needed
            }
            # Save updated data back to the JSON file
            with open(json_path, 'w') as json_file:
                json.dump(extracted_data, json_file, indent=4)
            return jsonify({'success': True, 'message': 'Metadata saved successfully'}), 200
        else:
            return jsonify({'success': False, 'message': 'Line item not found'}), 404
    else:
        return jsonify({'success': False, 'message': 'Page not found'}), 404

@app.route('/delete_line_item/<pdf_id>/<int:page_num>/<int:line_item>', methods=['DELETE'])
def delete_line_item(pdf_id, page_num, line_item):
    # Similar logic as before, adjusted to use pdf_id
    pdf_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.startswith(pdf_id)]
    if not pdf_files:
        return jsonify({'success': False, 'message': 'PDF not found'}), 404
    pdf_filename = pdf_files[0]
    pdf_name = os.path.splitext(pdf_filename)[0]

    save_directory = os.path.join(os.getcwd(), "data", "instance", pdf_name)
    json_path = os.path.join(save_directory, "extracted_data.json")

    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            extracted_data = json.load(json_file)
    else:
        return jsonify({'success': False, 'message': 'No extracted data found'}), 404

    page_key = f"Page {page_num}"

    if page_key in extracted_data[pdf_name]:
        line_items = extracted_data[pdf_name][page_key]
        item = next((item for item in line_items if item["line_item"] == line_item), None)
        if item:
            # Remove the image file if it exists
            img_filename = item['img_path']
            img_path = os.path.join(save_directory, img_filename)
            if os.path.exists(img_path):
                os.remove(img_path)

            # Remove the item from the list and update the JSON file
            line_items.remove(item)
            if not line_items:  # If no items left on the page, delete the page entry
                del extracted_data[pdf_name][page_key]

            with open(json_path, 'w') as json_file:
                json.dump(extracted_data, json_file, indent=4)

            return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Line item not found'}), 404

@app.route('/get_extracted_items/<pdf_name>')
def get_extracted_items(pdf_name):
    # Reload the extracted data from JSON file if it exists
    save_directory = os.path.join(os.getcwd(), "data", "instance", pdf_name)
    json_path = os.path.join(save_directory, "extracted_data.json")

    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            data = json.load(json_file)
        return jsonify(data)
    
    # Return an empty structure if no JSON data exists
    return jsonify({pdf_name: {}}), 200

if __name__ == '__main__':
    app.run(debug=True)
