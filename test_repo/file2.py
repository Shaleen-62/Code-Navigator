class Vehicle:
    def __init__(self, model):
        self.model = model

    def start_engine(self):
        print(f"{self.model} engine starting...")

    def stop_engine(self):
        print(f"{self.model} engine stopping...")

class Car(Vehicle):
    def start_engine(self):
        print(f"{self.model} revs up!")
        super().start_engine()

    def honk(self):
        print(f"{self.model} honks: Beep beep!")

def setup_levels():
    print("Setting up game levels...")
