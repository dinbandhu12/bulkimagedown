from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
import os
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import threading
import json

app = Flask(__name__)
CORS(app)
executor = ThreadPoolExecutor(max_workers=20)

@app.route('/')
def index():
    return render_template('index.html')


def download_single_image(img_url, filepath):
    """
    Download a single image from the given URL to the specified file path.
    """
    try:
        response = requests.get(img_url, stream=True, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading {img_url}: {e}")
        return False


@app.route('/download', methods=['POST'])
def download_images():
    """
    Endpoint to download images from provided links.
    """
    try:
        data = request.get_json()
        links = data.get('links', '')
        folder_name = data.get('folderName', 'images')

        if not os.path.exists('downloads'):
            os.makedirs('downloads')

        download_path = os.path.join('downloads', folder_name)
        if not os.path.exists(download_path):
            os.makedirs(download_path)

        soup = BeautifulSoup(links, 'html.parser')
        img_tags = soup.find_all('img', class_='lazy')
        total_images = len(img_tags)

        failed_images = []

        def generate():
            downloaded = 0

            for i, img in enumerate(img_tags):
                img_url = img.get('data-src')
                if img_url:
                    filepath = os.path.join(download_path, f'image_{i + 1}.jpg')
                    if download_single_image(img_url, filepath):
                        downloaded += 1
                    else:
                        failed_images.append(img_url)

                    yield f"data: {json.dumps({'current': downloaded, 'total': total_images, 'failed': failed_images})}\n\n"

            yield f"data: {json.dumps({'current': downloaded, 'total': total_images, 'failed': failed_images, 'complete': True})}\n\n"

        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
