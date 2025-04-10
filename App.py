import os
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
import google.generativeai as genai
import requests
import base64
from io import BytesIO
import json
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)

# Configure CORS properly
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

# Configure Hugging Face API
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"

def generate_image_from_prompt(prompt):
    """Generate an image using Hugging Face's FLUX.1-dev model."""
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": 1024,
            "height": 1024,
            "num_inference_steps": 50,
            "guidance_scale": 7.5,
        }
    }
    
    response = requests.post(HUGGINGFACE_API_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        image_bytes = response.content
        # Convert to base64 for sending to client
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        return base64_image
    else:
        raise Exception(f"Error generating image: {response.text}")


def generate_gemini_hashtags_from_bytes(image_bytes, mime_type):
    """Generate 30 relevant hashtags for the given image."""
    image_part = {"mime_type": mime_type, "data": image_bytes}
    prompt = "Generate exactly 30 relevant hashtags for this image, separated by commas."
    
    response = model.generate_content([prompt, image_part])
    return response.text.strip() if response.text else ""


def generate_gemini_hashtags_from_text(topic_text):
    """Generate 30 relevant hashtags for the given topic text."""
    prompt = f"Generate exactly 30 relevant hashtags for the topic: {topic_text}. Return them separated by commas."
    
    response = model.generate_content(prompt)
    return response.text.strip() if response.text else ""


def generate_content_from_text(topic_text, platform='linkedin'):
    """Generate viral social media content for a given topic."""
    prompt = f"""Create a viral social media post for {platform} about: {topic_text}. 
    The post should be engaging, professional, and optimized to reach a wide audience.
    Include relevant emojis, line breaks, and formatting for maximum impact.
    The post should be between 150-300 words.
    """
    
    response = model.generate_content(prompt)
    return response.text.strip() if response.text else ""


def generate_content_from_image(image_bytes, mime_type, topic_text='', platform='linkedin'):
    """Generate viral social media content based on an image and optional topic."""
    image_part = {"mime_type": mime_type, "data": image_bytes}
    
    prompt = f"""Create a viral social media post for {platform} about this image.
    {'The post should focus on: ' + topic_text if topic_text else 'Describe the image and create engaging content around it.'}
    The post should be engaging, professional, and optimized to reach a wide audience.
    Include relevant emojis, line breaks, and formatting for maximum impact.
    The post should be between 150-300 words.
    """
    
    response = model.generate_content([prompt, image_part])
    return response.text.strip() if response.text else ""


def generate_thumbnail_prompt(topic_text):
    """Generate a detailed thumbnail image prompt based on topic."""
    prompt = f"""Create a detailed prompt for generating a thumbnail image about: {topic_text}.
    The prompt should describe a visually appealing, high-quality image that would work well as a 
    YouTube or blog thumbnail. Include details about composition, colors, style, mood, and subject.
    Make it highly detailed and specific for the FLUX.1-dev image model.
    Keep the description focused and concise (80-120 words).
    """
    
    response = model.generate_content(prompt)
    return response.text.strip() if response.text else ""


@app.route('/')
def index():
    """Render the homepage."""
    return render_template('index.html')


@app.route('/generate_hashtags', methods=['POST'])
def generate_hashtags():
    """Handle hashtag generation from uploaded image."""
    if 'image' not in request.files and 'topic' not in request.form:
        return jsonify({'error': 'No image or topic provided'}), 400

    try:
        # Process image if available
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename != '':
                image_bytes = image_file.read()
                mime_type = image_file.content_type
                hashtags_text = generate_gemini_hashtags_from_bytes(image_bytes, mime_type)
            else:
                return jsonify({'error': 'Empty image file'}), 400
        # Process text if no image but topic is provided
        elif 'topic' in request.form:
            topic_text = request.form['topic']
            if topic_text.strip() != '':
                hashtags_text = generate_gemini_hashtags_from_text(topic_text)
            else:
                return jsonify({'error': 'Empty topic text'}), 400

        hashtags = [h.strip() for h in hashtags_text.split(',')]

        return jsonify({'hashtags': hashtags})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate_content', methods=['POST'])
def generate_content():
    """Handle content generation from topic or image+topic."""
    if 'image' not in request.files and 'topic' not in request.form:
        return jsonify({'error': 'No image or topic provided'}), 400

    try:
        platform = request.form.get('platform', 'linkedin')
        topic_text = request.form.get('topic', '').strip()
        
        # Process image+topic if available
        if 'image' in request.files and request.files['image'].filename != '':
            image_file = request.files['image']
            image_bytes = image_file.read()
            mime_type = image_file.content_type
            content = generate_content_from_image(image_bytes, mime_type, topic_text, platform)
        # Process topic only
        elif topic_text:
            content = generate_content_from_text(topic_text, platform)
        else:
            return jsonify({'error': 'Empty topic and no image provided'}), 400

        return jsonify({'content': content})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate_thumbnail', methods=['POST'])
def generate_thumbnail():
    """Handle thumbnail generation with AI image generation."""
    if 'topic' not in request.form:
        return jsonify({'error': 'No topic provided for thumbnail'}), 400

    try:
        topic_text = request.form.get('topic', '').strip()
        
        if not topic_text:
            return jsonify({'error': 'Empty topic provided'}), 400
        
        # Step 1: Generate a detailed prompt using Gemini
        image_prompt = generate_thumbnail_prompt(topic_text)
        
        # Step 2: Use the prompt to generate an image with Hugging Face
        try:
            base64_image = generate_image_from_prompt(image_prompt)
            
            return jsonify({
                'prompt': image_prompt,
                'image': base64_image,
                'success': True
            })
        except Exception as e:
            # If image generation fails, return just the prompt
            return jsonify({
                'prompt': image_prompt,
                'error': str(e),
                'message': 'Generated prompt but image generation failed. You can use this prompt with another tool.',
                'success': False
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.after_request
def after_request(response):
    """Add CORS headers to ensure they're properly set for all responses."""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Set debug=True for development to see detailed error messages
    app.run(host='0.0.0.0', port=port, debug=True)
