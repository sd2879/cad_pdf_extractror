import os
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
import fitz  # PyMuPDF
from ocr import get_ocr_results
from PIL import Image

app = Flask(__name__)

# Define the input PDF file path
pdf_input = os.path.join(os.getcwd(), "data", "pdf", "input.pdf")
pdf_document = fitz.open(pdf_input)
pdf_name = os.path.splitext(os.path.basename(pdf_input))[0]
save_directory = os.path.join(os.getcwd(), "data", "instance", pdf_name)

# Ensure the save directory exists
os.makedirs(save_directory, exist_ok=True)

# Path for the JSON file that will store extraction data
json_path = os.path.join(save_directory, "extracted_data.json")

# Load existing data from the JSON file or initialize an empty structure
if os.path.exists(json_path):
    with open(json_path, 'r') as json_file:
        extracted_data = json.load(json_file)
else:
    extracted_data = {pdf_name: {}}

@app.route('/')
def index():
    return render_template('index.html', page_count=pdf_document.page_count, pdf_name=pdf_name)

@app.route('/get_page/<int:page_num>')
def get_page(page_num):
    if 1 <= page_num <= pdf_document.page_count:
        page = pdf_document.load_page(page_num - 1)
        svg_image = page.get_svg_image()
        return jsonify({'svg_data': svg_image})
    else:
        return jsonify({'error': 'Page not found'}), 404

@app.route('/extract_bbox/<int:page_num>', methods=['POST'])
def extract_bbox(page_num):
    if 1 <= page_num <= pdf_document.page_count:
        data = request.get_json()
        x, y, width, height = data['x'], data['y'], data['width'], data['height']

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

# New route to serve extracted images
@app.route('/get_image/<filename>')
def get_image(filename):
    return send_from_directory(save_directory, filename)

# New route to handle OCR requests
@app.route('/perform_ocr', methods=['POST'])
def perform_ocr():
    data = request.get_json()
    page_num = data.get('pageNum')
    line_item = data.get('lineItem')
    x = int(data.get('x'))
    y = int(data.get('y'))
    width = int(data.get('width'))
    height = int(data.get('height'))

    page_key = f"Page {page_num}"

    if page_key in extracted_data[pdf_name]:
        line_items = extracted_data[pdf_name][page_key]
        # Find the line item in the list
        item = next((item for item in line_items if item["line_item"] == int(line_item)), None)
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

# Route to get line item data
@app.route('/get_line_item', methods=['POST'])
def get_line_item():
    data = request.get_json()
    page_num = data.get('pageNum')
    line_item = data.get('lineItem')
    page_key = f"Page {page_num}"

    if page_key in extracted_data[pdf_name]:
        line_items = extracted_data[pdf_name][page_key]
        item = next((item for item in line_items if item["line_item"] == int(line_item)), None)
        if item:
            # Return the line item data, including img_path
            return jsonify({'success': True, 'line_item_data': item}), 200
        else:
            return jsonify({'success': False, 'message': 'Line item not found'}), 404
    else:
        return jsonify({'success': False, 'message': 'Page not found'}), 404

@app.route('/submit_metadata', methods=['POST'])
def submit_metadata():
    data = request.get_json()
    page_num = data.get('pageNum')
    line_item = data.get('lineItem')
    page_key = f"Page {page_num}"

    if page_key in extracted_data[pdf_name]:
        line_items = extracted_data[pdf_name][page_key]
        # Find the line item in the list
        item = next((item for item in line_items if item["line_item"] == int(line_item)), None)
        if item:
            # Update the metadata fields
            item['metadata'] = {
                'lengthField': data.get('lengthField'),
                'breadthField': data.get('breadthField'),
                'heightField': data.get('heightField'),
                'paintCostField': data.get('paintCostField'),
                'noteField': data.get('noteField')
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

@app.route('/delete_line_item/<int:page_num>/<int:line_item>', methods=['DELETE'])
def delete_line_item(page_num, line_item):
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

@app.route('/get_extracted_items')
def get_extracted_items():
    # Reload the extracted data from JSON file if it exists
    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            data = json.load(json_file)
        return jsonify(data)
    
    # Return an empty structure if no JSON data exists
    return jsonify({pdf_name: {}}), 200

if __name__ == '__main__':
    app.run(debug=True)
