'''
A helper program to resize provided images into the same size
ex) 64x64 for Discord

* PIL is required

Author: David Chen
'''
from PIL import Image
from pathlib import Path

orig_path = Path('./assets/original')
resized_path = Path('./assets/resized')
new_size = (64, 64)

for img_path in orig_path.iterdir():
    img = Image.open(img_path)
    img_resized = img.resize(new_size, Image.ANTIALIAS)
    img_resized.save(resized_path / img_path.name)
