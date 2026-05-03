import os
import random
from PIL import Image, ImageTk

class GameLogic:
    def __init__(self, image_folder, max_size=(500, 500)):
        self.image_folder = image_folder
        self.max_size = max_size
        self.images = self._load_images()
        self.current_image = None
        self.current_image_path = None

    def _load_images(self):
        if not os.path.exists(self.image_folder):
            os.makedirs(self.image_folder, exist_ok=True)
            return []
        return [f for f in os.listdir(self.image_folder)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]

    def get_random_image(self):
        if not self.images:
            return None, None
        self.current_image_path = os.path.join(self.image_folder, random.choice(self.images))
        try:
            img = Image.open(self.current_image_path)
            img = self._scale_image(img)
            return ImageTk.PhotoImage(img), self.current_image_path
        except Exception as e:
            print(f"Error loading image: {e}")
            return None, None

    def _scale_image(self, img):
        # Maintain aspect ratio, fit within max_size
        img.thumbnail(self.max_size, Image.LANCZOS)
        # Create a new image with black background
        background = Image.new('RGB', self.max_size, (0, 0, 0))
        # Paste the resized image in the center
        offset = (
            (self.max_size[0] - img.width) // 2,
            (self.max_size[1] - img.height) // 2
        )
        background.paste(img, offset)
        return background
