import math
import argparse
from collections import defaultdict
from datetime import date
import asyncio
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
    if len(games_list) < num_games:
        print("Warning: Not enough games")
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

async def get_games(session, username, month, year):
    url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month:02d}"
    async with session.get(url) as response:
        json = await response.json()
        return json['games']

async def get_stats(session, url):
    async with session.get(url) as response:
        return await response.json()

async def main():
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

    six_months = [(date_time.month - i) % 12 for i in range(6)]
    async with aiohttp.ClientSession() as session:
        tasks = [get_games(session, username, month, date_time.year)
                 for month in six_months]
        tasks.append(get_stats(session, f"https://api.chess.com/pub/player/{username}/stats"))
        games = await asyncio.gather(*tasks)

    stats = games.pop()
    for games_month in games:
        for g in games_month[::-1]:
            games_list[g['time_class']].append(g)

    print()
    for tc in ['rapid', 'blitz', 'bullet']:
        rating = stats['chess_'+tc]['last']['rating']
        print(f"{tc.capitalize()} rating: {rating}")
        compute_performance_rating(games_list[tc], username, num_games)
        print()

if __name__=='__main__':
    asyncio.run(main())
