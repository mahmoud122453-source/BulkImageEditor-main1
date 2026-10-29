from PIL import Image
import os

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg')


def list_supported_images(input_dir, filenames=None):
    """Return supported image names. filenames=None means every image in the folder."""
    if not os.path.isdir(input_dir):
        return []
    candidates = os.listdir(input_dir) if filenames is None else filenames
    supported = []
    for filename in candidates:
        if not filename.lower().endswith(IMAGE_EXTENSIONS):
            continue
        if os.path.isfile(os.path.join(input_dir, filename)):
            supported.append(filename)
    return supported


def resize_images_maintain_aspect_ratio(input_dir, output_dir, max_size=(800, 800), filenames=None):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    results = []
    for filename in list_supported_images(input_dir, filenames):
        img_path = os.path.join(input_dir, filename)
        img = Image.open(img_path)
        original_size = img.size
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        output_path = os.path.join(output_dir, filename)
        img.save(output_path)
        results.append((filename, original_size, img.size))
    return results


if __name__ == "__main__":
    resize_images_maintain_aspect_ratio("../images/input", "../images/output", max_size=(512, 512))
