import sqlite3
from flask import Flask, render_template, request, flash, session, jsonify, redirect, send_from_directory
from collections import OrderedDict
import bcrypt
import random
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = '4d970fa5c06a01855554c8e453ce630c19135dc6ffc9bc7e'

def get_db_connection():
    conn = sqlite3.connect('top-trumps-db.db')
    conn.row_factory=sqlite3.Row
    return conn

def check_user_details(username):
    conn = get_db_connection()
    # returns None if no user otherwise will return the tuple containing user details
    user = conn.execute("SELECT * FROM users WHERE username=?",(username,)).fetchone()
    conn.close()
    return user

def check_user_credentials(username, password):
    user = check_user_details(username)
    if user:
        hashed_pw = bcrypt.hashpw(password.encode('utf8'), user['password'].encode('utf8'))
        return hashed_pw.decode('utf8')==user["password"]
    return False

# home page
@app.route('/', methods=('GET',))
def index():
    return render_template('index.html')

@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method=="POST":
        username = request.form["username"]
        password1 = request.form["password1"]
        password2 = request.form["password2"]
        if password1!=password2:
            flash("Passwords do not match!") 
            return render_template('register.html')
        else:
            hashed_pw = bcrypt.hashpw(password1.encode('utf8'), bcrypt.gensalt())
            conn=get_db_connection()
            conn.execute('INSERT INTO users (username, password) VALUES (?,?)',
                        (username, hashed_pw.decode('utf8')))
            conn.commit()
            user_id = conn.execute("SELECT id FROM users WHERE username=?",(username,)).fetchone()[0]
            conn.execute("INSERT INTO stats (player_id) VALUES (?)", (user_id,))
            conn.commit()
            conn.close()
            return redirect('/')
    
    if request.method=="GET":
        return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]
        
        if check_user_credentials(username, password):
            session['username'] = username
            return redirect('/')
        
        flash("Invalid credentials please try again")
        return render_template('login.html')
        
    if request.method=="GET":
        return render_template('login.html')
    
@app.route('/logout', methods=("GET",))
def logout():
    session.pop('username', None)
    return index()

def get_user():
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username=?",(session["username"],)).fetchone()
    conn.close()
    return user

def get_computer():
    conn = get_db_connection()
    computer = conn.execute("SELECT * FROM users WHERE username=?",("computer",)).fetchone()
    conn.close()
    return computer

# check if cards have been shuffled and therefore game alredy started
def check_shuffle():
    conn = get_db_connection()
    check = len(conn.execute("SELECT * FROM game").fetchall())!=0
    conn.close()
    return check

def get_player_cards():
    user = get_user()
    conn = get_db_connection()
    player_cards = conn.execute("SELECT * FROM game WHERE player_id=?",(user['id'],)).fetchall()
    conn.close()
    return player_cards

def get_computer_cards():
    computer = get_computer()
    conn = get_db_connection()
    computer_cards = conn.execute("SELECT * FROM game WHERE player_id=?", (computer['id'],)).fetchall()
    conn.close()
    return computer_cards

def get_card_counts():
    retDict={}
    retDict["player_count"] = len(get_player_cards())
    retDict["computer_count"] = len(get_computer_cards())
    return retDict

def get_latest_user_card():
    player_cards = get_player_cards()
    conn = get_db_connection()
    first_card_id = sorted(player_cards, key = lambda x: x['card_order'])[0]['card_id']
    card = conn.execute("SELECT * FROM cards WHERE id = ?",(first_card_id,)).fetchone()
    conn.close()
    return card

def get_latest_computer_card():
    computer_cards = get_computer_cards()
    conn = get_db_connection()
    next_computer_card_id = sorted(computer_cards, key=lambda x:x['card_order'])[0]['card_id']
    next_computer_card = conn.execute("SELECT * FROM cards WHERE id=?", (next_computer_card_id,)).fetchone()
    conn.close()
    return next_computer_card

# handle cards in the middle
def transfer_middle_cards(player_win):
    conn= get_db_connection()
    middle_cards = conn.execute("SELECT * FROM middle").fetchall()
    # dont perform transfer if draw or no cards in the middle
    if player_win=="DRAW" or len(middle_cards)==0:
        conn.close()
        return
    
    winner_id = get_user()['id'] if player_win else get_computer()['id']
    no_of_winners_cards = len(conn.execute("SELECT * FROM game WHERE player_id=?", (winner_id,)).fetchall())
    for card in middle_cards:
        conn.execute("INSERT INTO game (player_id, card_id, card_order) VALUES (?,?,?)",
                     (winner_id, card['card_id'], no_of_winners_cards))
        no_of_winners_cards+=1

        conn.execute("DELETE FROM middle WHERE card_id=?", (card['card_id'],))
    conn.commit()
    conn.close()

# transfer cards after a round
def transfer_card(player_win):
    transfer_middle_cards(player_win)
    conn=get_db_connection()
    if player_win=="DRAW":
        # put current cards into reserve. if each player has more than 1 card
        computer_card = get_latest_computer_card()
        user_card = get_latest_user_card()

        conn.execute("INSERT INTO middle (card_id) VALUES (?)",
                     (computer_card['id'],))
        conn.execute("DELETE FROM game WHERE card_id=?",(computer_card['id'],))
        conn.execute("INSERT INTO middle (card_id) VALUES (?)",
                     (user_card['id'],))
        conn.execute("DELETE FROM game WHERE card_id=?",(user_card['id'],))
    
    elif player_win:
        user_id = get_user()['id']
        computer_card_id = get_latest_computer_card()['id']
        number_of_player_cards = len(get_player_cards())
        conn.execute("UPDATE game SET player_id=?, card_order=? WHERE card_id=?",
                     (user_id, number_of_player_cards, computer_card_id))
    else:
        computer_id = get_computer()['id']
        user_card_id = get_latest_user_card()['id']
        number_of_computer_cards = len(get_computer_cards())
        conn.execute("UPDATE game SET player_id=?, card_order=? WHERE card_id=?",
                     (computer_id, number_of_computer_cards, user_card_id))
    conn.commit()
    conn.close()

# function to reorder cards after a play. moving latest cards to back
def reorder_cards(player_win):
    transfer_card(player_win)
    conn = get_db_connection()
    player_cards = get_player_cards()
    no_of_cards = len(player_cards)
    for card in player_cards:
        current_card_position = card['card_order']
        if current_card_position<=0:
            new_card_position = no_of_cards-1
        else:
            new_card_position = current_card_position-1
        conn.execute("UPDATE game SET card_order=? WHERE card_id=?",(new_card_position, card['card_id']))
    conn.commit()
       
    computer_cards = get_computer_cards() 
    no_of_cards = len(computer_cards)
    for card in computer_cards:
        current_card_position = card['card_order']
        if current_card_position<=0:
            new_card_position = no_of_cards-1
        else:
            new_card_position = current_card_position-1
        conn.execute("UPDATE game SET card_order=? WHERE card_id=?",(new_card_position, card['card_id']))
    conn.commit()
    conn.close()
        
def coin_flip():
    options = ["H","T"]
    return options[random.randint(0,1)]
    
def shuffle_cards():
    conn = get_db_connection()
    cards = conn.execute("SELECT * FROM cards").fetchall()
    # randomly select player cards
    players_cards = random.sample(cards, round(len(cards)/2))
    computers_cards = list(set(cards)-set(players_cards))
    
    user = get_user()
    order = 0
    for card in players_cards:
        conn.execute("INSERT INTO game (player_id, card_id, card_order) VALUES (?,?,?)",
                    (user['id'], card['id'], order))
        order+=1
    
    computer = get_computer()    
    order=0
    for card in computers_cards:
        conn.execute("INSERT INTO game (player_id, card_id, card_order) VALUES (?,?,?)",
                    (computer['id'], card['id'], order))
        order+=1

    conn.commit()
    conn.close()
    retDict = {
        "players_cards":players_cards,
        "computer_cards":computers_cards
    }
    return retDict
    
def start_game():
    conn = get_db_connection()
    conn.execute("DELETE FROM game")
    conn.execute("DELETE FROM middle")
    conn.commit()
    conn.close()

    players_cards = shuffle_cards()["players_cards"]
    card_count = get_card_counts()
    retDict = {
        "player_cards":dict(players_cards[0]),
        "count":card_count
    }
    return jsonify(retDict)
    
def update_winner_stats(player_win):
    conn = get_db_connection()
    # check user exists in the stats table
    user = get_user()
    user_stat = conn.execute("SELECT * FROM stats WHERE player_id=?",(user['id'],)).fetchone()
    if player_win:
        win_count = user_stat['win']
        conn.execute("UPDATE stats SET win=? WHERE player_id=?",(win_count+1, user['id']))
    elif player_win=="DRAW":
        draw_count = user_stat['draw']
        conn.execute("UPDATE stats SET draw=? WHERE player_id=?",(draw_count+1, user['id']))
    else:
        loss_count = user_stat['loss']
        conn.execute("UPDATE stats SET loss=? WHERE player_id=?",(loss_count+1, user['id']))
    conn.commit()
    conn.close()    
         
def check_winner():
    no_of_computer_cards=len(get_computer_cards())
    no_of_player_cards=len(get_player_cards())
    retJson={'winner':False}
    
    if no_of_computer_cards==0 or no_of_player_cards==0:
        retJson['winner']= True
        if no_of_computer_cards!=0:
            update_winner_stats(False)
            retJson['msg']="The Computer won!!! Uh oh...."
        elif no_of_player_cards!=0:
            update_winner_stats(True)
            retJson['msg']="You won! Congratulations!!!!"
        else:
            update_winner_stats("DRAW")
            retJson['msg']="You drew..... BOOOOOOOOO!!!!!!!!"
    return retJson

def computer_play():
    computer_card = get_latest_computer_card()
    # ignore first 2 values which are id and title
    max_value = max(computer_card[2:])
    # loop through fields to identify which has max value
    for field in dict(computer_card):
        if computer_card[field]==max_value and field!="id" and field!="title":
            max_field = field
            break
    # get player card and compare to computer value to find who won
    player_card = get_latest_user_card()
    player_score = player_card[max_field]
    if player_score==max_value:
        user_win = "DRAW"
    else:
        user_win = player_score>max_value

    retDict = {
        "computer_card":dict(computer_card),
        "user_win":user_win,
        "field":max_field,
    }
    return retDict

# main function called from template 
@app.route('/continue_game', methods=("GET", "POST"))
def continue_game():
    if request.method=="POST":
        posted_data = request.get_json()
        # check for computers turn
        if "computer_turn" in posted_data.keys():
            # check if just displaying computer card
            if "display" in posted_data.keys():
                retJson = computer_play()
                return retJson
            # return highest value and field for computer's next card along with if computer or player wins
            computer_play_dict = computer_play()
            reorder_cards(computer_play_dict['user_win'])
            winner = check_winner()
            if not winner['winner']:
                next_player_card = get_latest_user_card()
                computer_play_dict["player_card"] = dict(next_player_card)
           
            computer_play_dict['winner']=winner
            return jsonify(computer_play_dict)
        # below is for user's turn
        # get skill chosen by user and compare to computer card
        skill = posted_data['skill']
        value = get_latest_user_card()[skill]
        next_computer_card = get_latest_computer_card()
        if value==next_computer_card[skill]:
            result="DRAW"
        else:
            result =  value>next_computer_card[skill]
        # reorder players cards according to the result
        reorder_cards(result)
        # chck if oevrall winner and therefore game finished
        winner = check_winner()
        card_count = get_card_counts()
        retJson={
            "user_win":result,
            "winner":winner,
            "computer_card":dict(next_computer_card),
            "count":card_count
        }
        
        return jsonify(retJson)
    
    if request.method=="GET":        
        if check_shuffle():
            card = get_latest_user_card()
            computer_card = get_latest_computer_card()
            card_count = get_card_counts()
            card_dict = {
                "player_cards":dict(card),
                "computer_card":dict(computer_card),
                "count":card_count
            }

            return jsonify(card_dict)
        return start_game()

@app.route('/play', methods=('GET', 'POST'))
def play():
    start_game()
    return render_template('play.html')

@app.route('/reset', methods=("GET",))
def reset():
    start_game()
    return redirect("/play")

# function to return image for cards
@app.route('/image/<path:filename>')
def get_image(filename):
    filename = filename.lower()
    file_path = os.path.join('static/images', filename)
    if os.path.exists(file_path):
        return send_from_directory('static/images', filename)
    # use default image if no image found under filepath
    else:
        return send_from_directory('static/images', 'default.jpeg')

@app.route('/about', methods=('GET',))
def about():
    return render_template('about.html')

@app.route('/cards', methods=('GET',))
def cards():
    conn = get_db_connection()
    search_string=""
    if request.args.get('q'):
        search_string = request.args.get('q')
        cards=conn.execute("SELECT * FROM cards WHERE title LIKE '%"+search_string+"%'")
    else:
        cards = conn.execute("SELECT * FROM cards").fetchall()
    cardDict = {dict(card)['id']:dict(card) for card in cards}
    return render_template('cards.html', cards=cardDict, search_string=search_string)

@app.route('/stats', methods=('GET',))
def stats():
    user = get_user()
    conn = get_db_connection()
    user_id_dict = dict(conn.execute("SELECT id, username FROM users").fetchall())
    all_stats = conn.execute("SELECT * FROM stats").fetchall()    
    conn.close()
    
    computer_stats={"win":0,"draw":0,"loss":0}
    for stat in all_stats:
        computer_stats['loss']+=stat['win']
        computer_stats['win']+=stat['loss']
        computer_stats['draw']+=stat['draw']
    list_user_stats = list(filter(lambda x: x['player_id']==user['id'], all_stats))[0]
    user_info={"username":user['username'], "date_joined":list_user_stats['date_joined']}
    userStatsJson = {key:list_user_stats[key] for key in list_user_stats.keys() 
                        if key in ['win', 'loss','draw']}
    if ((userStatsJson['win']+userStatsJson['loss']+userStatsJson['draw'])==0):
        user_info['msg']="You have no stats yet!!!!!!"

    # Get leaderboard data
    #sort stats username by winner
    wins = sorted(all_stats, key=lambda x: x['win'], reverse=True)[:5]
    winJson={user_id_dict[user_stats['player_id']]:user_stats['win'] for user_stats in wins}
    draws = sorted(all_stats, key=lambda x: x['draw'], reverse=True)[:5]
    drawJson={user_id_dict[user_stats['player_id']]:user_stats['draw'] for user_stats in draws}
    losses = sorted(all_stats, key=lambda x: x['loss'], reverse=True)[:5]
    lossJson={user_id_dict[user_stats['player_id']]:user_stats['loss'] for user_stats in losses}
    
    return render_template('stats.html', stats=userStatsJson, user_info=user_info, wins=winJson, draws=drawJson, losses=lossJson, computer_stats=computer_stats)
    


# to do:
    # add more cards
    # make code cleaner   
    
    #  need to condense the show cards section