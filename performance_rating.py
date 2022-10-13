import json
import math
import argparse
from enum import Enum
from collections import defaultdict
from datetime import date
from dateutil import relativedelta
import requests

class TimeControl(Enum):
    RAPID = 'rapid'
    BLITZ = 'blitz'
    BULLET = 'bullet'

def get_elo_difference(score, num_games):
    if score == 0:
        p = 1 / num_games / 2
    elif score == num_games:
        p = 1 - 1 / num_games / 2
    else:
        p = score / num_games
    return -400 * math.log10(1 / p - 1)

def compute_performance_rating(games_list, username, num_games):
    if len(games_list) < num_games:
        raise Exception("Not enough games.")
    score = 0
    results = []
    total_rating = 0
    for game in games_list[:num_games]:
        white = game['white']
        black = game['black']
        if white['username'] == username:
            result = white['result']
            total_rating += black['rating']
        else:
            result = black['result']
            total_rating += white['rating']
        results.append(result)
        if result == 'win':
                score += 1
        elif result in ['stalemate', 'repetition']:
                score += 0.5
    
    print(f"Score: {score:g} / {num_games}")
    # print(f"Average rating of opponents: {total_rating / num_games:.0f}")
    performance_rating = total_rating / num_games \
                         + get_elo_difference(score, num_games)
    print(f"Performance rating: {performance_rating:.0f}")

def populate_games(username, month, year, games_list):
    url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month:02d}"
    text = requests.get(url).text
    games = json.loads(text)['games']
    if year < 2000:
        raise Exception("Too far in the past.")
    for g in games[::-1]:
        games_list[TimeControl(g['time_class'])].append(g)

def main():
    parser = argparse.ArgumentParser(
        description='Compute the performance rating of a Chess.com account using the public API.'
    )
    parser.add_argument('username', type=str,
                        help='username of the Chess.com account')
    parser.add_argument('--games', type=int, default=20, metavar='G',
                        help='your performance rating based on your last G games')
    args = parser.parse_args()
    num_games = args.games
    username = args.username
    
    date_time = date.today()
    games_list = defaultdict(list)

    while len(games_list[TimeControl.RAPID]) < num_games \
          or len(games_list[TimeControl.BLITZ]) < num_games \
          or len(games_list[TimeControl.BULLET]) < num_games:
        year = date_time.year
        month = date_time.month
        populate_games(username, month, year, games_list)
        date_time = date_time - relativedelta.relativedelta(months=1)
    
    url = f"https://api.chess.com/pub/player/{username}/stats"
    text = requests.get(url).text
    stats = json.loads(text)

    print()
    for tc in TimeControl:
        rating = stats['chess_'+tc.value]['last']['rating']
        print(f"{tc.value.capitalize()} rating: {rating}")
        compute_performance_rating(games_list[tc], username, num_games)
        print()

main()
