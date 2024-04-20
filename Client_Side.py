import socket
import struct
from Client_Input import Client_Input


class TriviaClient:
    def __init__(self, player_name):
        self.player_name = player_name
        self.udp_port = 13117
        self.tcp_socket = None

    def run(self):
        """
        Listens for server offers and connects to the server, then starts game mode.

        """
        server_ip, server_port = self.listen_for_offers()  # blocking
        if self.connect_to_server(server_ip, server_port):
            self.game_mode()

    def listen_for_offers(self):
        """
         Listens for UDP offers from the server and returns server IP and port.

        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp_socket.bind(("", self.udp_port))
            print("Client started, listening for offer requests...")
            while True:
                data, addr = udp_socket.recvfrom(1024)  # blocking operation; addr is a (host, udp port) tuple
                magic_cookie, message_type, server_name, server_port = struct.unpack('!Ib32sH', data)
                if magic_cookie == 0xabcddcba and message_type == 0x2:
                    print(f"Received offer from server: {addr},server port:{server_port} , attempting to connect...")
                    return addr[0], server_port

    def connect_to_server(self, server_ip, server_port):
        """
        Establishes a TCP connection with the server using IP and port.

        """
        try:
            # Create a new socket for the TCP connection
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Optionally, set a timeout for the connection attempt to prevent hanging indefinitely
            self.tcp_socket.settimeout(10)

            # Attempt to establish a TCP connection to the server
            self.tcp_socket.connect((server_ip, server_port))  # blocking operation

            # Send the player's name followed by a newline character to the server
            self.tcp_socket.sendall(f"{self.player_name}\n".encode())

            # Reset the timeout to None (blocking mode) or another value, as needed for the game_mode logic
            self.tcp_socket.settimeout(None)

            # If reached here, the connection and initial data send were successful
            print("Connected to the server successfully.\n")
            return True
        except socket.timeout:
            # Handle a timeout during the connection attempt
            print("Connection attempt timed out. The server might be busy or offline.")
        except ConnectionRefusedError:
            # Handle the server refusing the connection
            print(
                f"Connection refused by the server. The server might be down or not accepting connections at this time.")
        except socket.error as err:
            # Handle other socket-related errors
            print(f"\033[31mSocket error occurred: {err}\033[00m")
        except Exception as e:
            # Handle any other exceptions that were not caught by the specific error handlers above
            print(f"\033[31mAn unexpected error occurred while trying to connect to the server: {e}\033[00m")

        # Close the socket if it exists and clear the reference to it
        self.cleanup()
        return False  # Indicate that the connection attempt was unsuccessful

    def cleanup(self):
        """
        Cleans up resources, like closing the TCP socket.
        """
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except Exception as e:
                print(f"\033[31mError closing socket: {e}\033[00m")
            self.tcp_socket = None

    def game_mode(self):
        """
         Manages game mode, receiving and sending messages from/to the server.
        """
        print("Game mode started. Waiting for questions...\n")
        loser = 0
        try:
            while True:
                try:
                    message = self.tcp_socket.recv(1024).decode()
                    if message == "":
                        raise Exception
                    if 'You have been disqualified(loser!)' in message and not loser:
                        self.tcp_socket.settimeout(None)
                        loser = 1
                    if 'Congratulations' in message or "You are the only registered player, the game is over." in message:
                        print(message)

                        break  # Exit the loop and finish the game

                    print(message)
                    if "Here's your question:" in message or "Round" in message:
                        client_input = Client_Input()
                        ans = client_input.execute()
                        if ans is not None:
                            print(f'Your answer: {ans}\n')
                            self.tcp_socket.sendall(ans.encode('utf-8'))
                        else:
                            print("\033[31mTime's up! No response provided.\033[00m")

                except Exception as e:
                    print("Server crushed, trying to find new server...")
                    self.cleanup()
                    self.run()

        finally:
            # Ensure the socket is closed when leaving game mode
            self.cleanup()
