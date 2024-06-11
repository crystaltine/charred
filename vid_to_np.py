import cv2
import numpy as np

def extract_frames(video_path, fps=10, width=None, height=None):
    video = cv2.VideoCapture(video_path)
    
    # Get the original FPS of the video
    original_fps = video.get(cv2.CAP_PROP_FPS)
    
    # Calculate the interval between frames to capture based on the desired FPS
    frame_interval = int(original_fps // fps)
    
    # Initialize a list to store the frames
    frames = []
    
    # Initialize a frame counter
    frame_count = 0
    
    while True:
        # Read a frame from the video
        
        ret, frame = video.read()
        
        if not ret:
            print(f"\ndone reading frames")
            break
        
        # If the current frame is at the interval, store it
        if frame_count % frame_interval == 0:
            frame_count += 1
            #if width is not None and height is not None:
            #    frame = cv2.resize(frame, (width, height))
            frames.append(frame)
            #print(f"recording frame {frame_count}")
        else:
            frame_count += 1
            #print(f"skipping frame {frame_count}")
            continue
    
    # Release the video object
    video.release()
    
    # Convert the list of frames to a NumPy array
    print("numpy izing")
    frames_array = np.array(frames)
    print(f"donezo")
    
    return frames_array

def get_bad_apple() -> np.ndarray:

    # Example usage:
    video_path = './badapple240p.mp4'
    frames = extract_frames(video_path, fps=14, width=80, height=60)
    return frames
