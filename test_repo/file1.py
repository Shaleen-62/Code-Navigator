import file2

def initialize_game():
    print("Initializing game...")
    load_assets()
    file2.setup_levels()

def load_assets():
    print("Loading game assets...")

class Character:
    def __init__(self, name, health):
        self.name = name
        self.health = health

    def attack(self, target):
        print(f"{self.name} attacks {target.name}!")

    def move(self, direction):
        print(f"{self.name} moves {direction}.")

class Player(Character):
    def attack(self, target):
        print(f"{self.name} performs a special attack on {target.name}!")
        super().attack(target)

    def jump(self):
        print(f"{self.name} jumps high!")
