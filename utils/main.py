import os
import json
import fitz  # PyMuPDF
from PIL import Image
from utils.ocr import get_ocr_results

def get_pdf_info(upload_folder, pdf_id):
    pdf_files = [f for f in os.listdir(upload_folder) if f.startswith(pdf_id) and f.endswith('.pdf')]
    if len(pdf_files) != 1:
        return None 
    pdf_filename = pdf_files[0]
    pdf_name = os.path.splitext(pdf_filename)[0]
    pdf_input = os.path.join(upload_folder, pdf_filename)
    pdf_document = fitz.open(pdf_input)
    page_count = pdf_document.page_count
    return pdf_filename, pdf_name, page_count, pdf_input


def get_svg_page_image(pdf_input, page_num):
    pdf_document = fitz.open(pdf_input)
    page = pdf_document.load_page(page_num - 1)
    svg_image = page.get_svg_image()
    return svg_image

def extract_bbox_content(UPLOAD_FOLDER, pdf_input, pdf_filename, pdf_name, page_num, x, y, width, height):
    pdf_document = fitz.open(pdf_input)
    save_directory = UPLOAD_FOLDER
    os.makedirs(save_directory, exist_ok=True)

    json_path = os.path.join(save_directory, "extracted_data.json")
    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            extracted_data = json.load(json_file)
    else:
        extracted_data = {pdf_name: {}}

    # Load the page and extract the specified region
    page = pdf_document.load_page(page_num - 1)
    bbox = fitz.Rect(x, y, x + width, y + height)
    pix = page.get_pixmap(clip=bbox)

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doubled_size = (img.width * 2, img.height * 2)
    resized_img = img.resize(doubled_size, Image.LANCZOS)

    # Save the extracted image as a PNG
    img_filename = f"extracted_page{page_num}_{x}_{y}.png"
    img_folder = os.path.join(save_directory, "images")
    os.makedirs(img_folder, exist_ok=True)
    img_path = os.path.join(img_folder, img_filename)
    resized_img.save(img_path)

    # Format the page key as "Page {number}"
    page_key = f"Page {page_num}"

    # Initialize metadata with fixed keys and None values
    initial_metadata = {
        'lengthField': None,
        'breadthField': None,
        'heightField': None,
        'paintCostField': None,
        'noteField': None
    }

    # Update the extracted data dictionary without OCR text
    if page_key not in extracted_data[pdf_name]:
        extracted_data[pdf_name][page_key] = []
    line_item_number = len(extracted_data[pdf_name][page_key]) + 1
    extracted_data[pdf_name][page_key].append({
        "line_item": line_item_number,
        "coordinates": {"x": x, "y": y, "width": width, "height": height},
        "img_path": img_filename, 
        "img_actual_path" : img_path,
        "metadata": initial_metadata
    })

    # Save updated data back to the JSON file
    with open(json_path, 'w') as json_file:
        json.dump(extracted_data, json_file, indent=4)

    message = f'BBox contents saved as {img_path}'
    return message, page_key, line_item_number

def perform_ocr_on_image(UPLOAD_FOLDER, pdf_name, page_num, line_item, x, y, width, height):
    save_directory = UPLOAD_FOLDER
    json_path = os.path.join(save_directory, "extracted_data.json")

    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            extracted_data = json.load(json_file)
    else:
        return False, 'No extracted data found'

    page_key = f"Page {page_num}"

    if page_key in extracted_data[pdf_name]:
        line_items = extracted_data[pdf_name][page_key]
        # Find the line item in the list
        item = next((item for item in line_items if item["line_item"] == line_item), None)
        if item:
            # Load the image associated with the line item
            img_filename = item['img_path']
            # img_path = item['img_path']
            img_path = os.path.join(save_directory, "images", img_filename)
            if os.path.exists(img_path):
                img = Image.open(img_path)

                # Crop the image according to the bounding box
                bbox = (x, y, x + width, y + height)
                cropped_img = img.crop(bbox)

                # Perform OCR on the cropped image
                # Save the cropped image temporarily
                cropped_img_path = os.path.join(save_directory, "images", f"cropped_{img_filename}")
                # cropped_img_path = os.path.join(img_path)
                cropped_img.save(cropped_img_path)

                ocr_text = get_ocr_results(cropped_img_path)

                # Remove the temporary cropped image
                # os.remove(cropped_img_path)

                # Return the OCR text
                return True, ocr_text
            else:
                return False, 'Image file not found'
        else:
            return False, 'Line item not found'
    else:
        return False, 'Page not found'

def update_line_item_metadata(UPLOAD_FOLDER, pdf_name, page_num, line_item, data):
    save_directory = UPLOAD_FOLDER
    json_path = os.path.join(save_directory, "extracted_data.json")

    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            extracted_data = json.load(json_file)
    else:
        return False, 'No extracted data found'

    page_key = f"Page {page_num}"

    if page_key in extracted_data[pdf_name]:
        line_items = extracted_data[pdf_name][page_key]
        # Find the line item in the list
        item = next((item for item in line_items if item["line_item"] == line_item), None)
        if item:
            # Update the metadata fields with fixed keys
            metadata_fields = ['lengthField', 'breadthField', 'heightField', 'paintCostField', 'noteField']
            metadata = {}
            for field in metadata_fields:
                value = data.get(field)
                # Replace empty strings with None
                if value == '':
                    metadata[field] = None
                else:
                    metadata[field] = value
            item['metadata'] = metadata
            # Save updated data back to the JSON file
            with open(json_path, 'w') as json_file:
                json.dump(extracted_data, json_file, indent=4)
            return True, 'Metadata saved successfully'
        else:
            return False, 'Line item not found'
    else:
        return False, 'Page not found'

def get_line_item_data(UPLOAD_FOLDER, pdf_name, page_num, line_item):
    save_directory = UPLOAD_FOLDER
    json_path = os.path.join(save_directory, "extracted_data.json")

    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            extracted_data = json.load(json_file)
    else:
        return False, 'No extracted data found'

    page_key = f"Page {page_num}"

    if page_key in extracted_data[pdf_name]:
        line_items = extracted_data[pdf_name][page_key]
        item = next((item for item in line_items if item["line_item"] == line_item), None)
        if item:
            # Ensure metadata has fixed keys with None values if missing
            metadata_fields = ['lengthField', 'breadthField', 'heightField', 'paintCostField', 'noteField']
            if not item.get('metadata'):
                item['metadata'] = {field: None for field in metadata_fields}
            else:
                # Ensure all keys are present in metadata and replace empty strings with None
                for field in metadata_fields:
                    value = item['metadata'].get(field)
                    if value == '':
                        item['metadata'][field] = None
                    elif field not in item['metadata']:
                        item['metadata'][field] = None
            # Return the line item data, including img_path and metadata
            return True, item
        else:
            return False, 'Line item not found'
    else:
        return False, 'Page not found'

def get_extracted_items_data(UPLOAD_FOLDER, pdf_name):
    save_directory = UPLOAD_FOLDER
    json_path = os.path.join(save_directory, "extracted_data.json")
    pdf_folder = os.path.join(os.getcwd(), "data", "pdf")
    
    pdf_files = [f for f in os.listdir(pdf_folder) if f.startswith(pdf_name)]
    if not pdf_files:
        page_count = 0
    else:
        pdf_filename = pdf_files[0]
        pdf_input = os.path.join(pdf_folder, pdf_filename)
        pdf_document = fitz.open(pdf_input)
        page_count = pdf_document.page_count

    data = {pdf_name: {}}
    
    for page_num in range(1, page_count + 1):
        page_key = f"Page {page_num}"
        data[pdf_name][page_key] = None

    # If the JSON file exists, update the data with actual values
    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            extracted_data = json.load(json_file)
        # Update the data dictionary with extracted data
        for page_key in extracted_data.get(pdf_name, {}):
            line_items = extracted_data[pdf_name][page_key]
            # Ensure metadata has fixed keys with None values and replace empty strings
            metadata_fields = ['lengthField', 'breadthField', 'heightField', 'paintCostField', 'noteField']
            for item in line_items:
                if not item.get('metadata'):
                    item['metadata'] = {field: None for field in metadata_fields}
                else:
                    for field in metadata_fields:
                        value = item['metadata'].get(field)
                        if value == '':
                            item['metadata'][field] = None
                        elif field not in item['metadata']:
                            item['metadata'][field] = None
                # Replace empty strings in coordinates if necessary
                # (Assuming coordinates are always numbers; adjust if needed)
            data[pdf_name][page_key] = line_items
    
    return data

def delete_line_item_data(UPLOAD_FOLDER, pdf_name, page_num, line_item):
    save_directory = UPLOAD_FOLDER
    json_path = os.path.join(save_directory, "extracted_data.json")

    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            extracted_data = json.load(json_file)
    else:
        return False, 'No extracted data found'

    page_key = f"Page {page_num}"

    if page_key in extracted_data[pdf_name]:
        line_items = extracted_data[pdf_name][page_key]
        item = next((item for item in line_items if item["line_item"] == line_item), None)
        if item:
            # Remove the image file if it exists
            img_filename = item['img_path']
            img_path = os.path.join(save_directory, "images", img_filename)
            if os.path.exists(img_path):
                os.remove(img_path)

            # Remove the item from the list and update the JSON file
            line_items.remove(item)
            if not line_items:  # If no items left on the page, delete the page entry
                del extracted_data[pdf_name][page_key]

            with open(json_path, 'w') as json_file:
                json.dump(extracted_data, json_file, indent=4)

            return True, 'Line item deleted'
    return False, 'Line item not found'
