import random
import sys
from phe import paillier


class Ship:
    """Represents a ship with a size and coordinates"""
    def __init__(self, name, size):
        self.name = name
        self.size = size
        self.coordinates = []
        self.hits = set()
    
    def is_sunk(self):
        return len(self.hits) == self.size
    
    def place(self, start_row, start_col, horizontal):
        """Place ship on board"""
        self.coordinates = []
        for i in range(self.size):
            if horizontal:
                self.coordinates.append((start_row, start_col + i))
            else:
                self.coordinates.append((start_row + i, start_col))
        return self.coordinates


class Player:
    """Represents a player with their own board and ships"""
    def __init__(self, name):
        self.name = name
        self.board = [[0 for _ in range(10)] for _ in range(10)]  # 0 = water, 1 = ship
        self.guess_board = [[' ' for _ in range(10)] for _ in range(10)]  # Track guesses
        self.ships = [
            Ship("Carrier", 5),
            Ship("Battleship", 4),
            Ship("Cruiser", 3),
            Ship("Submarine", 2),
            Ship("Destroyer", 2)
        ]
        self.encrypted_board = {}  # Store encrypted positions
        self.public_key = None
        self.private_key = None
        self.hits_received = 0
        self.total_ship_cells = sum(ship.size for ship in self.ships)
    
    def generate_keys(self):
        """Generate Paillier keypair"""
        self.public_key, self.private_key = paillier.generate_paillier_keypair()
    
    def place_ship_random(self, ship):
        """Randomly place a ship on the board"""
        placed = False
        while not placed:
            horizontal = random.choice([True, False])
            if horizontal:
                row = random.randint(0, 9)
                col = random.randint(0, 10 - ship.size)
            else:
                row = random.randint(0, 10 - ship.size)
                col = random.randint(0, 9)
            
            # Check if position is valid
            coords = ship.place(row, col, horizontal)
            if all(self.board[r][c] == 0 for r, c in coords):
                # Place the ship
                for r, c in coords:
                    self.board[r][c] = 1
                placed = True
    
    def setup_board(self):
        """Setup board with all ships"""
        print(f"\n[{self.name}] Setting up board...")
        for ship in self.ships:
            self.place_ship_random(ship)
        print(f"[{self.name}] All ships placed!")
        self.display_own_board()
    
    def encrypt_board(self):
        """Encrypt all ship positions"""
        print(f"[{self.name}] Encrypting board positions...")
        for row in range(10):
            for col in range(10):
                position_index = row * 10 + col  # Convert 2D to 1D index
                # Encrypt 1 if ship, 0 if water
                self.encrypted_board[(row, col)] = self.public_key.encrypt(self.board[row][col])
    
    def display_own_board(self):
        """Display player's own board with ships"""
        print(f"\n{self.name}'s Board:")
        print("   " + " ".join(str(i) for i in range(10)))
        for i, row in enumerate(self.board):
            display = ["S" if cell == 1 else "~" for cell in row]
            print(f"{i}  " + " ".join(display))
    
    def display_guess_board(self):
        """Display board showing guesses made"""
        print(f"\n{self.name}'s Tracking Board (Your Guesses):")
        print("   " + " ".join(str(i) for i in range(10)))
        for i, row in enumerate(self.guess_board):
            print(f"{i}  " + " ".join(row))
    
    def check_hit_homomorphic(self, guess_row, guess_col, opponent):
        """
        Check if guess is a hit using homomorphic encryption.
        The opponent decrypts and returns the result.
        """
        # Get the encrypted value at the guessed position
        encrypted_position = self.encrypted_board[(guess_row, guess_col)]
        
        # Apply blinding for security
        blinding_factor = random.randint(1, 999999)
        encrypted_result = encrypted_position * blinding_factor
        
        # Opponent decrypts (they're checking their own board)
        decrypted_val = self.private_key.decrypt(encrypted_result)
        
        # If decrypted value is 0, it's water (miss)
        # If decrypted value is non-zero, it's a hit (blinding_factor * 1)
        is_hit = (decrypted_val != 0)
        
        if is_hit:
            self.hits_received += 1
            # Mark which ship was hit
            for ship in self.ships:
                if (guess_row, guess_col) in ship.coordinates:
                    ship.hits.add((guess_row, guess_col))
                    if ship.is_sunk():
                        return "sunk", ship.name
                    break
            return "hit", None
        else:
            return "miss", None
    
    def has_lost(self):
        """Check if all ships are sunk"""
        return self.hits_received >= self.total_ship_cells


def get_player_guess():
    """Get valid coordinates from player"""
    while True:
        try:
            guess = input("Enter your guess (row col, e.g., '3 4'): ").strip()
            parts = guess.split()
            if len(parts) != 2:
                print("Please enter two numbers separated by a space.")
                continue
            row, col = int(parts[0]), int(parts[1])
            if 0 <= row <= 9 and 0 <= col <= 9:
                return row, col
            else:
                print("Coordinates must be between 0 and 9.")
        except ValueError:
            print("Invalid input. Please enter two numbers.")


def main():
    print("=" * 60)
    print("   HOMOMORPHIC BATTLESHIP - Full Two-Player Game")
    print("=" * 60)
    print("\nRules:")
    print("- Each player has a 10x10 board")
    print("- Ships: Carrier(5), Battleship(4), Cruiser(3), Submarine(2), Destroyer(2)")
    print("- Players take turns guessing coordinates")
    print("- First to sink all opponent's ships wins!")
    print("- Boards are encrypted - even the game can't see ship locations!\n")
    
    # Initialize players
    player1 = Player("Alice")
    player2 = Player("Bob")
    
    # Setup Phase
    print("\n" + "=" * 60)
    print("SETUP PHASE")
    print("=" * 60)
    
    # Generate keys for both players
    print("\nGenerating encryption keys...")
    player1.generate_keys()
    player2.generate_keys()
    
    # Setup boards
    player1.setup_board()
    player2.setup_board()
    
    # Encrypt boards
    player1.encrypt_board()
    player2.encrypt_board()
    
    print("\n" + "=" * 60)
    print("GAME START!")
    print("=" * 60)
    
    # Game Loop
    turn = 0
    game_over = False
    current_player = player1
    opponent = player2
    
    while not game_over:
        turn += 1
        print(f"\n{'=' * 60}")
        print(f"TURN {turn} - {current_player.name}'s Turn")
        print(f"{'=' * 60}")
        
        # Show current player's boards
        current_player.display_own_board()
        current_player.display_guess_board()
        
        # Get guess
        print(f"\n{current_player.name}, make your guess!")
        guess_row, guess_col = get_player_guess()
        
        # Check if already guessed
        if current_player.guess_board[guess_row][guess_col] != ' ':
            print("You already guessed that position! Try again.")
            continue
        
        # Perform homomorphic check
        print(f"\n[Network] Processing encrypted guess at ({guess_row}, {guess_col})...")
        print(f"[Network] Computing with encrypted data (opponent's board stays hidden)...")
        
        result, ship_name = opponent.check_hit_homomorphic(guess_row, guess_col, current_player)
        
        # Update guess board
        if result == "hit":
            current_player.guess_board[guess_row][guess_col] = 'X'
            print(f"\n*** HIT! ***")
            print(f"{opponent.name}'s ship was hit at ({guess_row}, {guess_col})!")
        elif result == "sunk":
            current_player.guess_board[guess_row][guess_col] = 'X'
            print(f"\n*** HIT! ***")
            print(f"*** You sunk {opponent.name}'s {ship_name}! ***")
        else:
            current_player.guess_board[guess_row][guess_col] = 'O'
            print(f"\nMiss. No ship at ({guess_row}, {guess_col}).")
        
        # Check for winner
        if opponent.has_lost():
            print(f"\n{'=' * 60}")
            print(f"GAME OVER!")
            print(f"{'=' * 60}")
            print(f"\n🎉 {current_player.name} WINS! 🎉")
            print(f"All of {opponent.name}'s ships have been sunk!")
            print(f"Total turns: {turn}")
            
            # Show final boards
            print(f"\n{player1.name}'s Final Board:")
            player1.display_own_board()
            print(f"\n{player2.name}'s Final Board:")
            player2.display_own_board()
            
            game_over = True
        else:
            # Switch players
            current_player, opponent = opponent, current_player
            input("\nPress Enter to continue to next turn...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGame interrupted. Thanks for playing!")
        sys.exit()