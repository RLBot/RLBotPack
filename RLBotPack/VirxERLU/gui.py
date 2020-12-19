from os import path
from threading import Thread
from tkinter import HORIZONTAL, BooleanVar, PhotoImage, StringVar, Tk, ttk
from traceback import print_exc


class Gui(Thread):
    def __init__(self, agent):
        super().__init__(daemon=True)
        self.agent = agent

    def run(self):
        root = Tk()

        icon_path = path.join(path.dirname(path.abspath(__file__)), "./logo.png")
        root.iconphoto(True, PhotoImage(file=icon_path))

        root.title("VirxEC/VirxERLU")

        root.geometry("255x250")

        title = ttk.Label(root, text=f"{self.agent.name} hosted by VirxERLU")
        title.pack()

        author = ttk.Label(root, text=f"Bot by BotMaker (BotMaker/githubRepo)")
        author.pack()

        # Disable driving

        drive_bool = BooleanVar()
        drive_bool.set(self.agent.disable_driving)

        def set_drive():
            self.agent.disable_driving = drive_bool.get()

        drive_btn = ttk.Checkbutton(root, text='Disable driving', variable=drive_bool, command=set_drive)
        drive_btn.pack()

        # Debugging

        debug_bool = BooleanVar()
        debug_bool.set(self.agent.debugging)

        def set_debug():
            self.agent.debugging = debug_bool.get()

        debug_btn = ttk.Checkbutton(root, text='Debugging', variable=debug_bool, command=set_debug)
        debug_btn.pack()

        # Debug 2D

        debug_2d_bool = BooleanVar()
        debug_2d_bool.set(self.agent.debug_2d_bool)

        def set_debug_2d():
            self.agent.debug_2d_bool = debug_2d_bool.get()

        debug_2d = ttk.Checkbutton(root, text='Debug 2D', variable=debug_2d_bool, command=set_debug_2d)
        debug_2d.pack()

        # Location

        show_coords_bool = BooleanVar()
        show_coords_bool.set(self.agent.show_coords)

        def set_show_coords():
            self.agent.show_coords = show_coords_bool.get()

        show_coords_btn = ttk.Checkbutton(root, text='Show Car Info (2D/Lines)', variable=show_coords_bool, command=set_show_coords)
        show_coords_btn.pack()

        # Debug 3D

        debug_3d_bool = BooleanVar()
        debug_3d_bool.set(self.agent.debug_3d_bool)

        def set_debug_3d():
            self.agent.debug_3d = debug_3d_bool.get()

        debug_3d = ttk.Checkbutton(root, text='Debug 3D', variable=debug_3d_bool, command=set_debug_3d)
        debug_3d.pack()

        # Debug Stack

        debug_stack_bool = BooleanVar()
        debug_stack_bool.set(self.agent.debug_stack_bool)

        def set_debug_stack():
            self.agent.debug_stack_bool = debug_stack_bool.get()

        debug_stack = ttk.Checkbutton(root, text='Debug Stack (3D)', variable=debug_stack_bool, command=set_debug_stack)
        debug_stack.pack()

        # Debug Lines

        debug_lines_bool = BooleanVar()
        debug_lines_bool.set(self.agent.debug_lines)

        def set_debug_lines():
            self.agent.debug_lines = debug_lines_bool.get()

        debug_lines = ttk.Checkbutton(root, text='Debug Lines', variable=debug_lines_bool, command=set_debug_lines)
        debug_lines.pack()

        # Debug ball prediction

        debug_ball_path_bool = BooleanVar()
        debug_ball_path_bool.set(self.agent.debug_ball_path)

        def set_debug_ball_path():
            self.agent.debug_ball_path = debug_ball_path_bool.get()

        debug_ball_path = ttk.Checkbutton(root, text='Debug Ball Path (Lines)', variable=debug_ball_path_bool, command=set_debug_ball_path)
        debug_ball_path.pack()

        # Debug ball prediction precision

        debug_ball_path_precision_str = StringVar()
        debug_ball_path_precision_str.set("Precision: " + str(self.agent.debug_ball_path_precision))
        debug_ball_path_precision_label = ttk.Label(root, textvariable=debug_ball_path_precision_str)
        debug_ball_path_precision_label.pack()

        def set_debug_ball_path_precision(value):
            value = round(float(value))
            self.agent.debug_ball_path_precision = value
            debug_ball_path_precision_str.set("Precision: " + str(value))

        debug_ball_path_precision = ttk.Scale(root, orient=HORIZONTAL, from_=2, to=20, command=set_debug_ball_path_precision)
        debug_ball_path_precision.set(self.agent.debug_ball_path_precision)
        debug_ball_path_precision.pack()

        self.stop = root.destroy

        try:
            root.mainloop()
        except Exception:
            print_exc()
