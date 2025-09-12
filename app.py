from flask import Flask, request, send_file, render_template, jsonify, session
from PIL import Image
import pillow_avif  # Register AVIF support
import io
import os
import zipfile
import base64
import uuid
from werkzeug.utils import secure_filename
import mimetypes
from datetime import datetime

app = Flask(__name__)
# Remove CORS for same-origin requests only
app.config.update(ENV="production")
app.secret_key = os.environ.get('SESSION_SECRET', os.urandom(24).hex())

# Configure upload settings
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max total file size for bulk uploads

# In-memory storage for converted images (session-based)
converted_images = {}

# Allowed file extensions and MIME types
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'avif'}
ALLOWED_MIME_TYPES = {
    'image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/avif'
}

def allowed_file(filename, content_type):
    """Check if the uploaded file is allowed"""
    return ('.' in filename and 
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS and
            content_type in ALLOWED_MIME_TYPES)

def get_file_extension(format_type):
    """Get the appropriate file extension for the format"""
    format_map = {
        'JPEG': '.jpg',
        'JPG': '.jpg', 
        'PNG': '.png',
        'WEBP': '.webp',
        'AVIF': '.avif'
    }
    return format_map.get(format_type.upper(), '.jpg')

def convert_single_image(file_data, output_format, original_filename):
    """Convert a single image and return the converted data"""
    try:
        image = Image.open(io.BytesIO(file_data))
        
        # Convert RGBA to RGB for JPEG format
        if output_format in ['JPEG', 'JPG'] and image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # Create output buffer
        output_buffer = io.BytesIO()
        
        # Set conversion parameters based on format
        save_kwargs = {}
        format_name = 'JPEG'  # Default format
        
        if output_format in ['JPEG', 'JPG']:
            save_kwargs = {'quality': 95, 'optimize': True}
            format_name = 'JPEG'
        elif output_format == 'PNG':
            save_kwargs = {'optimize': True}
            format_name = 'PNG'
        elif output_format == 'WEBP':
            save_kwargs = {'quality': 95, 'lossless': False}
            format_name = 'WEBP'
        elif output_format == 'AVIF':
            save_kwargs = {'quality': 95}
            format_name = 'AVIF'
        
        # Save the converted image
        image.save(output_buffer, format=format_name, **save_kwargs)
        output_buffer.seek(0)
        
        # Generate filename
        original_name = secure_filename(original_filename)
        name_without_ext = os.path.splitext(original_name)[0]
        new_filename = f"{name_without_ext}_converted{get_file_extension(output_format)}"
        
        # Get image data for preview (create a smaller thumbnail)
        preview_buffer = io.BytesIO()
        thumbnail = image.copy()
        thumbnail.thumbnail((200, 200), Image.Resampling.LANCZOS)
        thumbnail.save(preview_buffer, format='JPEG', quality=85)
        preview_buffer.seek(0)
        preview_base64 = base64.b64encode(preview_buffer.getvalue()).decode('utf-8')
        
        return {
            'success': True,
            'filename': new_filename,
            'data': output_buffer.getvalue(),
            'preview': preview_base64,
            'mimetype': f'image/{output_format.lower() if output_format.lower() != "jpg" else "jpeg"}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'filename': original_filename
        }

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_bulk_images():
    """Handle bulk image conversion"""
    try:
        # Check if files are present
        if 'files' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        output_format = request.form.get('format', 'JPEG').upper()
        
        # Validate files
        if not files or len(files) == 0:
            return jsonify({'error': 'No files selected'}), 400
        
        # Validate output format
        if output_format not in ['JPEG', 'JPG', 'PNG', 'WEBP', 'AVIF']:
            return jsonify({'error': 'Invalid output format'}), 400
        
        # Generate session ID for this conversion batch
        session_id = str(uuid.uuid4())
        session['current_conversion'] = session_id
        converted_images[session_id] = []
        
        results = []
        successful_conversions = 0
        
        for file in files:
            if file.filename and file.filename != '':
                if allowed_file(file.filename, file.content_type):
                    # Convert the image
                    file_data = file.read()
                    result = convert_single_image(file_data, output_format, file.filename)
                    
                    if result['success']:
                        # Store converted image data in memory
                        image_id = str(uuid.uuid4())
                        converted_images[session_id].append({
                            'id': image_id,
                            'filename': result['filename'],
                            'data': result['data'],
                            'mimetype': result['mimetype']
                        })
                        
                        # Add to results for frontend
                        results.append({
                            'success': True,
                            'original_filename': file.filename,
                            'converted_filename': result['filename'],
                            'preview': result['preview'],
                            'download_id': image_id
                        })
                        successful_conversions += 1
                    else:
                        results.append({
                            'success': False,
                            'original_filename': file.filename,
                            'error': result['error']
                        })
                else:
                    results.append({
                        'success': False,
                        'original_filename': file.filename,
                        'error': 'Invalid file type. Only AVIF, PNG, JPG, JPEG, and WebP are allowed.'
                    })
            
        return jsonify({
            'session_id': session_id,
            'total_files': len(files),
            'successful_conversions': successful_conversions,
            'results': results
        })
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/download/<image_id>')
def download_single_image(image_id):
    """Download a single converted image"""
    try:
        session_id = session.get('current_conversion')
        if not session_id or session_id not in converted_images:
            return jsonify({'error': 'No conversion session found'}), 404
        
        # Find the image
        image_data = None
        for img in converted_images[session_id]:
            if img['id'] == image_id:
                image_data = img
                break
        
        if not image_data:
            return jsonify({'error': 'Image not found'}), 404
        
        # Return the image file
        return send_file(
            io.BytesIO(image_data['data']),
            as_attachment=True,
            download_name=image_data['filename'],
            mimetype=image_data['mimetype']
        )
        
    except Exception as e:
        return jsonify({'error': f'Download error: {str(e)}'}), 500

@app.route('/download-zip')
def download_zip():
    """Download all converted images as a ZIP file"""
    try:
        session_id = session.get('current_conversion')
        if not session_id or session_id not in converted_images:
            return jsonify({'error': 'No conversion session found'}), 404
        
        if not converted_images[session_id]:
            return jsonify({'error': 'No converted images found'}), 404
        
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for img in converted_images[session_id]:
                zip_file.writestr(img['filename'], img['data'])
        
        zip_buffer.seek(0)
        
        # Generate ZIP filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'converted_images_{timestamp}.zip'
        
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({'error': f'ZIP creation error: {str(e)}'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Force disable debug mode and reloader for security
    os.environ.pop("FLASK_DEBUG", None)
    os.environ.pop("FLASK_ENV", None)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, use_debugger=False)