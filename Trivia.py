import socket
import time
from threading import Lock, Event
import select
import struct
from Bot import *
from threading import Thread


class TriviaServer:
    """
    A Trivia Server class that utilizes both UDP and TCP sockets for communication.

    Attributes:
        host (str): The IP address of the server.
        udp_port (int): The UDP port number for broadcasting server offers.
        tcp_port (int): The TCP port number for accepting client connections.
        clients (list): A list to store connected clients (socket, address).
        game_state (str): The state of the game, either 'waiting' or 'game'.
        udp_socket (socket.socket): The UDP socket for broadcasting server offers.
        tcp_socket (socket.socket): The TCP socket for accepting client connections.
        lock (threading.Lock): A lock for thread safety.
    """

    def __init__(self, udp_port=13117):
        self.host = self.get_server_ip()
        self.udp_port = udp_port
        self.tcp_port = self.find_available_port()  # changed because it didn't work normally
        self.clients = []
        self.game_state = 'waiting'
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lock = Lock()
        self.cumulative_true_answers = 0
        self.cumulative_false_answers = 0
        self.current_game_true_answers = 0
        self.current_game_false_answers = 0
        self.start_game_event = Event()
        self.MIN_PLAYERS = 2
        self.player_wins = {}  # Tracks the number of wins per player

        self.questions = [("Does Quentin Tarantino have a cameo in 'Pulp Fiction'?", True),
                ("Is 'Reservoir Dogs' Quentin Tarantino's debut film?", True),
                ("Does 'Kill Bill' feature a black-and-white sequence?", True),
                ("Is 'Once Upon a Time in Hollywood' set in the 1980s?", False),
                ("Does Uma Thurman play the lead role in 'Jackie Brown'?", False),
                ("In 'Django Unchained,' is Dr. King Schultz a bounty hunter?", True),
                ("Is 'The Hateful Eight' primarily set in a saloon?", False),
                ("Does 'Death Proof' feature a serial killer who targets men?", False),
                ("Is 'Inglourious Basterds' centered around the assassination of Hitler?", True),
                ("Does 'Pulp Fiction' win the Academy Award for Best Picture?", False),
                ("In 'Kill Bill,' is the Bride's real name revealed in the first volume?", False),
                ("Does 'Jackie Brown' feature a character named Max Cherry?", True),
                ("In 'Django Unchained,' is the character Django freed at the beginning of the movie?", False),
                ("Is the film 'Reservoir Dogs' entirely set inside a warehouse?", False),
                ("Does 'Once Upon a Time in Hollywood' feature Charles Manson as a main character?", False),
                ("In 'The Hateful Eight,' does the story take place during a blizzard?", True),
                ("Does 'Kill Bill' include a fight scene that lasts more than 10 minutes?", True),
                ("Is 'Inglourious Basterds' a silent film?", False),
                ("Does 'Death Proof' primarily revolve around stunt car driving?", True),
                ("In 'Pulp Fiction,' does Vincent Vega survive the movie?", False)]

        self.player_activity = {}  # Tracks the number of ames each plater has participated in

    def start(self):
        """
        Starts the TriviaServer by launching UDP broadcast and TCP connection acceptance threads.
        """
        flag = 1
        while True:
            if flag:
                flag = 0
                self.tcp_socket.bind((self.host, self.tcp_port))  # Bind to an available port
                self.tcp_socket.listen()
                print(f"Server started, listening on IP address {self.host} on port {self.tcp_port}")

                Thread(target=self.accept_tcp_connections).start()
                Thread(target=self.udp_broadcast).start()

                # Wait for a minimum number of players to connect
                self.start_game_event.wait()


                # Once the minimum number of players have connected, start the game
                self.start_game()
            print(f"Server restarted, listening on IP address {self.host} on port {self.tcp_port}")

            Thread(target=self.accept_tcp_connections).start()
            Thread(target=self.udp_broadcast).start()

            # Wait for a minimum number of players to connect
            self.start_game_event.wait()

            # Once the minimum number of players have connected, start the game
            self.start_game()

    def udp_broadcast(self):
        """
            Broadcasts server offers over UDP to all devices in the network, following the specified packet format.
        """
        magic_cookie = 0xabcddcba
        message_type = 0x2
        server_name = "MysticTriviaServer".ljust(32)  # Ensure the server name is 32 characters

        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        offer_message = struct.pack('!Ib32sH', magic_cookie, message_type, server_name.encode('utf-8'), self.tcp_port)
        while self.game_state == 'waiting':
            self.udp_socket.sendto(offer_message, ('<broadcast>', self.udp_port))
            time.sleep(1)

    def accept_tcp_connections(self):
        """
            Accepts and processes incoming TCP connections.
        """
        while True:
            try:
                client_socket, address = self.tcp_socket.accept()
                self.tcp_socket.settimeout(10)  # Set a 10-second timeout for accept()
                client_socket.setblocking(True)  # Make socket blocking to receive name
                client_name = ''
                while True:
                    char = client_socket.recv(1).decode()  # Corrected to recv(1)
                    if char == '\n':
                        break
                    client_name += char
                client_name = client_name.strip()
                client_socket.setblocking(False)

                with self.lock:
                    self.clients.append((client_socket, address, client_name))
                self.update_player_activity(client_name)
                print(f"New client {address} connected with name: {client_name}")

            except socket.timeout:
                break  # Explicitly breaking is optional, depends on desired flow

        self.tcp_socket.settimeout(None)

        self.start_game_event.set()

    def get_server_ip(self):
        """
        Retrieves the server's IP address by attempting to establish a UDP
        connection with an external address. Falls back to a specified default if
        any issues arise.
        """
        # Set your preferred default IP address here
        default_server_ip = "192.168.1.1"  # Example default IP address
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.4.4", 53))  # Google's public DNS server
                server_ip = sock.getsockname()[0]
        except Exception as ex:
            print(f"\033[31mFailed to get server IP, defaulting to {default_server_ip}. Error: {ex}\033[00m")
            server_ip = default_server_ip
        return server_ip

    def find_available_port(self):
        """
        Searches for an available (free) TCP port within the specified range.
        Defaults to the dynamic and/or private ports range (49152-65535).

        """
        for port in range(49152, 65536):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if sock.connect_ex(('localhost', port)) != 0:  # Port is free if connect_ex returns non-zero
                    return port  # Return the first free port found
        raise Exception("\033[31mFailed to find an available port in the specified range.\033[00m")

    def start_game(self):
        """
         Starts the game with connected clients. Sets the game state to 'game' and plays rounds
         of questions with active clients. Send questions, collects responses, and
         updates clients based on results.
        """
        self.game_state = 'game'
        print("Game starting with connected clients...")
        active_clients = [client_socket for client_socket, _, name in self.clients]
        client_names = {client_socket: name for client_socket, _, name in self.clients}

        if len(active_clients) == 1:
            cancellation_message = "\033[34mYou are the only registered player, the game is over.\033[00m"
            print(cancellation_message)
            for client_socket in active_clients:
                try:
                    client_socket.sendall(cancellation_message.encode())
                except Exception as e:
                    print(f"\033[31mError sending to client: {e}\033[00m")
            self.stop_game()
            return

        flag = False
        round_num = 1
        while len(active_clients) > 1:
            if flag:
                names = ""
                last = 0
                for name in client_names.values():
                    if last == 0:
                        names += f"{name}"
                        last += 1
                    elif last == len(client_names.values()) - 1:
                        names += f" and {name}"
                    else:
                        names += f", {name}"
                        last += 1
                question_text, correct_answer = self.pick_question()
                welcome_message = f"\n\033[35mRound {round_num}, played by {names}:\n{question_text}\033[00m\n"
            else:
                question_text, correct_answer = self.pick_question()
                flag = True
                welcome_message = f"\033[35mWelcome to the Trivia Contest!\nHere's your question:\n{question_text}\033[00m\n"
            print(welcome_message)

            # Send question to all active clients
            with self.lock:
                self.send_message_to_all(welcome_message, active_clients)

            # Collect responses
            responses = self.collect_responses(active_clients)

            # Determine round results
            correct_responses, incorrect_responses, no_responses = self.determine_round_results(responses, correct_answer, client_names)
            # Update active clients based on round result
            active_clients = self.update_active_clients(correct_responses, incorrect_responses, no_responses, active_clients, client_names)
            client_names = {client_socket: name for client_socket, _, name in self.clients if
                            client_socket in active_clients}

            # Handling for no correct responses or more than one correct response
            if not correct_responses or len(correct_responses) > 1:
                round_num += 1
                print("\033[35mMoving to the next round with another question...\033[00m\n")
                continue

            # Handling for exactly one winner
        self.announce_winner_and_cleanup(correct_responses[0], client_names)

    def send_message_to_all(self, message, active_clients):
        """
        Sends a message to all active clients. Use threads to send the given message to each client
        in `active_clients`. Handles any errors during sending and removes problematic clients.
        """
        def send_message(client_socket):
            try:
                client_socket.sendall(message.encode())
            except Exception as e:
                print(f"\033[31mError sending to client: {e}\033[00m")
                with self.lock:
                    active_clients.remove(client_socket)

        threads = []
        for client_socket in active_clients:
            thread = Thread(target=send_message, args=(client_socket,))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()  # Optionally wait for all threads to complete

    def collect_responses(self, active_clients):
        """
        Collects responses from active clients within a 10-second time limit.
        """
        responses = {client_socket: None for client_socket in active_clients}  # Initialize all responses to None
        start_time = time.time()

        while time.time() - start_time < 10:
            time_left = 10 - (time.time() - start_time)
            readable, _, _ = select.select(active_clients, [], [], time_left)

            for client_socket in readable:
                data = client_socket.recv(1024).strip()
                responses[client_socket] = data.decode()  # Store the response

            if all(response is not None for response in responses.values()):
                # All clients have responded, now wait for the remaining time to finish 10 seconds
                time.sleep(time_left)
                break

        return responses

    def determine_round_results(self, responses, correct_answer, client_names):
        """
         Determines the results of a round based on client responses.
        """
        correct_responses = []
        incorrect_responses = []
        no_response_clients = []

        # Normalize the correct answer to '1' or '0'
        normalized_correct_answer = '1' if correct_answer else '0'

        for client_socket, response in responses.items():
            if response is None:
                no_response_clients.append(client_socket)
                print(f"\033[93m{client_names[client_socket]} did not answer.\033[00m")
            else:
                # Normalize the response to '1' or '0'
                normalized_response = self.normalize_response(response)

                if normalized_response == normalized_correct_answer:
                    correct_responses.append(client_socket)
                    print(f"\033[32m{client_names[client_socket]} is correct!\033[00m")
                elif normalized_response is None:
                    # Handle None normalized responses as incorrect (invalid input)
                    incorrect_responses.append(client_socket)
                    print(f"\033[93m{client_names[client_socket]} provided an invalid response.\033[00m")
                else:
                    incorrect_responses.append(client_socket)
                    print(f"\033[93m{client_names[client_socket]} is incorrect!\033[00m")

        return correct_responses, incorrect_responses, no_response_clients

    def normalize_response(self, response):
        """
        Normalizes a client's response to '1' or '0' (yes or no).

        """
        if response.upper() in ['Y', 'T', '1']:
            return '1'
        elif response.upper() in ['N', 'F', '0']:
            return '0'
        else:
            return None  # Consider an invalid response as incorrect

    def update_active_clients(self, correct_responses, incorrect_responses, no_response_clients, active_clients, client_names):
        """
        Updates the list of active clients based on round results.

        """
        # If no correct responses, all players proceed to the next round
        if not correct_responses:
            print("\033[35mNo correct answers, all players proceed to the next round.\033[00m")
            return active_clients  # No change in active clients

        def disqualify_client(client_socket, message):
            try:
                client_socket.sendall(message.encode())
            except Exception as e:
                print(f"\033[31mError sending to client: {e}\033[00m")

        threads = []
        message = "You have been disqualified (loser)\n"
        for client_socket in incorrect_responses + no_response_clients:
            client_name = client_names[client_socket]
            print(f"\033[35m{client_name} is disqualified.\033[00m")
            thread = Thread(target=disqualify_client, args=(client_socket, message))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        updated_active_clients = [client_socket for client_socket in correct_responses if client_socket in active_clients]

        # Log updates
        if len(updated_active_clients) != 1:
            for client_socket in updated_active_clients:
                client_name = client_names[client_socket]
                print(f"\033[35m{client_name} proceeds to the next round.\033[00m")
        return updated_active_clients

    def update_player_activity(self, client_name):
        """
        Updates the activity count for a client.

        """
        # Increment the count of games this player has participated in
        if client_name in self.player_activity:
            self.player_activity[client_name] += 1
        else:
            self.player_activity[client_name] = 1

    def send_most_active_players_stats(self):
        """
        Sends stats of the most active players.
        """
        # Determine the maximum number of games played
        if not self.player_activity:
            most_games = 0
        else:
            most_games = max(self.player_activity.values())

        # Collect all players who have played the maximum number of games
        most_active_players = [name for name, games in self.player_activity.items() if games == most_games]

        # Format the message based on the number of top players
        if len(most_active_players) > 1:
            most_active_message = f"Most active players each with {most_games} games: " + ", ".join(most_active_players) + " (nerds)\n"
        else:
            most_active_message = f"Most active player: {most_active_players[0]} with {most_games} games (nerd).\n"

        print(most_active_message)  # Server-side log
        return most_active_message

    def update_player_wins(self, winner_name):
        """
        Updates the win count for a player.

        """
        if winner_name in self.player_wins:
            self.player_wins[winner_name] += 1
        else:
            self.player_wins[winner_name] = 1

    def send_most_wins_stats(self):
        """
        Sends stats of players with the most wins.
        """
        if not self.player_wins:
            print("No games have been won yet")

        # Find the maximum number of wins and who achieved it
        max_wins = max(self.player_wins.values())
        top_winners = [name for name, wins in self.player_wins.items() if wins == max_wins]

        # Format the message based on the number of top winners
        if len(top_winners) > 1:
            top_winners_message = f"Top winners, each with {max_wins} wins: " + ", ".join(top_winners) + "\n"
        else:
            top_winners_message = f"Top winner: {top_winners[0]} with {max_wins} wins.\n"
        print(top_winners_message)
        return top_winners_message

    def display_true_false_rate(self):
        """
        Calculate and display statistics after a game.
        """
        total_questions = self.cumulative_true_answers + self.cumulative_false_answers
        current_game_total = self.current_game_true_answers + self.current_game_false_answers

        if total_questions > 0:  # Avoid division by zero
            cumulative_true_pct = self.cumulative_true_answers / total_questions
            cumulative_false_pct = self.cumulative_false_answers / total_questions
        else:
            cumulative_true_pct = cumulative_false_pct = 0

        if current_game_total > 0:
            current_game_true_pct = self.current_game_true_answers / current_game_total
            current_game_false_pct = self.current_game_false_answers / current_game_total
        else:
            current_game_true_pct = current_game_false_pct = 0

        # Print statistics in a table format
        print("+--------------------------------+")
        print("| Statistic                | Value |")
        print("+--------------------------------+")
        print(f"| Cumulative True Answers   | {cumulative_true_pct:.2%} |")
        print(f"| Cumulative False Answers  | {cumulative_false_pct:.2%} |")
        print("+--------------------------------+")
        print(f"| Current Game True Answers | {current_game_true_pct:.2%} |")
        print(f"| Current Game False Answers| {current_game_false_pct:.2%} |")
        print("+--------------------------------+")

        # Reset current game statistics
        self.current_game_true_answers = 0
        self.current_game_false_answers = 0

        # Return the statistics as a string
        return (f"Cumulative True Answers: {cumulative_true_pct:.2%}\n"
                f"Cumulative False Answers: {cumulative_false_pct:.2%}\n"
                f"Current Game True Answers: {current_game_true_pct:.2%}\n"
                f"Current Game False Answers: {current_game_false_pct:.2%}")

    def announce_winner_and_cleanup(self, winner_socket, client_names):
        """
        Announces the winner and performs cleanup. Congratulates the winner and updates player wins.
        Sends a game-over message with stats to all clients using threads, then stops the game.
        """
        winner_name = client_names[winner_socket]
        winner_message = f"\033[34mCongratulations to {winner_name}, the winner of this game!\033[00m\n"
        print(winner_message)
        self.update_player_wins(winner_name)

        game_over_message = (f"\033[34mGame over!\nCongratulations to the winner: {winner_name}\033[00m\n" +
                             "\n" + self.send_most_active_players_stats() + '\n' +
                             self.send_most_wins_stats() + '\n' + self.display_true_false_rate())

        threads = []
        with self.lock:
            for client_socket, _, _ in self.clients:
                thread = Thread(target=self.send_game_over_message, args=(client_socket, game_over_message))
                thread.start()
                threads.append(thread)

        for thread in threads:
            thread.join()

        self.stop_game()

    def send_game_over_message(self, client_socket, message):
        """
        Sends a game-over message to a client.
        Tries to send the given message to the client's socket. Logs an error if sending fails.
        """
        try:
            client_socket.sendall(message.encode())
        except Exception as e:
            print(f"\033[31mError sending summary to client: {e}\033[00m")

    def stop_game(self):
        """
        Handles the end-of-game tasks: closing client connections, announcing the game's conclusion,
        and resetting the server state to begin sending out offer messages again.
        """
        # Close all client connections
        with self.lock:
            for client_socket, _, __ in self.clients:
                try:
                    client_socket.close()  # Attempt to close each connection gracefully
                except Exception as e:
                    print(f"\033[31mError closing client socket: {e}\033[00m")
            self.clients.clear()  # Clear the list of clients for the next game

        # Announce game over and that the server will resume sending out offers
        print("Game over, sending out offer requests...")

        # Reset the game state and clear any events if necessary
        self.game_state = 'waiting'

        self.start_game_event.clear()  # Reset the event for the next game cycle

    def pick_question(self):
        """
        Randomly selects a trivia question from the list.
        """
        question, answer = random.choice(self.questions)
        # Update cumulative and current game statistics
        if answer:
            self.cumulative_true_answers += 1
            self.current_game_true_answers += 1
        else:
            self.cumulative_false_answers += 1
            self.current_game_false_answers += 1
        return question, answer


if __name__ == '__main__':
    server = TriviaServer()
    try:
        # Start the server
        server.start()
    except KeyboardInterrupt:
        # Stop the server if interrupted by Ctrl+C
        server.stop_game()
