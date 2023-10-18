from rlbot.botmanager.agent_metadata import AgentMetadata
from rlbot.botmanager.bot_helper_process import BotHelperProcess
from rlbot.utils.logging_utils import get_logger

from pathlib import Path
from multiprocessing import shared_memory
import tkinter as tk
from tkinter import ttk


class Nexto_EZ_GUI(BotHelperProcess):

    exec_path = None

    def __init__(self, agent_metadata_queue, quit_event, options):
        super().__init__(agent_metadata_queue, quit_event, options)

        self.logger = get_logger("nexto-ez")
        self.bots = [ [], [] ]

    def try_receive_agent_metadata(self):
        while not self.metadata_queue.empty():
            metadata: AgentMetadata = self.metadata_queue.get(timeout=1.0)
            self.bots[metadata.team].append(metadata)
        for botTeamList in self.bots:
            botTeamList.sort(key=lambda m: m.index)

    def start(self):
        """Starts the BotHelperProcess."""

        self.try_receive_agent_metadata()
        self.logger.info(f"found {len(self.bots)} nexto-ez bots")

        self.init_gui()


    def init_gui(self):
        root = tk.Tk()
        root.minsize(width=350, height=50)
        root.resizable(False, False)
        root.title('Nexto-EZ')
        root.iconbitmap(str(Path(__file__).parent / "nexto_logo.ico"))


        root.columnconfigure(0, weight=3)
        root.columnconfigure(1, weight=2)
        root.columnconfigure(2, weight=25)



        ttk.Label(
            root,
            text='Bots:'
        ).grid(
            column=0,
            row=0,
            ipadx=3,
            sticky='s'
        )

        ttk.Label(
            root,
            text='Dumb as\na rock'
        ).grid(
            column=2,
            row=0,
            ipadx=3,
            sticky='sw'
        )
        ttk.Label(
            root,
            text='Nexto'
        ).grid(
            column=2,
            row=0,
            ipadx=3,
            sticky='se'
        )

        class Scale(ttk.Scale):
            """a type of Scale where the left click is hijacked to work like a right click"""
            def __init__(self, master=None, **kwargs):
                ttk.Scale.__init__(self, master, **kwargs)
                self.bind('<Button-1>', self.set_value)

            def set_value(self, event):
                self.event_generate('<Button-3>', x=event.x, y=event.y)
                return 'break'

        self.row_i = 1

        def add_bot_slider(metadata):
            memory = shared_memory.SharedMemory(metadata.helper_process_request.options["shared_memory_name"])

            def format_value(val):
                return '{: .0f}%'.format(val * 100)

            # label for the slider
            ttk.Label(
                root,
                text=f"{metadata.name}:",
                foreground="orange" if metadata.team else "blue",
            ).grid(
                column=0,
                row=self.row_i,
                sticky='e'
            )

            # percentage label
            value_label = ttk.Label(
                root,
                text=format_value(memory.buf[0] / 255),
            )
            value_label.grid(
                column=1,
                row=self.row_i,
            )

            def update_slider(val):
                nonlocal memory
                nonlocal value_label
                val = float(val)
                memory.buf[0] = int(round((1 - val) * 255))
                value_label.configure(text=format_value(val))

            #  slider
            Scale(
                root,
                from_=0,
                to=1,
                value=memory.buf[0] / 255,
                orient='horizontal',
                command=lambda val: update_slider(val),
            ).grid(
                column=2,
                row=self.row_i,
                sticky='we'
            )
            self.row_i += 1

        for botTeamList in self.bots:
            for metadata in botTeamList:
                add_bot_slider(metadata)

        root.mainloop()

