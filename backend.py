import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///pets.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# --- Model ---
class Pet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    food = db.Column(db.Float, default=100.0, nullable=False)
    water = db.Column(db.Float, default=100.0, nullable=False)
    fun = db.Column(db.Float, default=100.0, nullable=False)
    xp = db.Column(db.Integer, default=0, nullable=False)
    level = db.Column(db.Integer, default=1, nullable=False)
    last_decay = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def as_dict(self):
        return {
            "id": self.id,
            "food": self.food,
            "water": self.water,
            "fun": self.fun,
            "xp": self.xp,
            "level": self.level
        }

# --- API ---

@app.before_first_request
def create_tables():
    db.create_all()
    # Optional: Create a default pet if none exist
    if Pet.query.first() is None:
        db.session.add(Pet())
        db.session.commit()

@app.route("/pet/<int:pet_id>", methods=["GET"])
def get_pet(pet_id):
    pet = Pet.query.get_or_404(pet_id)
    return jsonify(pet.as_dict())

@app.route("/pet/<int:pet_id>", methods=["PUT"])
def update_pet(pet_id):
    pet = Pet.query.get_or_404(pet_id)
    data = request.get_json()
    for field in ["food", "water", "fun", "xp", "level"]:
        if field in data:
            setattr(pet, field, float(data[field]) if field in ["food", "water", "fun"] else int(data[field]))
    db.session.commit()
    return jsonify(pet.as_dict())

@app.route("/pet/<int:pet_id>/action", methods=["POST"])
def pet_action(pet_id):
    pet = Pet.query.get_or_404(pet_id)
    data = request.get_json()
    action = data.get("action")
    amount = float(data.get("amount", 10.0))
    if action == "feed":
        pet.food = min(100.0, pet.food + amount)
    elif action == "fill_water":
        pet.water = min(100.0, pet.water + amount)
    elif action == "play":
        pet.fun = min(100.0, pet.fun + amount)
    db.session.commit()
    return jsonify(pet.as_dict())

# --- Decay endpoint (call this every minute with a cron job or script) ---
@app.route("/cron/decay", methods=["POST"])
def cron_decay():
    # Rates per minute
    food_decay = 0.54
    water_decay = 0.24
    fun_decay = 0.12

    pets = Pet.query.all()
    for pet in pets:
        pet.food = max(0, pet.food - food_decay)
        pet.water = max(0, pet.water - water_decay)
        pet.fun = max(0, pet.fun - fun_decay)
        # XP: +1 every 10 minutes (do +0.1 per minute for simplicity)
        pet.xp += 0.1
        if pet.xp >= 25:
            levels_gained = int(pet.xp // 25)
            pet.level += levels_gained
            pet.xp = pet.xp % 25
        pet.last_decay = datetime.utcnow()
    db.session.commit()
    return jsonify({"status": "decay_applied", "count": len(pets)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
