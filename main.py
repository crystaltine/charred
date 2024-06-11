import curses
from logger import Logger
import traceback
from cursor import hide, show
from gd_constants import stuff
from time import sleep, time_ns
from camera_frame import CameraFrame
from vid_to_np import get_bad_apple

def main():
    
    FPS = 30
    
    bad_apple = get_bad_apple()
    
    #stuff.screen.addstr(0, 0, f"bad apple video array shape: {bad_apple.shape}")
    sleep(2)
    
    frame = CameraFrame()
    frame.add_pixels_topleft(0, 0, bad_apple[0])
    frame.render_raw_old()    
    #curses.napms(500)
    for i in range(1, len(bad_apple)):
        
        if i == 3: # print some stuff
            Logger.log("i = 3 rn")
            Logger.log(f"frame: {bad_apple[i]}")
        
        new_frame = CameraFrame()
        new_frame.add_pixels_topleft(0, 0, bad_apple[i])
        
        time_start = time_ns()
        new_frame.render_raw_old()
        Logger.log(f"frame {i} took {(time_ns()-time_start)/1e9:4f}s to render.")
        sleep(round(1/FPS))
    

if __name__ == "__main__":
    try:
        hide()
        main()        
    
    except Exception as e:
        Logger.log(f"[Main Thread/main2.py] Error: {traceback.format_exc()}")
        print(f"\x1b[31m{traceback.format_exc()}\x1b[0m")
    except KeyboardInterrupt:
        Logger.log(f"qutting")
        print(f"quit")
    
    show()
    #curses.endwin()  
    Logger.write()
        