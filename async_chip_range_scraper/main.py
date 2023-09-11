import asyncio

import aiofiles
import aiohttp

from aiocsv import AsyncWriter
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


async def get_elements(session: aiohttp.ClientSession,
                       url: str,
                       page: int) -> list[list]:
    """
    Собирает номенклатуру со страницы

    :param session:
    :param url:
    :param page:
    :return: Список списков, во вложенных списках хранятся данные о производителе и названии
    """
    response = await session.get(url)
    content = await response.text()
    soup = BeautifulSoup(content, "lxml")
    components_names = soup.find_all('h2', class_='woocommerce-loop-product__title')
    components_developers = soup.find_all('p', class_='categories')
    names = [name.text for name in components_names]
    developers = [developer.text for developer in components_developers]
    items = [list(pair) for pair in zip(names, developers)]
    print(f'Обрабатывается страница: {page}')
    return items


async def scrape_data() -> None:
    """
    Основная функция, создаёт .csv файл на запись
    :return: Возвращает пользователю готовый .csv со всей собранной номенклатурой
    """
    async with aiofiles.open(f'data/chip_range.csv', 'w', encoding='utf-8-sig', newline='') as file:
        writer = AsyncWriter(file, delimiter=';')
        await writer.writerow(
            ('Название',
             "Производитель"
             )
        )

    ua = UserAgent()
    headers = {
        'accept': '*/*',
        'user-agent': ua.google,
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        semaphore = asyncio.Semaphore(10)  # Ставим лимит на количество корутин
        tasks = []
        for i in range(1, 500):
            chip_url = f'https://chip-range.com/products/?product-page={i}'
            tasks.append(get_elements_with_semaphore(session, chip_url, i, semaphore))

        results = await asyncio.gather(*tasks)

        for result in results:
            for item in result:
                async with aiofiles.open(f'data/chip_range.csv', 'a', encoding='utf-8-sig', newline='') as file:
                    writer = AsyncWriter(file, delimiter=';')
                    await writer.writerow(
                        (
                            f'{item[0]}',
                            f'{item[1]}'
                        )
                    )

    print('Программа завершена')


async def get_elements_with_semaphore(session: aiohttp.ClientSession,
                                      url: str,
                                      page: int,
                                      semaphore: asyncio.Semaphore) -> get_elements:
    """
    Ограничивает количество корутин (max: 10 корутин одновременно)

    :param session:
    :param url:
    :param page:
    :param semaphore:
    :return: Вызывает функцию get_elements
    """
    async with semaphore:
        await asyncio.sleep(4)
        return await get_elements(session, url, page)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(scrape_data())
