import curses
from typing import TYPE_CHECKING, Literal, Tuple, List
from utils import (
    fcode_opt as fco, blend_rgba_img_onto_rgb_img_inplace, 
    first_diff_color, last_diff_color, lesser, greater, draw_line,
    get_diff_intervals, combine_intervals, print2
)
from time import perf_counter
from threading import Thread
from logger import Logger
import numpy as np
from gd_constants import stuff

class CameraFrame:
    """
    Wrapper over a 2D array of pixels for rendering to the screen.
    
    Images with transparency can be added to a CameraFrame, however the final compiled result that gets
    printed to the screen will assume all alpha values are 255 (opaque).
    """

    def __init__(self, size: Tuple[int | None, int | None] = (None, None), pos: Tuple[int | None, int | None] = (0, 0)) -> None:
        """ Optional params:
        - `size`: tuple (width, height) in pixels. None values will default to the terminal's width/height.
        - `pos`: tuple (x, y) in pixels, where the top left corner of the frame will be placed. Defaults to (0, 0) (top left of screen)
        
        NOTE: Height and y-position MUST both be even. Each character is 2 pixels tall, and we cant render half-characters.
        """
        
        assert size[1] is None or size[1] % 2 == 0, f"[CameraFrame/__init__]: height must be even, instead got {size[1]}"
        assert pos[1] is None or pos[1] % 2 == 0, f"[CameraFrame/__init__]: y position must be even, instead got {pos[1]}"
        
        self.width = size[0] if size[0] is not None else stuff.term.width
        """ Width in pixels (1px = width of 1 monospaced character) """
        self.height = size[1] if size[1] is not None else stuff.term.height*2
        """ Height in pixels (2px = height of 1 monospaced character) """
        
        self.pos = pos
        
        self.initialized_colors = set()
        """ Set of color pairs that have been initialized. """
        
        self.pixels: np.ndarray = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        """ 2d array of pixels. Each pixel is an rgb tuple. (0, 0) is the top left of the frame, not the top left of the screen. """

    def render_raw(self) -> None:
        for top_row_index in range(0, self.height, 2):       
            screen_y = top_row_index // 2
            for j in range(len(self.pixels[top_row_index])-1):
                #string += fco(self.pixels[top_row_index,j], self.pixels[top_row_index+1,j]) + '▀' # pixels1 is top, so it gets fg color. pixels2 is bottom, so it gets bg color.
                # TODO - cant use color codes - need to use curses.initcolor
                # ^^ maybe make a color cache???? using rgb tuples -> curses color id
                
                # calculate key of color
                fg_grayscale_value = np.mean(self.pixels[top_row_index,j]) # 0-255
                bg_grayscale_value = np.mean(self.pixels[top_row_index+1,j]) # 0-255
                
                # scale each down to 0-15 (from 0-255)
                scaled_fg = int(fg_grayscale_value / 255 * 15)
                scaled_bg = int(bg_grayscale_value / 255 * 15)
                
                # combine into 8-bit number
                color_key = (scaled_fg << 4) + scaled_bg
                
                if color_key not in self.initialized_colors:
                    # initialize the color pair
                    fg_1000_based = int(scaled_fg / 15 * 1000)
                    bg_1000_based = int(scaled_bg / 15 * 1000)
                    #Logger.log(f"scaled fg: {scaled_fg}, scaled bg: {scaled_bg}, fg_1000_based: {fg_1000_based}, bg_1000_based: {bg_1000_based}")
                    curses.init_color(scaled_fg << 4, fg_1000_based, fg_1000_based, fg_1000_based)
                    curses.init_color(scaled_bg, bg_1000_based, bg_1000_based, bg_1000_based)
                    #Logger.log(f"color key: {color_key}, fg: {scaled_fg << 4}, bg: {scaled_bg}")
                    curses.init_pair(color_key, scaled_fg << 4, scaled_bg)
                    self.initialized_colors.add(color_key)                        
                
                #Logger.log(f"printing at yx {screen_y}, {j} with color key {color_key}")
                stuff.screen.addstr(screen_y, j, "▀", curses.color_pair(color_key))
        
        #Logger.log(f"[CameraFrame/render]: Appending ({print_start}, {print_end}) to indices_to_print, which currently has {len(indices_to_print)} elements (b4 adding)")
        #indices_to_print.append((print_start, print_end))
        
        #Logger.log(f"(raw) refreshing curses screen")
        stuff.screen.refresh()

    def render_raw_old(self) -> None:
        """ Simply prints the frame to the screen, without the need for a previous frame. 
        Keep in mind, this is quite slow and should only be used for rendering the first frame. """
        
        # handle odd starting y. NOTE - this wont happen for now, since we are requiring even starting y and height.
        if self.pos[1] % 2 == 1:
            # first line prints bottom half char (top half will be terminal default bg)
            string1 = ""
            for j in range(self.width):
                string1 += fco(self.pixels[self.pos[1],j], None) + '▀'
            print2(stuff.term.move_xy(self.pos[0], self.pos[1]//2) + string1)
            
            # print middle rows
            stop_at = (self.pos[1] + self.height - (self.pos[1] + self.height) % 2) - 1
            # if height is even there will be an extra line at the end
            # if odd, then we just go until the end right here, since there is no last isolated line
            for i in range(self.pos[1]+1, stop_at):
                string = ""
                for j in range(self.width):
                    string += fco(self.pixels[i,j], self.pixels[i+1,j]) + '▀'
                print2(stuff.term.move_xy(self.pos[0], i//2) + string)
                
            # print last line if needed
            if self.height % 2 == 0: # since y is odd, if height is even, then we have another case of a single line
                string2 = ""
                for j in range(self.width):
                    string2 += fco(None, self.pixels[self.pos[1]+self.height-1,j]) + '▀'
                print2(stuff.term.move_xy(self.pos[0], (self.pos[1]+self.height)//2 + 1) + string2)
            
        else:
            
            #compiled_str = "" # try printing the whole thing at once
            
            for i in range(0, self.height, 2):
                string = ""
                for j in range(self.width):
                    string += fco(self.pixels[i,j], self.pixels[i+1,j]) + '▀' # for quick copy: ▀
                
                #compiled_str += string + "\n"
                print2(stuff.term.move_xy(self.pos[0], (i+self.pos[1])//2) + string)
            #print2(stuff.term.move_xy(self.pos[0], self.pos[1]//2) + compiled_str)
        
        stuff.screen.refresh()

    def render(self, prev_frame: "CameraFrame") -> None:
        """ Prints the frame to the screen using curses.addstr().
        Optimized by only drawing the changes from the previous frame. """
        
        #indices_to_print = []
        #""" Should end up being a list of tuples (start, end) 
        #where start and end are the first and last changed "pixels columns" (characters) in a row. """
        
        # compare the curr frame with the previous frame
        # for each pair of rows, find the first and last changed column
        # multiply term height by 2 since chars are 2 pixels tall
        for top_row_index in range(0, self.height, 2):       
            #first_diff_row1 = first_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            #first_diff_row2 = first_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            #last_diff_row1 = last_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            #last_diff_row2 = last_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            row1_diff_intervals = get_diff_intervals(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            row2_diff_intervals = get_diff_intervals(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            combined_intervals: List[Tuple[int, int]] = combine_intervals(*row1_diff_intervals, *row2_diff_intervals)
            
            Logger.log(f"combined intervals: {combined_intervals}")
            
            # render
            screen_y = top_row_index // 2
            for interval in combined_intervals:
                # example interval: (17, 29)
                
                for j in range(interval[0], interval[1]-1):
                    # calculate key of color
                    fg_grayscale_value = np.mean(self.pixels[top_row_index,j]) # 0-255
                    bg_grayscale_value = np.mean(self.pixels[top_row_index+1,j]) # 0-255
                    
                    # scale each down to 0-15 (from 0-255)
                    scaled_fg = int(fg_grayscale_value / 255 * 15)
                    scaled_bg = int(bg_grayscale_value / 255 * 15)
                    
                    # combine into 8-bit number
                    color_key = (scaled_fg << 4) + scaled_bg
                    
                    color_key = max(1, color_key) # cant use 0 lol
                    
                    if color_key not in self.initialized_colors:
                        # initialize the color pair
                        fg_1000_based = int(scaled_fg / 15 * 1000)
                        bg_1000_based = int(scaled_bg / 15 * 1000)
                        curses.init_color(scaled_fg << 4, fg_1000_based, fg_1000_based, fg_1000_based)
                        curses.init_color(scaled_bg, bg_1000_based, bg_1000_based, bg_1000_based)
                        Logger.log(f"attempting to init color pair {color_key} with fg {scaled_fg << 4} and bg {scaled_bg}")
                        curses.init_pair(color_key, scaled_fg << 4, scaled_bg)
                        self.initialized_colors.add(color_key)   
                    #string = "▀"                 
                    
                    Logger.log(f"(render) at yx {screen_y}, {j} string of len 1")
                    stuff.screen.addch(screen_y, j, "▀", curses.color_pair(color_key))
            
            #Logger.log(f"[CameraFrame/render]: Appending ({print_start}, {print_end}) to indices_to_print, which currently has {len(indices_to_print)} elements (b4 adding)")
            #indices_to_print.append((print_start, print_end))
        
        Logger.log(f"(render) refreshing curses screen")
        stuff.screen.refresh()
        
        # printing the frame
        # for each pair of rows, convert the pixels from start to end into colored characters, then print.
        """ OLD PRINT-BASED RENDERING
        for i in range(len(indices_to_print)):
            #Logger.log(f"[CameraFrame/render]: row {i} indices to print: {indices_to_print[i]}")
            start, end = indices_to_print[i]
            
            # if both are None, that means the rows were the exact same, so we don't need to print anything
            if start is None and end is None:
                #Logger.log(f"Skipping row {i} since it's the same as the previous row!")
                continue
            
            # converting the two pixel rows into a string
            string = ""
            for j in range(start, end+1):
                string += fco(self.pixels[i*2,j], self.pixels[i*2+1,j]) + '▀' # pixels1 is top, so it gets fg color. pixels2 is bottom, so it gets bg color.
            
            # go to coordinates in terminal, and print the string
            # terminal coordinates: start, i
            
            #Logger.log_on_screen(self.term, f"[CameraFrame/render]: printing@{int(start) + self.pos[0]}, {i + self.pos[1]//2} for len {end-start+1}")
            #Logger.log_on_screen(self.term, f"[CameraFrame/render]: printing@{int(start) + self.pos[0]},{i + self.pos[1]//2}: \x1b[0m[{string}\x1b[0m]")
            print2(self.term.move_xy(int(start)+self.pos[0], i+self.pos[1]//2) + string)
        """

    def render_old(self, prev_frame: "CameraFrame") -> None:
        """ Prints the frame to the screen.
        Optimized by only printing the changes from the previous frame. """
        
        indices_to_print = []
        """ Should end up being a list of tuples (start, end) 
        where start and end are the first and last changed "pixels columns" (characters) in a row. """
        
        # compare the curr frame with the previous frame
        # for each pair of rows, find the first and last changed column
        # multiply term height by 2 since chars are 2 pixels tall
        for top_row_index in range(0, self.height, 2):       
            first_diff_row1 = first_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            first_diff_row2 = first_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            last_diff_row1 = last_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            last_diff_row2 = last_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            print_start = lesser(first_diff_row1, first_diff_row2)
            print_end = greater(last_diff_row1, last_diff_row2)
            
            #Logger.log(f"[CameraFrame/render]: Appending ({print_start}, {print_end}) to indices_to_print, which currently has {len(indices_to_print)} elements (b4 adding)")
            indices_to_print.append((print_start, print_end))
            
        # printing the frame
        # for each pair of rows, convert the pixels from start to end into colored characters, then print.
        for i in range(len(indices_to_print)):
            #Logger.log(f"[CameraFrame/render]: row {i} indices to print: {indices_to_print[i]}")
            start, end = indices_to_print[i]
            
            # if both are None, that means the rows were the exact same, so we don't need to print anything
            if start is None and end is None:
                #Logger.log(f"Skipping row {i} since it's the same as the previous row!")
                continue
            
            # converting the two pixel rows into a string
            string = ""
            for j in range(start, end+1):
                string += fco(self.pixels[i*2,j], self.pixels[i*2+1,j]) + '▀' # pixels1 is top, so it gets fg color. pixels2 is bottom, so it gets bg color.
            
            # go to coordinates in terminal, and print the string
            # terminal coordinates: start, i
            
            #Logger.log_on_screen(stuff.term, f"[CameraFrame/render]: printing@{int(start) + self.pos[0]}, {i + self.pos[1]//2} for len {end-start+1}")
            #Logger.log_on_screen(stuff.term, f"[CameraFrame/render]: printing@{int(start) + self.pos[0]},{i + self.pos[1]//2}: \x1b[0m[{string}\x1b[0m]")
            print2(stuff.term.move_xy(int(start)+self.pos[0], i+self.pos[1]//2) + string)
            
        stuff.screen.refresh()

    def fill(self, color: Tuple[int, int, int]) -> None:
        """ Fills the entire canvas with the given color. RGB (3-tuple) required. Should be pretty efficient because of numpy. """
        assert len(color) == 3, f"[FrameLayer/fill]: color must be an rgb (3 ints) tuple, instead got {color}"
        self.pixels[:,:] = color
        
    def fill_with_gradient(
        self, 
        color1: Tuple[int, int, int], 
        color2: Tuple[int, int, int], 
        direction: Literal["horizontal", "vertical"] = "horizontal"
        ) -> None:
        """ Fills the entire canvas with a gradient from color1 to color2.
        The gradient can be either horizontal or vertical. """
        
        # create a gradient
        if direction == "horizontal":
            gradient = np.linspace(color1, color2, self.width)
            
            # fill each row with the gradient
            for i in range(self.height):
                self.pixels[i] = gradient
            
        elif direction == "vertical":
            gradient = np.linspace(color1, color2, self.height)
            
            for i in range(self.width):
                self.pixels[:,i] = gradient

    Anchor = Literal[
        "top-left", 
        "top-right", 
        "bottom-left", 
        "bottom-right", 
        "center",
        "top",
        "bottom",
        "left",
        "right"
    ]
    def add_rect(
        self, 
        color: Tuple[int, int, int] | Tuple[int, int, int, int], 
        x: int, y: int, 
        width: int, height: int,
        outline_width: int = 0,
        outline_color: Tuple[int, int, int] | Tuple[int, int, int, int] = (0,0,0,0),
        anchor: Anchor = "top-left",
        ) -> None:
        """ Places a rectangle on the frame with the given RGBA color and position.
        Optionally, can add an outline to the rectangle with the given width and color. 
        Can also specify what part of the rectangle x and y refer to. (default is top left)"""

        # add alpha to color/outline if it's an rgb tuple
        
        if color is None:
            return
        
        if len(color) == 3:
            color = (*color, 255)
        if len(outline_color) == 3:
            outline_color = (*outline_color, 255)
            
        x = round(x)
        y = round(y)
        width = round(width)
        height = round(height)
            
        rect_as_pixels = np.full((height+outline_width*2, width+outline_width*2, 4), outline_color, dtype=np.uint8)
        
        # set the middle of rect_as_pixels to the color
        rect_as_pixels[outline_width:outline_width+height, outline_width:outline_width+width] = color
        
        y1 = y - outline_width
        y2 = y + height + outline_width
        x1 = x - outline_width
        x2 = x + width + outline_width
        
        match(anchor):
            case "top-right":
                x1 -= width
                x2 -= width
            case "bottom-left":
                y1 -= height
                y2 -= height
            case "bottom-right":
                x1 -= width
                x2 -= width
                y1 -= height
                y2 -= height
            case "center":
                x1 -= width // 2
                x2 -= width // 2
                y1 -= height // 2
                y2 -= height // 2
            case "top":
                x1 -= width // 2
                x2 -= width // 2
            case "bottom":
                x1 -= width // 2
                x2 -= width // 2
                y1 -= height
                y2 -= height
            case "left":
                y1 -= height // 2
                y2 -= height // 2
            case "right":
                y1 -= height // 2
                y2 -= height // 2
                x1 -= width
                x2 -= width
        
        # if any coords go out of bounds, set it to the edge of the frame and clip the rect_as_pixels
        clipped_y1 = max(0, y1)
        clipped_y2 = min(self.height, y2)
        clipped_x1 = max(0, x1)
        clipped_x2 = min(self.width, x2)
        
        offset_y1 = clipped_y1 - y1
        offset_y2 = clipped_y2 - y2
        offset_x1 = clipped_x1 - x1
        offset_x2 = clipped_x2 - x2
        
        # clip the rect_as_pixels
        clipped_rect_as_pixels = rect_as_pixels[
            int(offset_y1):int(rect_as_pixels.shape[0]-offset_y2), 
            int(offset_x1):int(rect_as_pixels.shape[1]-offset_x2)
        ]
        
        blend_rgba_img_onto_rgb_img_inplace(
            self.pixels[
                clipped_y1:clipped_y2,
                clipped_x1:clipped_x2
            ], clipped_rect_as_pixels
        )
        
    def add_pixels_topleft(self, x: int, y: int, pixels: np.ndarray) -> None:
        """ Same as add_pixels, but with the anchor set to top-left. mainly for optimization. """
        #Logger.log(f"[FrameLayer/add_pixels_topleft]: adding pixels at {x}, {y}, size {pixels.shape}")

        # if x or y are negative, clip them
        clipped_y1 = max(0, y)
        #clipped_y2 = min(self.height, y+pixels.shape[0])
        clipped_x1 = max(0, x)
        #clipped_x2 = min(self.width, x+pixels.shape[1])
        
        # these should always be nonnegative
        offset_x1 = clipped_x1 - x
        #offset_x2 = clipped_x2 - x
        offset_y1 = clipped_y1 - y
        #offset_y2 = clipped_y2 - y
        
        # TODO - this shouldnt happen, but we catch just in case
        if offset_x1 >= pixels.shape[1] or offset_y1 >= pixels.shape[0]:
            #Logger.log(f"[FrameLayer/add_pixels_topleft]: clipped off all pixels, returning")
            return

        blend_rgba_img_onto_rgb_img_inplace(
            self.pixels[int(clipped_y1):int(clipped_y1+pixels.shape[0]-offset_y1), int(clipped_x1):int(clipped_x1+pixels.shape[1]-offset_x1)],
            pixels[int(offset_y1):self.height, int(offset_x1):self.width]
        )
    
    def add_pixels_centered_at(self, x: int, y: int, pixels: np.ndarray) -> None:
        """ Adds a set of pixels to the frame, with the center at the given position. """
        # find the range that would actually be visible
        # find true topleft
        
        pixels_height_1 = pixels.shape[0] // 2
        pixels_height_2 = pixels.shape[0] - pixels_height_1
        pixels_width_1 = pixels.shape[1] // 2
        pixels_width_2 = pixels.shape[1] - pixels_width_1
        
        left = x - pixels_width_1
        top = y - pixels_height_1
        
        clipped_left = int(max(0, left))
        clipped_top = int(max(0, top))
        
        offset_left = int(clipped_left - left)
        offset_top = int(clipped_top - top)
        
        # ignore if fully offscreen
        #if offset_left >= pixels_width_2 or offset_top >= pixels_height_2:
        #    return
        
        #Logger.log(f"[CameraFrame/add_pixels_centered_at]: adding pixels at {x}, {y}, size {pixels.shape}, left={left}, top={top}, clipped_left={clipped_left}, clipped_top={clipped_top}, offset_left={offset_left}, offset_top={offset_top}")
        #Logger.log(f"^^^ Final indices to use: self.pixels[{clipped_top}:{clipped_top+pixels.shape[0]-offset_top}, {clipped_left}:{clipped_left+pixels.shape[1]-offset_left}]")
        #Logger.log(f"^^^ Indices for pixels: pixels[{offset_top}:{pixels.shape[0]}, {offset_left}:{pixels.shape[1]}]")
        
        if clipped_top+pixels.shape[0]-offset_top <= 0: # if the top is offscreen
            return
        
        if clipped_left+pixels.shape[1]-offset_left <= 0: # if the left is offscreen
            return
        
        #Logger.log(f"indices for self.pixels: self.pixels[{clipped_top}:{clipped_top+pixels.shape[0]-offset_top}, {clipped_left}:{clipped_left+pixels.shape[1]-offset_left}]")
        
        blend_rgba_img_onto_rgb_img_inplace(
            self.pixels[clipped_top:int(clipped_top+pixels.shape[0]-offset_top), clipped_left:int(clipped_left+pixels.shape[1]-offset_left)],
            pixels[offset_top:, offset_left:]
        )
    
    def add_line(self, pos1: Tuple[int, int], pos2: Tuple[int, int], color: Tuple[int, int, int]) -> None:
        """ Draws a non-antialiased, 1-wide line between two points on the frame. """
        draw_line(self.pixels, pos1, pos2, color)
    
    def copy(self) -> "CameraFrame":
        """ Returns a deep copy of this CameraFrame. (except for the terminal reference) """
        new_frame = CameraFrame((self.width, self.height), self.pos)
        new_frame.pixels = np.copy(self.pixels)
        return new_frame