from flask import Flask, Response, request, render_template
import uuid
import json
import pickle
import os

app = Flask(__name__)

EMPTY_SPACE_TOKEN = '_'
PLAYER_TOKEN = 's'
FOOD_TOKEN = 'f'
game_history = {}

def create_folder_structure_for_player_if_not_exists(name, unique_token, board_number):
    player_folder = f"game_history/{board_number}/{name}"
    if not os.path.exists(player_folder):
        os.makedirs(player_folder)
    
    current_game_folder = f"game_history/{board_number}/{name}/{unique_token}"
    if not os.path.exists(current_game_folder):
        os.makedirs(current_game_folder)

def record_step(name, unique_token, board_number, board, score, max_steps, steps_taken):
    d = {}
    d["name"] = name
    d["unique_token"] = unique_token
    d["max_steps"] = max_steps
    d["board"] = board
    d["score"] = score
    d["steps_taken"] = steps_taken

    with open(f"game_history/{board_number}/{name}/{unique_token}/{steps_taken}.json", 's') as fp:
        json.dump(d, fp)

def calculate_last_step_taken(name, unique_token, board_number):
    highest_step_taken = -1
    
    directory = f"game_history/{board_number}/{name}/{unique_token}"
    for filename in os.listdir(directory):
        steps_taken = int(filename.split(".json")[0])

        if steps_taken > highest_step_taken:
            highest_step_taken = steps_taken

    return highest_step_taken

def find_player_index(name, unique_token, last_step_taken, board_number):
    filepath = f"game_history/{board_number}/{name}/{unique_token}/{last_step_taken}.json"

    with open(filepath, 'r') as fp:
        data = json.load(fp)
        player_index = 0

        for row in data["board"]:
            for column in row:
                if column == "s":
                    return player_index

                player_index += 1

def parse_last_game_state(name, unique_token, last_step_taken, board_number):
    filepath = f"game_history/{board_number}/{name}/{unique_token}/{last_step_taken}.json"

    with open(filepath, 'r') as fp:
        data = json.load(fp)
        
        return data["max_steps"], data["board"], data["score"], data["steps_taken"], find_player_index(name, unique_token, last_step_taken, board_number)

def move_player(name, unique_token, last_step_taken, new_player_location_index_offset, score, steps_taken, board_number):
    filepath = f"game_history/{board_number}/{name}/{unique_token}/{last_step_taken}.json"
    player_index = find_player_index(name, unique_token, last_step_taken, board_number)
    new_player_index = player_index + new_player_location_index_offset
    found_players_new_position = False

    with open(filepath, 'r') as fp:
        data = json.load(fp)
        data_copy = {**data}
        index = 0
        new_score = score

        for row_index, row in enumerate(data_copy["board"]):
            for column_index, column in enumerate(row):
                if index == player_index:
                    data_copy["board"][row_index][column_index] = "_"
                if index == new_player_index:
                    found_players_new_position = True

                    if column == "f":
                        new_score += 1
                    data_copy["board"][row_index][column_index] = "s"
                index += 1

        if found_players_new_position:
            return True, data_copy["board"], new_score, steps_taken + 1
        else:
            return False, data, score, steps_taken # no valid choice was made

def get_players_highest_score(name, board_number):
    best_score = -1
    player_folder = f"game_history/{board_number}/{name}"

    if os.path.exists(player_folder):
        for game in os.listdir(player_folder):
            last_step_taken = calculate_last_step_taken(name, game, board_number)

            _, _, score, _, _ = parse_last_game_state(name, game, last_step_taken, board_number)

            if score > best_score:
                best_score = score
    
    return best_score

def get_players_names_and_best_scores_per_level():
    data = {}

    game_history_folder = "game_history"
    if os.path.exists(game_history_folder):
        for level in os.listdir(game_history_folder):
            data[level] = {}
            for player_name in os.listdir(f"{game_history_folder}/{level}"):
                data[level][player_name] = get_players_highest_score(player_name, level)
    return data

def find_board_number(player_name, unique_token):
    game_history_folder = "game_history"
    if os.path.exists(game_history_folder):
        for level in os.listdir(game_history_folder):
            for player in os.listdir(game_history_folder + "/" + level):
                if player == player_name:
                    for token in os.listdir(game_history_folder + "/" + level + "/" + player):
                        if token == unique_token:
                            return level

@app.route('/')
def index(name=None):
    data = get_players_names_and_best_scores_per_level()

    return render_template("index.html", data=data)

@app.route('/api/game', methods=["POST"])
def init(board_number=0):
    print(request.json)

    if "name" not in request.json:
        return Response(json.dumps({"message": "Required parameter 'name' was not provided. How would we know who you are?"}), 422)

    if "board_number" in request.json:
        board_number = request.json["board_number"]
        print(board_number)

    with open(f'levels/{board_number}.json', 'r') as fp:
        INITIAL = json.load(fp)

    initial_copy = {**INITIAL}

    unique_token = str(uuid.uuid4()) 

    initial_copy["unique_token"] = unique_token 

    initial_copy["score"] = 0

    initial_copy["steps_taken"] = 0

    game_history[request.json["name"] ] = unique_token

    create_folder_structure_for_player_if_not_exists(request.json["name"], unique_token, board_number)

    print(f"initial board \n {initial_copy['board']}")

    record_step(request.json["name"], unique_token, board_number, initial_copy["board"], 0, initial_copy["max_steps"], 0) 

    return Response(json.dumps(initial_copy), mimetype='text/json')

@app.route('/api/step', methods=["POST"])
def step():
    if "name" not in request.json:
        return Response(json.dumps({"message": "Required parameter 'name' was not provided. How would we know who you are?"}), 422)
    
    if "unique_token" not in request.json:
        return Response(json.dumps({"message": "Required parameter 'unique_token' was not provided. How would we know what game you are playing?"}), 422)

    if "step_direction" not in request.json:        
        return Response(json.dumps({"message": "Required parameter 'step_direction' was not provided. How would we know where your snail intends to go?"}), 400)

    board_number = find_board_number(request.json["name"], request.json["unique_token"])
    last_step_taken = calculate_last_step_taken(request.json["name"], request.json["unique_token"], board_number)

    max_steps, board, score, steps_taken, player_location_index = parse_last_game_state(request.json["name"], request.json["unique_token"], last_step_taken, board_number)

    if max_steps == steps_taken:
        d = {}

        d["max_steps"] = max_steps
        d["board"] = board
        d["unique_token"] = request.json["unique_token"]
        d["score"] = score
        d["steps_taken"] = steps_taken

        d["message"] = "Game has already ended and your newest move was not processed"

        # d["your best score"] = calculate_players_best_score(request.json["name"], request.json["unique_token"]) # TODO
        # d["best score"] = calculate_best_score() # TODO

        return Response(json.dumps(d), 400, mimetype='text/json')

    if request.json["step_direction"]  == "n":
        player_location_index_offset = -5 # going up a row
    elif request.json["step_direction"]  == "e":
        player_location_index_offset = 1 # going right a column
    elif request.json["step_direction"]  == "s":
        player_location_index_offset = 5 # going down a row 
    elif request.json["step_direction"]  == "w":
        player_location_index_offset = -1 # going left a column
    else:
        return Response(json.dumps({"message": "Required parameter 'step_direction' was not valid character. Accepted characters are ['n', 'e', 's', 'w']"}), 422)

    valid_mode, new_board, new_score, steps_taken = move_player(request.json["name"], request.json["unique_token"], last_step_taken, player_location_index_offset, score, steps_taken, board_number)    

    if not valid_mode:
        return Response(json.dumps({"message": "Invalid move. You would have gone off the edge"}), 422)

    print(f"new board \n{new_board}")

    record_step(request.json["name"], request.json["unique_token"], board_number, new_board, new_score, max_steps, steps_taken)

    d = {}

    d["max_steps"] = max_steps
    d["board"] = new_board
    d["unique_token"] = request.json["unique_token"]
    d["score"] = new_score
    d["steps_taken"] = steps_taken

    return Response(json.dumps(d), 200, mimetype='text/json')

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)