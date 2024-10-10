import os
import json
from flask import Flask, render_template, request, jsonify
import fitz  # PyMuPDF

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
        
        # Additional metadata fields
        length = data.get('length', 0)
        item_width = data.get('width', 0)
        item_height = data.get('height', 0)
        cost = data.get('cost', 0.0)

        # Load the page and extract the specified region
        page = pdf_document.load_page(page_num - 1)
        bbox = fitz.Rect(x, y, x + width, y + height)
        pix = page.get_pixmap(clip=bbox)

        # Save the extracted image as a PNG
        img_filename = f"extracted_page{page_num}_{x}_{y}.png"
        img_path = os.path.join(save_directory, img_filename)
        pix.save(img_path)

        # Format the page key as "Page {number}"
        page_key = f"Page {page_num}"

        # Update the extracted data dictionary with metadata
        if page_key not in extracted_data[pdf_name]:
            extracted_data[pdf_name][page_key] = []
        line_item_number = len(extracted_data[pdf_name][page_key]) + 1
        extracted_data[pdf_name][page_key].append({
            "line_item": line_item_number,
            "coordinates": {"x": x, "y": y, "width": width, "height": height},
            "img_path": img_path,
            "metadata": {
                "length": length,
                "width": item_width,
                "height": item_height,
                "cost": cost
            }
        })

        # Save updated data back to the JSON file
        with open(json_path, 'w') as json_file:
            json.dump(extracted_data, json_file, indent=4)

        return jsonify({'message': f'BBox contents saved as {img_path}', 'page': page_key, 'line_item': line_item_number})
    else:
        return jsonify({'error': 'Page not found'}), 404



@app.route('/delete_line_item/<int:page_num>/<int:line_item>', methods=['DELETE'])
def delete_line_item(page_num, line_item):
    page_key = f"Page {page_num}"
    if page_key in extracted_data[pdf_name]:
        line_items = extracted_data[pdf_name][page_key]
        item = next((item for item in line_items if item["line_item"] == line_item), None)
        if item:
            # Remove the image file if it exists
            img_path = item['img_path']
            if os.path.exists(img_path):
                os.remove(img_path)

            # Remove the item from the list and update the JSON file
            line_items.remove(item)
            if not line_items:  # If no items left on the page, delete the page entry
                del extracted_data[pdf_name][page_key]

            # Save changes to JSON
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