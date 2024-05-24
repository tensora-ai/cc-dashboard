import cv2
import numpy as np


def compute_homography(src_points, square_size=2.0, px_per_m=10):
    """
    Compute homography matrix based on a square in the real world.

    Parameters:
    - src_points: 4x2 array of source points (x, y) in the image (pixels)
                  Ordered as: [top-left, top-right, bottom-right, bottom-left]
    - square_size: Length of the sides of the square in meters (default is 2 meters)
    - px_per_m: Pixels per meter in the new coordinate system (default is 10 pixels per meter)

    Returns:
    - H: Homography matrix
    """
    assert src_points.shape == (4, 2), "src_points must be a 4x2 array"

    half_size = square_size / 2.0

    # Define destination points, centered at [0, 0] and scaled
    dst_points = np.array(
        [
            [-half_size * px_per_m, -half_size * px_per_m],  # Top-left
            [half_size * px_per_m, -half_size * px_per_m],  # Top-right
            [half_size * px_per_m, half_size * px_per_m],  # Bottom-right
            [-half_size * px_per_m, half_size * px_per_m],  # Bottom-left
        ],
        dtype=np.float32,
    )

    # Compute the homography matrix
    H, _ = cv2.findHomography(src_points, dst_points)
    return H
