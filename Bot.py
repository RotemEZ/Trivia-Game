import random
from Client_Side import TriviaClient


class BotManager:
    instance = None

    def __init__(self):
        self.existing_bot_numbers = set()
        if not BotManager.instance:
            BotManager.instance = self

    @staticmethod
    def get_instance():
        """
        Returns the singleton instance of BotManager.
        """
        if not BotManager.instance:
            BotManager()
        return BotManager.instance

    def generate_bot_name(self):
        """
        Generate a random number and make sure it's unique
        """
        while True:
            bot_number = random.randint(1, 9999)  # You can adjust the range as needed
            if bot_number not in self.existing_bot_numbers:
                self.existing_bot_numbers.add(bot_number)
                return f"bot{bot_number}"

    def release_bot_name(self, bot_name):
        """
        Remove the bot number from the set when the bot is no longer in use
        """
        try:
            bot_number = int(bot_name.replace("bot", ""))
            self.existing_bot_numbers.discard(bot_number)
        except ValueError:
            # Handle the case where bot_name is not formatted as expected
            pass


class TriviaBot(TriviaClient):
    def __init__(self):
        bot_manager = BotManager.get_instance()
        bot_name = bot_manager.generate_bot_name()
        super().__init__(bot_name)

    def cleanup(self):
        """
        Cleans up and releases the bot name.
        """
        bot_manager = BotManager.get_instance()
        bot_manager.release_bot_name(self.player_name)
        super().cleanup()

    def game_mode(self):
        """
        Starts the bot's game mode, handling questions and sending responses.
        """
        print(f"{self.player_name} started game mode. Waiting for questions...\n")
        loser = 0
        try:
            while True:
                try:
                    message = self.tcp_socket.recv(1024).decode()
                    if message == "":
                        raise Exception
                    if "You have been disqualified(loser!)" in message and not loser:
                        print(message)
                        self.tcp_socket.settimeout(None)
                        loser = 1
                    if 'Congratulations' in message:
                        print(message)
                        break  # Exit the loop and finish the game

                    print(message)
                    if "Here's your question:" in message or "Round" in message:
                        ans = self.generate_random_answer()
                        print(f'Bot {self.player_name} answer: {ans}\n')
                        self.tcp_socket.sendall(ans.encode('utf-8'))
                        # Set timeout as required

                except Exception as e:
                    print("Server crushed, trying to find new server...")
                    self.cleanup()
                    self.run()

        finally:
            self.cleanup()

    def generate_random_answer(self):
        """
        Bot randomly chooses '1' or '0'
        """
        return random.choice(['1', '0'])




