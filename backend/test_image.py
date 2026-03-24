import requests
import io
from PIL import Image

# Create a valid 10x10 JPEG in memory
img = Image.new('RGB', (10, 10), color = 'red')
buf = io.BytesIO()
img.save(buf, format='JPEG')
jpeg_bytes = buf.getvalue()

with open('dummy.jpg', 'wb') as f:
    f.write(jpeg_bytes)

with open('dummy.jpg', 'rb') as f:
    res = requests.post('http://127.0.0.1:8000/api/v1/verify/upload', files={'file': ('dummy.jpg', f, 'image/jpeg')}, data={'detection_mode': 'faceswap'})

print('Status:', res.status_code)
print('Response:', res.text)
