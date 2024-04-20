# Trivia-Game

This repository contains a trivia game system implemented in Python. The system includes both a server (Server) and a client (TriviaClient), which communicate over a network using UDP for broadcasting offers and TCP for game communication. The game supports multiple clients simultaneously through a thread-based approach.

## Features

- *Server-side Trivia Management*: The server manages trivia sessions, accepts connections, broadcasts offers, and handles game logic.
- *Client Interaction*: Clients listen for server offers and participate in trivia games by answering questions provided by the server.
- *Dynamic IP and Port Handling*: The server can automatically pick its IP and an available TCP port.
- *Multi-threaded Architecture*: Both server and client utilize multiple threads to handle networking and user interaction concurrently.

## Getting Started

### Running the Server

To start the server, navigate to the server directory and run:

python Trivia.py

This will start the trivia server, which will begin listening for incoming client connections and broadcasting offers via UDP.

### Running the Client

To connect a client to the server, create an instance and invoke the "run" function. You need to provide a player name when prompted.

### Using Bots

Bots can join games and answer trivia questions. To run a bot, create and invoke the "run" function:

## Files Description

- Trivia.py: Contains the server logic for handling trivia games.
- Client_Side.py: Client-side logic for participating in games.
- Client_Input.py: creates a graphical user interface for collecting user input.
- Bot.py: Script for automated bots that can join and play trivia games.
- There are python files which represent instances of clients and bots.



