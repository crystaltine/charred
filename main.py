import curses
from logger import Logger
import traceback
from cursor import hide, show
from gd_constants import stuff
from camera_frame import CameraFrame

def main():
    frame = CameraFrame()
    frame.fill((255, 0, 0))
    frame.render_raw()    
    curses.napms(500)
    new_frame = CameraFrame()
    new_frame.fill((255, 255, 255))
    new_frame.add_rect((0, 0, 0), 10, 10, 50, 50)
    new_frame.render(frame)
    curses.napms(5000)
    

if __name__ == "__main__":
    try:
        hide()
        main()        
    
    except Exception as e:
        Logger.log(f"[Main Thread/main2.py] Error: {traceback.format_exc()}")
        print(f"\x1b[31m{traceback.format_exc()}\x1b[0m")
    
    show()
    curses.endwin()  
    Logger.write()
        