import io
import logging
import requests
from PIL import Image, ImageDraw

# Animation parameters (based on common PetPet implementations)
AVATAR_BASE_SIZE = (112, 112)  # The size the input avatar will be resized to initially
CANVAS_SIZE = (112, 112)      # Output GIF dimensions
FRAME_DURATION_MS = 50        # Duration of each frame in milliseconds

# Hand animation sequence (indices for hand0.png to hand4.png)
ANIMATION_HAND_INDICES = [0, 1, 2, 3, 4, 3, 2, 1] # 8 frames total for one pat cycle

# Deformation parameters for the avatar for each of the 5 unique hand states.
# (x, y, width, height) of the avatar on the 112x112 canvas.
AVATAR_DEFORM_PARAMS = {
    0: {"x": 22, "y": 28, "w": 70, "h": 62}, # Corresponds to hand0.png
    1: {"x": 20, "y": 30, "w": 74, "h": 60}, # Corresponds to hand1.png
    2: {"x": 16, "y": 32, "w": 80, "h": 58}, # Corresponds to hand2.png
    3: {"x": 12, "y": 30, "w": 88, "h": 60}, # Corresponds to hand3.png
    4: {"x": 10, "y": 28, "w": 90, "h": 62}  # Corresponds to hand4.png
}
# Adjusted y & h values slightly for better visual based on common generators

HAND_IMAGE_PATHS = [f"assets/hand{i}.png" for i in range(5)]
HAND_IMAGE_PATHS = [f"assets/pet{i}.gif" for i in range(5)] # Updated to use petX.gif

async def generate_petpet_gif(avatar_url: str) -> io.BytesIO | None:
    """
    Generates an animated PetPet GIF for the given avatar URL.

    Args:
        avatar_url: URL of the user's avatar.

    Returns:
        An io.BytesIO object containing the GIF data, or None if an error occurred.
    """
    try:
        # Fetch and prepare avatar
        response = requests.get(avatar_url, stream=True, timeout=10)
        response.raise_for_status()
        avatar_bytes = response.content
        
        base_avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        base_avatar_img = base_avatar_img.resize(AVATAR_BASE_SIZE, Image.Resampling.LANCZOS)

        # Load hand images
        hand_images = []
        for i in range(5):
            try:
                hand_img = Image.open(HAND_IMAGE_PATHS[i]).convert("RGBA")
                if hand_img.size != CANVAS_SIZE: # Ensure hands are also 112x112
                    hand_img = hand_img.resize(CANVAS_SIZE, Image.Resampling.LANCZOS)
                hand_images.append(hand_img)
            except FileNotFoundError:
                logging.error(f"Hand image not found: {HAND_IMAGE_PATHS[i]}")
                return None
        
        output_frames = []

        for hand_idx_for_cycle in ANIMATION_HAND_INDICES:
            # Get deformation parameters for the current hand state
            deform_params = AVATAR_DEFORM_PARAMS[hand_idx_for_cycle]

            # Create a new transparent canvas for this frame
            frame_canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))

            # Deform (resize) the base avatar
            squished_avatar = base_avatar_img.resize(
                (deform_params["w"], deform_params["h"]), 
                Image.Resampling.LANCZOS
            )

            # Paste the deformed avatar onto the canvas at its specified position
            frame_canvas.paste(squished_avatar, (deform_params["x"], deform_params["y"]), squished_avatar)

            # Get the current hand image
            current_hand_image = hand_images[hand_idx_for_cycle]
            
            # Paste the hand image over the avatar
            # Hand images are 112x112 and pre-positioned, so paste at (0,0)
            frame_canvas.paste(current_hand_image, (0, 0), current_hand_image)
            
            output_frames.append(frame_canvas)

        # Save frames as an animated GIF into a BytesIO object
        gif_bytesio = io.BytesIO()
        output_frames[0].save(
            gif_bytesio, format="GIF", save_all=True, append_images=output_frames[1:],
            duration=FRAME_DURATION_MS, loop=0, transparency=0, disposal=2 # disposal=2 means restore background
        )
        gif_bytesio.seek(0)
        return gif_bytesio

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download avatar: {e}")
    except IOError as e: # Catches PIL image opening/processing errors
        logging.error(f"Image processing error for PetPet: {e}")
    except Exception as e:
        logging.error(f"Unexpected error generating PetPet GIF: {e}", exc_info=True)
    return None