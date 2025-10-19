from file1 import initialize_game, Player
from file2 import Car

def run_game():
    initialize_game()

def test_player_actions():
    hero = Player("Archer", 100)
    hero.move("forward")
    hero.attack(hero)  # attacks self for test
    hero.jump()

def test_car_actions():
    car = Car("Ferrari")
    car.start_engine()
    car.honk()
    car.stop_engine()
