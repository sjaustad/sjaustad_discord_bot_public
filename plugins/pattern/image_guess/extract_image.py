from PIL import Image
import math

## delete old images
import os
dir = 'plugins/pattern/image_guess/src/'
for f in os.listdir(dir):
    os.remove(os.path.join(dir, f))

image = Image.open("plugins\pattern\image_guess\stpetersbasilica.jpeg")
w,h = image.size

split_height = 70
split_width = 70

##118 x 79

columns = math.ceil(w / split_width)
rows = math.ceil(h/split_height)

height = 0 
width = 0
for x in range(columns):
    width = 0
    for y in range(rows):
        crop_box = (width,height,width+split_height,height+split_width)
        cropped_image = image.crop(crop_box)
        width = width + split_width + 1

        cropped_image.save(f"plugins/pattern/image_guess/src/{str(height)+str(width)}.jpg")
        
    height = height + split_height + 1