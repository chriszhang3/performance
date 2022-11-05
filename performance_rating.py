import math
import argparse
from collections import defaultdict
from datetime import date
import asyncio
import time
import aiohttp

def get_elo_difference(score, num_games):
    if score == 0:
        p = 1 / num_games / 2
    elif score == num_games:
        p = 1 - 1 / num_games / 2
    else:
        p = score / num_games
    return -400 * math.log10(1 / p - 1)

def compute_performance_rating(games_list, username, num_games):
    if not games_list:
        print("No games")
        return
    score = 0
    results = []
    total_rating = 0
    recent_games = games_list[:num_games]
    for game in recent_games:
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

    N = len(recent_games)
    print(f"Score: {score:g} / {N}")
    # print(f"Average rating of opponents: {total_rating / num_games:.0f}")
    performance_rating = total_rating / N \
                         + get_elo_difference(score, N)
    print(f"Performance rating: {performance_rating:.0f}")

def generate_url(username, month, year):
    return f"https://api.chess.com/pub/player/{username}/games/{year}/{month:02d}"

async def async_get(session: aiohttp.ClientSession, url):
    json = None
    while json is None:
        async with session.get(url) as response:
            try:
                json = await response.json()
            except aiohttp.ContentTypeError:
                # We can retry these after all the responses are received.
                print(response)
                time.sleep(1)
                exit(1)

            if 'code' in json and json['code'] == 0:
                message = json['message']
                if "not found" in message:
                    exit("User not found.")
                else:
                    print(f"Error response from Chess.com: {json}")
                    exit(json['message'])
    return json

async def main():
    parser = argparse.ArgumentParser(
        description='Compute the performance rating of a Chess.com account using the public API.'
    )
    parser.add_argument('username', type=str,
                        help='username of the Chess.com account')
    parser.add_argument('--games', type=int, default=20, metavar='G',
                        help='your performance rating based on your last G games')
    parser.add_argument('--months', type=int, default=6, metavar='M',
                        help='use games from the last M months')
    args = parser.parse_args()
    num_games = args.games
    username = args.username
    
    date_time = date.today()
    games_list = defaultdict(list)

    six_months = [(date_time.month - i) % 12 for i in range(args.months)]
    async with aiohttp.ClientSession() as session:
        tasks = [async_get(session, generate_url(username, month, date_time.year))
                 for month in six_months]
        tasks.append(async_get(session, f"https://api.chess.com/pub/player/{username}/stats"))
        games = await asyncio.gather(*tasks)

    stats = games.pop()
    for games_month in games:
        for g in games_month['games'][::-1]:
            games_list[g['time_class']].append(g)

    print()
    for tc in ['rapid', 'blitz', 'bullet']:
        rating = stats['chess_'+tc]['last']['rating']
        print(f"{tc.capitalize()} rating: {rating}")
        compute_performance_rating(games_list[tc], username, num_games)
        print()

if __name__=='__main__':
    asyncio.run(main())
