from flask import Flask, request, send_file, render_template, jsonify
from PIL import Image
import pillow_avif  # Register AVIF support
import io
import os
from werkzeug.utils import secure_filename
import mimetypes

app = Flask(__name__)
# Remove CORS for same-origin requests only
app.config.update(ENV="production")

# Configure upload settings
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

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

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_image():
    """Handle image conversion"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        output_format = request.form.get('format', 'JPEG').upper()
        
        # Validate file
        if not file.filename or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename, file.content_type):
            return jsonify({'error': 'Invalid file type. Only AVIF, PNG, JPG, JPEG, and WebP are allowed.'}), 400
        
        # Validate output format
        if output_format not in ['JPEG', 'JPG', 'PNG', 'WEBP', 'AVIF']:
            return jsonify({'error': 'Invalid output format'}), 400
        
        # Read and process the image
        try:
            image = Image.open(io.BytesIO(file.read()))
            
            # Convert RGBA to RGB for JPEG format
            if output_format in ['JPEG', 'JPG'] and image.mode in ('RGBA', 'LA', 'P'):
                # Create a white background
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
            original_name = secure_filename(file.filename)
            name_without_ext = os.path.splitext(original_name)[0]
            new_filename = f"{name_without_ext}_converted{get_file_extension(output_format)}"
            
            # Return the converted image
            return send_file(
                output_buffer,
                as_attachment=True,
                download_name=new_filename,
                mimetype=f'image/{output_format.lower()}'
            )
            
        except Exception as e:
            return jsonify({'error': f'Error processing image: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Force disable debug mode and reloader for security
    os.environ.pop("FLASK_DEBUG", None)
    os.environ.pop("FLASK_ENV", None)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, use_debugger=False)