import asyncio
import logging
import math
import time
from urllib.parse import urljoin
from aiohttp import ClientSession
from bs4 import BeautifulSoup

TOTAL_PAGES = 21042
MAIN_URL = 'https://www.kinopoisk.ru/'
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0'


async def get_html(session: ClientSession, url: str) -> str:
    """Загружаем html по ссыкле. В случае ошибки возвращаем None"""
    html = None
    logging.info('in get html url %s', url)
    try:
        async with session.get(url, raise_for_status=True, headers={'user-agent': USER_AGENT}) as resp:
            html = await resp.text()
    except Exception as err:
        logging.exception(err)
    finally:
        return html


async def get_films_url_from_page(session: ClientSession, num_page: int = 1) -> list:
    request_url = f'/lists/navigator/?page={num_page}'

    logging.info('get films url from page %d', num_page)
    html = await get_html(session, urljoin(MAIN_URL, request_url))

    if html is None:
        return None

    bs_parser = BeautifulSoup(html, 'html.parser')
    films_url = []
    for tags in bs_parser.select('.selection-film-item-meta__link'):
        film_url = tags['href']
        films_url.append(film_url)

    return films_url


async def get_reviews(session: ClientSession, film_url: str):
    """Принимает строку формата "/film/film_id" """

    def parse_reviews_html(bs_parser: BeautifulSoup) -> list:
        """
        Достаёт из bs4 парсера текст рецензии и конечную оценку. Спец символы удалены,
        символ переноса строки заменён на пробел. Возварщает список словарей,
        по ключу "text" - текст рецензии, по ключу sentiment_category - оценка: neutral, good, bad
        """
        parsed_reviews = []
        for review in bs_parser.select('div[class="reviewItem userReview"]'):
            _, sentiment_category = review.find(itemprop="reviews")['class']
            text = review.find(itemprop="reviewBody").text
            text = text.replase('\r', '').replase('\n', ' ')
            parsed_reviews.append({'text': text, 'sentiment_category': sentiment_category})

        return parsed_reviews

    page_url = lambda page_num: f'{film_url}reviews/status/all/perpage/200/page/{page_num}'
    logging.info('get reviews for film %s', film_url)

    html = await get_html(session, urljoin(MAIN_URL, page_url(1)))
    if html is None:
        return None

    bs_parser = BeautifulSoup(html, 'html.parser')
    from_to_string = bs_parser.select_one('.pagesFromTo')
    _, _, reviews_count = from_to_string.text.split()

    page_count = math.ceil(int(reviews_count) / 200) - 1  # одну страницу мы уже спарсили
    reviews_per_page = [parse_reviews_html(bs_parser)]
    for page in range(2, page_count + 1):
        html = await get_html(session, urljoin(MAIN_URL, page_url(page)))
        if html is None:
            logging.warning('limit for %s sleep 1.5 seconds', film_url)
            reviews_per_page.append(None)
            await asyncio.sleep(1.5)
            continue
        else:
            bs_parser = BeautifulSoup(html, 'html.parser')
            parsed_reviews = parse_reviews_html(bs_parser)
            reviews_per_page.append(parsed_reviews)

        await asyncio.sleep(0.5)

    return reviews_per_page


async def main():
    logging.basicConfig(level=logging.INFO)
    film_url = '/film/361/'
    async with ClientSession() as session:
       rev = await get_reviews(session, film_url)

    return rev

if __name__ == '__main__':
    rev = asyncio.run(main())
    if rev is not None:
        print(len(rev), rev[:5])
    else:
        print('Error')