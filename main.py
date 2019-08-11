import asyncio
import logging
from aiohttp import ClientSession
from bs4 import BeautifulSoup


async def get_html(session: ClientSession, url: str) -> str:
    """Загружаем html по ссыкле. В случае ошибки возвращаем None"""
    html = None
    try:
        async with session.get(url, raise_for_status=True) as resp:
            html = await resp.text()
    finally:
        return html


async def main():
    test_url = 'https://www.kinopoisk.ru/'

    async with ClientSession() as session:
        html = await get_html(session, test_url)

    if html is not None:
        print(html[:50])
    else:
        print('ERROR')

if __name__ == '__main__':
    asyncio.run(main())