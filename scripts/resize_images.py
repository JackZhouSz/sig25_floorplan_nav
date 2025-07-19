import os
import argparse
from PIL import Image

def resize_images(source_dir, dest_dir, max_shortest_side=1024):
    """
    Resizes images from source_dir so their shortest side is at most max_shortest_side,
    and saves them in dest_dir.
    """
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        print(f"Created directory: {dest_dir}")

    for filename in os.listdir(source_dir):
        source_path = os.path.join(source_dir, filename)

        if not os.path.isfile(source_path):
            continue
        try:
            img = Image.open(source_path)
        except (IOError, SyntaxError) as e:
            print(f"Skipping non-image file: {filename} ({e})")
            continue

        width, height = img.size
        shortest_side = min(width, height)
        
        resized_img = img

        if shortest_side > max_shortest_side:
            if width < height:  # shortest side is width
                new_width = max_shortest_side
                aspect_ratio = height / width
                new_height = int(new_width * aspect_ratio)
            else:  # shortest side is height
                new_height = max_shortest_side
                aspect_ratio = width / height
                new_width = int(new_height * aspect_ratio)
            
            print(f"Resizing {filename} from {width}x{height} to {new_width}x{new_height}")
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
        else:
            print(f"Image {filename} doesn't need resizing. It will be copied.")

        if resized_img.mode in ('RGBA', 'P'):
            resized_img = resized_img.convert('RGB')
        
        base, _ = os.path.splitext(filename)
        dest_filename = f"{base}.jpg"
        dest_path = os.path.join(dest_dir, dest_filename)
        
        resized_img.save(dest_path, "JPEG", quality=95)
        print(f"Saved image to {dest_path}")


def main():
    parser = argparse.ArgumentParser(description="Resize images based on the shortest side's dimension.")
    parser.add_argument("source_dir", help="Directory containing the original images.")
    parser.add_argument("dest_dir", help="Directory to save the resized images.")
    parser.add_argument("--max_shortest_side", type=int, default=1024, help="Maximum pixel size for the shortest side.")

    args = parser.parse_args()

    resize_images(args.source_dir, args.dest_dir, args.max_shortest_side)

if __name__ == "__main__":
    main() 