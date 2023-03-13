import os, random
dir = 'plugins/pattern/image_guess/src/'


for x in range(0,5):
    all_files = os.listdir(dir)
    file = random.choice(all_files)
    print(file)