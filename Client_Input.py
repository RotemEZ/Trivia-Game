import tkinter as tk
from tkinter import simpledialog


class Client_Input:
    def __init__(self):
        self.main_window = tk.Tk()
        self.main_window.withdraw()  # Main window is hidden.
        self.user_input = None
        self.timer_id = None

    def execute(self):
        """
        Prompts the user for input with a 10-second timeout. Shows a dialog for the user to enter
        an answer and sets `user_input` based on the response. Cancels the timeout if input is received.

        """
        self.timer_id = self.main_window.after(10000, self.handle_timeout)
        user_response = simpledialog.askstring("Input", "Enter your answer (True/False):", parent=self.main_window)

        if self.timer_id:
            self.main_window.after_cancel(self.timer_id)
            self.timer_id = None

        if user_response:
            self.user_input = user_response

        self.terminate()
        return self.user_input

    def handle_timeout(self):
        """
        Handles timeout for user input. Sets `user_input` to None and terminates the session if no
        input is received within the timeout.
        """
        try:
            if self.main_window.winfo_exists():
                self.user_input = None  # Indicates absence of input
                self.terminate()
        except tk.TclError:
            print("Window session ended.")  # User-friendly message

    def terminate(self):
        """
        Terminates the session. Cancels any remaining timers and closes the main window if it exists.
        """
        if self.timer_id:
            self.main_window.after_cancel(self.timer_id)
            self.timer_id = None
        try:
            if self.main_window.winfo_exists():
                self.main_window.destroy()
        except tk.TclError:
            pass  # Exception ignored as the window is already closed


if __name__ == "__main__":
    dialog = Client_Input()
    result = dialog.execute()
    print(f"Received input: {result}")