import argparse
from src.resizer import resize_images_maintain_aspect_ratio
from src.watermark import add_watermark


def main():
    parser = argparse.ArgumentParser(description="Image Processing Tool")

    # Arguments for input and output paths
    parser.add_argument('--input_path', type=str, required=True, help="Path to the input image")
    parser.add_argument('--output_path', type=str, required=True, help="Path to save the processed image")

    # Optional flags for resizing
    parser.add_argument('--resize', action='store_true', help="Flag to resize the image")
    parser.add_argument('--max_width', type=int, default=800, help="Max width for resizing (default is 800)")
    parser.add_argument('--max_height', type=int, default=800, help="Max height for resizing (default is 800)")

    # Optional flags for adding watermark
    parser.add_argument('--add_watermark', action='store_true', help="Flag to add a watermark to the image")
    parser.add_argument('--watermark_text', type=str, default="Sample Watermark", help="Text for the watermark (ignored if --watermark_image is used)")
    parser.add_argument('--watermark_image', type=str, default=None, help="Path to an image file for watermarking")
    parser.add_argument('--position', type=str, choices=['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center'], default='bottom-right', help="Position of the watermark")
    parser.add_argument('--alpha', type=float, default=0.5, help="Transparency level of the watermark (0 to 1, default is 0.5)")
    parser.add_argument('--fill', action='store_true', help="Flag to fill the entire image with watermark")
    parser.add_argument('--text_color', type=str, default="#ffffff", help="Hex color code for the text watermark.")

    args = parser.parse_args()

    if args.resize:
        print("Resizing the image...")
        resize_images_maintain_aspect_ratio(input_dir=args.input_path, output_dir=args.output_path, max_size=(args.max_width, args.max_height))
    if args.add_watermark:
        print("Adding watermark to the image...")
        add_watermark(
            input_dir=args.output_path if args.resize else args.input_path,
            output_dir=args.output_path,
            watermark_text=args.watermark_text if not args.watermark_image else None,
            watermark_image=args.watermark_image,
            position=args.position,
            alpha=args.alpha,
            fill=args.fill,
            text_color=args.text_color
        )


if __name__ == "__main__":
    main()
