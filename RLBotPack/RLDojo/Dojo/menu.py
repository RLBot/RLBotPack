import numpy as np
from enum import Enum
import keyboard

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState
from scenario import Scenario, OffensiveMode, DefensiveMode
import utils

units_x_per_char = 11
units_y_per_line = 40

class UIElement():
    ''' Each element consist of a text and a function to call when the element is clicked '''
    def __init__(self, text, function=None, function_args=None, 
    submenu=None, header=False, display_value_function=None, chooseable=False, spacer=False, 
    submenu_refresh_function=None):
        self.text = text
        self.function = function
        self.function_args = function_args
        self.selected = False
        self.entered = False
        self.submenu = submenu
        self.header = header
        self.display_value_function = display_value_function
        self.chooseable = chooseable
        self.chosen = False
        self.spacer = spacer
        self.submenu_refresh_function = submenu_refresh_function
        
    def get_display_value(self):
        if self.display_value_function:
            return self.display_value_function()
        return None
    
    def back(self):
        self.entered = False
        
    def enter(self):
        self.entered = True
        if self.submenu_refresh_function:
            self.submenu = self.submenu_refresh_function()

        
class MenuRenderer():
    def __init__(self, renderer, columns=1, text_input=False, 
    text_input_callback=None, render_function=None, show_selections=False, disable_menu_render=False):
        self.renderer = renderer
        # Each column has its own list of elements
        self.elements = [[] for _ in range(columns)]
        self.columns = columns
        self.active_column = 0
        # Add scroll offset for each column to handle long lists
        self.scroll_offset = [0 for _ in range(columns)]
        self.is_root = False
        self.is_text_input_menu = text_input
        self.text_input_value = ""
        self.text_input_callback = text_input_callback
        self.show_selections = show_selections
        self.disable_menu_render = disable_menu_render
        
        # Allows for an element to be rendered outside of the menu when selected
        self.render_function = render_function
        
    def add_element(self, element, column=0):
        self.elements[column].append(element)
        
    def handle_text_input(self, key):
        if self.is_text_input_menu:
            self.text_input_value += key
        else:
            for element in self.elements[self.active_column]:
                if element.entered:
                    element.submenu.handle_text_input(key)
                    
    def handle_text_backspace(self):
        if self.is_text_input_menu:
            if len(self.text_input_value) > 0:
                self.text_input_value = self.text_input_value[:-1]
        else:
            for element in self.elements[self.active_column]:
                if element.entered:
                    element.submenu.handle_text_backspace()
    
    def complete_text_input(self):
        print("entering complete text input: ", self.is_text_input_menu)
        if self.is_text_input_menu:
            print("completing text input: ", self.text_input_value)
            if self.text_input_callback:
                self.text_input_callback(self.text_input_value)
            self.text_input_value = ""
            self.is_text_input_menu = False
            self.text_input_callback = None
        else:
            for element in self.elements[self.active_column]:
                if element.entered:
                    element.submenu.complete_text_input()
    
    def _back_deepest_entered_element(self):
        has_entered_element = False
        for column in range(self.columns):
            for element in self.elements[column]:
                if element.entered:
                    has_entered_element = True
                    deepest_element = element.submenu._back_deepest_entered_element()
                    if deepest_element:
                        # Unchoose all of the element's submenu's elements, for all columns
                        for column in range(element.submenu.columns):
                            for submenu_element in element.submenu.elements[column]:
                                submenu_element.chosen = False
                        element.back()
                        return False
        if not has_entered_element:
            return True
        return False

    def _get_max_visible_elements(self):
        """Calculate maximum number of elements that can fit in the menu"""
        MENU_HEIGHT = 500
        available_height = MENU_HEIGHT - 20  # Account for padding
        return available_height // units_y_per_line

    def _ensure_selected_visible(self):
        """Ensure the selected element is visible by adjusting scroll offset"""
        max_visible = self._get_max_visible_elements()
        
        # Find selected element index
        selected_index = -1
        for index, element in enumerate(self.elements[self.active_column]):
            if element.selected:
                selected_index = index
                break
        
        if selected_index == -1:
            return
        
        # Adjust scroll offset to keep selected element visible
        if selected_index < self.scroll_offset[self.active_column]:
            # Selected element is above visible area
            self.scroll_offset[self.active_column] = selected_index
        elif selected_index >= self.scroll_offset[self.active_column] + max_visible:
            # Selected element is below visible area
            self.scroll_offset[self.active_column] = selected_index - max_visible + 1

    def select_next_element(self):
        # If an element is currently entered, call its select_next_element function
        for element in self.elements[self.active_column]:
            if element.entered:
                element.submenu.select_next_element()
                return
        for index, element in enumerate(self.elements[self.active_column]):
            if element.selected:
                element.selected = False
                if index < len(self.elements[self.active_column]) - 1:
                    self.elements[self.active_column][index + 1].selected = True
                else:
                    if not self.elements[self.active_column][0].header:
                        self.elements[self.active_column][0].selected = True
                    else:
                        self.elements[self.active_column][1].selected = True
                break
        self._ensure_selected_visible()

    def select_last_element(self):
        # If an element is currently entered, call its select_last_element function
        for element in self.elements[self.active_column]:
            if element.entered:
                element.submenu.select_last_element()
                return
        for index, element in enumerate(self.elements[self.active_column]):
            if element.selected:
                element.selected = False
                if index > 0:
                    if not self.elements[self.active_column][index - 1].header:
                        self.elements[self.active_column][index - 1].selected = True
                    else:
                        if index == 1:
                            self.elements[self.active_column][len(self.elements[self.active_column]) - 1].selected = True
                        else:
                            self.elements[self.active_column][index - 2].selected = True
                else:
                    self.elements[self.active_column][len(self.elements[self.active_column]) - 1].selected = True
                break
        self._ensure_selected_visible()

    def move_to_next_column(self):
        print("move_to_next_column")
        for column in range(self.columns):
            for element in self.elements[column]:
                if element.entered:
                    element.submenu.move_to_next_column()
                    return
        prev_column = self.active_column
        self.active_column += 1
        if self.active_column >= self.columns:
            self.active_column = 0

        # Update selected element
        for index, element in enumerate(self.elements[prev_column]):
            if element.selected:
                if index < len(self.elements[self.active_column]):
                    self.elements[self.active_column][index].selected = True
                else:
                    self.elements[self.active_column][len(self.elements[self.active_column]) - 1].selected = True
                element.selected = False
                break
        print(self.active_column)

    def move_to_prev_column(self):
        for column in range(self.columns):
            for element in self.elements[column]:
                if element.entered:
                    element.submenu.move_to_prev_column()
                    return
        prev_column = self.active_column
        self.active_column -= 1
        if self.active_column < 0:
            self.active_column = self.columns - 1

        # Update selected element
        for index, element in enumerate(self.elements[prev_column]):
            if element.selected:
                if index < len(self.elements[self.active_column]):
                    self.elements[self.active_column][index].selected = True
                else:
                    self.elements[self.active_column][len(self.elements[self.active_column]) - 1].selected = True
                element.selected = False
                break

    def enter_element(self):
        # If an element is currently entered, call its enter_element function
        for element in self.elements[self.active_column]:
            if element.entered:
                element.submenu.enter_element()
                return
        for element in self.elements[self.active_column]:
            if element.selected:
                if element.function:
                    if element.function_args:
                        element.function(element.function_args)
                    else:
                        element.function()
                if element.submenu:
                    print("entering submenu: ", element.submenu)
                    element.enter()
                elif element.chooseable:
                    element.chosen = True
                    # Unchoose all other elements in the column
                    for other_element in self.elements[self.active_column]:
                        if other_element != element:
                            other_element.chosen = False
                break

    def handle_back_key(self):
        """Handle the 'b' key press to go back in menus"""
        self._back_deepest_entered_element()
        
    def is_in_text_input_mode(self):
        if self.is_text_input_menu:
            return True
        for column in range(self.columns):
            for element in self.elements[column]:
                if element.entered:
                    return element.submenu.is_in_text_input_mode()
        return False
    
    def render_text_input_menu(self, callback):
        # Set current entered menu as a text input menu, recursively finding the deepest entered menu
        for column in range(self.columns):
            for element in self.elements[column]:
                if element.entered:
                    element.submenu.render_text_input_menu(callback)
                    return
        self.text_input_callback = callback
        self.is_text_input_menu = True
        return

    def render_menu(self):
        # If no elements are selected the first time we render the menu, select the first non-header element
        if not any(element.selected for element in self.elements[self.active_column]):
            for element in self.elements[self.active_column]:
                if not element.header:
                    element.selected = True
                    break

        # First, check if any submenu is entered
        for element in self.elements[self.active_column]:
            if element.entered:
                element.submenu.render_menu()
                return

        # If selected element is a spacer, move to the next element
        for element in self.elements[self.active_column]:
            if element.selected:
                if element.spacer:
                    self.select_next_element()
                    return
                else:
                    break
        
        # Ensure selected element is visible
        self._ensure_selected_visible()

        # Draw a rectangle around the menu
        MENU_START_X = 20
        MENU_START_Y = 400
        MENU_WIDTH = 500
        MENU_HEIGHT = 500
        COLUMN_WIDTH = MENU_WIDTH / self.columns
        max_visible_elements = self._get_max_visible_elements()
        
        # If menu renderer is disabled, only render the external function
        if self.disable_menu_render and self.render_function and not self.is_text_input_menu:
            self.render_function()
            return
        
        self.renderer.begin_rendering()
        self.renderer.draw_rect_2d(MENU_START_X, MENU_START_Y, MENU_WIDTH, MENU_HEIGHT, False, self.renderer.black())
        print_x = MENU_START_X + 10
        print_y = MENU_START_Y + 10
        text_color = self.renderer.white()

        # Render the list of options, if this menu isn't a text input
        if not self.is_text_input_menu:
            # If this menu has an external render function, call it in addition to the normal rendering
            if self.render_function:
                self.render_function()
                
            for column in range(self.columns):
                print_x = MENU_START_X + COLUMN_WIDTH * column + 10
                print_y = MENU_START_Y + 10
                
                # Calculate which elements to show based on scroll offset
                start_index = self.scroll_offset[column]
                end_index = min(start_index + max_visible_elements, len(self.elements[column]))
                
                # Render only visible elements
                for i in range(start_index, end_index):
                    element = self.elements[column][i]
                    
                    display_value = element.get_display_value()
                    
                    text = element.text
                    if display_value != None:
                        text += ": " + str(display_value)
                        
                    if element.chosen:
                        text += " [x]"
                    
                    # If header, draw a smaller rectangle
                    if element.header:
                        self.renderer.draw_rect_2d(print_x, print_y - 10, len(element.text) * units_x_per_char, units_y_per_line, False, self.renderer.blue())
                    # If selected, draw a rectangle around the element
                    if element.selected:
                        self.renderer.draw_rect_2d(print_x, print_y - 10, len(text) * units_x_per_char, units_y_per_line, False, self.renderer.white())
                        color = self.renderer.black()
                    else:
                        color = text_color
                    # If header, draw text in green
                    if element.header:
                        self.renderer.draw_string_2d(print_x + 5, print_y, 1, 1, element.text, self.renderer.white())
                    else:
                        self.renderer.draw_string_2d(print_x + 5, print_y, 1, 1, text, color)
                    print_y += units_y_per_line
                
                # Draw scroll indicators if needed
                if len(self.elements[column]) > max_visible_elements:
                    # Draw scroll up indicator
                    if self.scroll_offset[column] > 0:
                        indicator_x = print_x + COLUMN_WIDTH - 30
                        indicator_y = MENU_START_Y + 10
                        self.renderer.draw_string_2d(indicator_x, indicator_y, 1, 1, "↑", self.renderer.white())
                    
                    # Draw scroll down indicator
                    if end_index < len(self.elements[column]):
                        indicator_x = print_x + COLUMN_WIDTH - 30
                        indicator_y = MENU_START_Y + MENU_HEIGHT - 30
                        self.renderer.draw_string_2d(indicator_x, indicator_y, 1, 1, "↓", self.renderer.white())
        else:
            # Prompt user to enter a name for the entity
            self.renderer.draw_string_2d(MENU_START_X + 10, MENU_START_Y + 10, 1, 1, "Enter a name:", self.renderer.white())
            
            # Display user's current input
            self.renderer.draw_string_2d(MENU_START_X + 10, MENU_START_Y + 30, 1, 1, self.text_input_value, self.renderer.white())
            
            # Show a cursor
            self.renderer.draw_rect_2d(MENU_START_X + 10 + len(self.text_input_value) * units_x_per_char, MENU_START_Y + 30, 2, units_y_per_line, False, self.renderer.white())

        instruction_text = "Press 'b' to go back" if not self.is_root else "Press 'm' to exit menu"
        instruction_x = MENU_START_X + (MENU_WIDTH - len(instruction_text) * units_x_per_char) // 2
        instruction_y = MENU_START_Y + MENU_HEIGHT - 30
        self.renderer.draw_string_2d(instruction_x, instruction_y, 1, 1, instruction_text, self.renderer.white())
        
        self.renderer.end_rendering()
