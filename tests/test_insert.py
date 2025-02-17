import asyncio
import logging
import logging.config
import os
import sys
from multiprocessing import Pool
from random import randint
from time import time

from random_word import RandomWords

sys.path.insert(1, os.path.join("/home/bot/code/vpn_dan_bot/src"))


from db.utils import add_user

logging.config.fileConfig("log.ini", disable_existing_loggers=True)
logger = logging.getLogger()
# logging.disable()

RETRIES = 4


def gen_input(null):
    return dict(
        user_id=randint(10**9, 10**10 - 1),
        user_name=RandomWords().get_random_word(),
    )


async def main():
    start = time()

    with Pool(processes=8) as pool:
        values = range(RETRIES)
        result = pool.map(gen_input, values)

    gen = time() - start

    coros = [add_user(**kwargs) for kwargs in result]

    coros_gen = time() - start - gen

    await asyncio.gather(*coros)

    end = time() - start - coros_gen - gen

    print(f"{coros_gen=}  {gen=}  {end=}")


if __name__ == "__main__":
    # for _ in range(30):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

# if __name__ == "__main__":
#     query = update(UserData).where(UserData.id == 2616).values(balance=100)

#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(execute_query(query))
