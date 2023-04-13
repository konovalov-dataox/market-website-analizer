import asyncio
import io
import json
import time
from copy import deepcopy
from logging import INFO
from urllib.parse import (
    urlparse,
    unquote,
)

import PIL.Image as Image
import aiohttp as aiohttp
import fake_useragent

from config import (
    IMAGES_DOWNLOADER_MAX_REQUEST_RETRIES,
    PROXY_STRING,
)
from constants import (
    RUN_SETTINGS_LIST,
    IS_LAST_PAGE_HANDLED_KEY,
    IS_IMAGES_DOWNLOADED_KEY,
    UNIQUE_ADVERTS_KEY,
    INCREMENT_VALUE,
)
from image_downloader_constants import (
    IMAGE_RESIZE_HEIGHT,
    IMAGE_RESIZE_WIDTH,
    HEADERS,
)
from utils.logger import LoggerFactory
from utils.proxy import Proxy
from utils.redis_client import RedisClient


class ImageDownloader:

    def __init__(self):
        self.logger = LoggerFactory.get_logger(
            name='IMAGE DOWNLOADER',
            log_level=INFO,
        )
        self.proxy = Proxy.from_string(PROXY_STRING)
        self.user_agent_faker = fake_useragent.UserAgent()
        self.redis_client = RedisClient()
        self.already_downloaded_imgs = dict()
        self.logger.info('IMAGE DOWNLOADER CREATED')

    async def start(self) -> None:
        self.__preset_images_dict()

        while True:
            for run_settings in RUN_SETTINGS_LIST:

                if self.__check_if_already_downloaded(
                    filter_name=run_settings["filter_name"],
                ):
                    continue

                await self.__download_images(
                    run_settings=run_settings,
                )

            time.sleep(5)

    async def __download_images(
            self,
            run_settings: dict,
    ) -> None:
        tasks = list()
        step = 100
        notify = False

        while True:
            is_last_page_handled = self.redis_client.hash_get(
                main_key=run_settings["filter_name"],
                inner_key=IS_LAST_PAGE_HANDLED_KEY,
            )
            img_dict_as_str = self.redis_client.left_pop(
                key=f'{run_settings["filter_name"]}_images'
            )

            if img_dict_as_str:
                img_dict = json.loads(img_dict_as_str)
                tasks.append(
                    self.__download_the_image(
                        img_dict=img_dict,
                    )
                )
            elif not img_dict_as_str and is_last_page_handled:
                notify = True
                break
            else:
                break

        for skip in range(0, len(tasks), step):
            results = await asyncio.gather(*tasks[skip:skip + step])

            for downloaded in results:
                if not downloaded:
                    self.__increment_unique_adverts_amount(
                        main_key=run_settings["filter_name"],
                    )

        if notify:
            self.__notify_images_downloaded(
                filter_name=run_settings["filter_name"],
            )

    async def __download_the_image(
            self,
            img_dict: dict,
    ) -> bool:
        async with aiohttp.ClientSession() as session:
            for retry_number in range(IMAGES_DOWNLOADER_MAX_REQUEST_RETRIES):
                try:
                    self.logger.info(f'DOWNLOAD: {img_dict["image_url"]} | {img_dict["filter_name"]}')
                    img_unique_name = unquote(
                        urlparse(img_dict["image_url"])
                            .path
                            .split("/")[-1]
                    )
                    filename = f'{img_dict["filter_name"]}/{img_unique_name}'

                    async with session.get(
                        url=img_dict["image_url"],
                        headers=self.__create_request_headers(),
                        timeout=30,
                    ) as response:
                        image = Image.open(
                            io.BytesIO(await response.read())
                        )
                        image = image.resize(
                            (
                                IMAGE_RESIZE_WIDTH,
                                IMAGE_RESIZE_HEIGHT,
                            ),
                            Image.LANCZOS,
                        )
                        image.save(filename)
                        return True
                except BaseException:
                    if retry_number + 1 >= IMAGES_DOWNLOADER_MAX_REQUEST_RETRIES:
                        self.logger.info(
                            f'Cannot download the image with url {img_dict["image_url"]}'
                            f' | {img_dict["filter_name"]}'
                        )

            return False

    def __check_if_already_downloaded(
            self,
            filter_name: str,
    ) -> bool:
        if self.redis_client.hash_get(
            main_key=filter_name,
            inner_key=IS_IMAGES_DOWNLOADED_KEY,
        ):
            return True
        else:
            return False

    def __create_request_headers(self) -> dict:
        headers = deepcopy(HEADERS)
        headers["user-agent"] = self.user_agent_faker.random
        return headers

    def __increment_unique_adverts_amount(
            self,
            main_key: str,
    ):
        self.redis_client.hash_increase(
            main_key=main_key,
            inner_key=UNIQUE_ADVERTS_KEY,
            value=INCREMENT_VALUE,
        )

    def __notify_images_downloaded(
            self,
            filter_name: str,
    ) -> None:
        self.redis_client.hash_set(
            main_key=filter_name,
            inner_key=IS_IMAGES_DOWNLOADED_KEY,
            value=True,
        )

    def __preset_images_dict(self) -> None:
        for run_settings in RUN_SETTINGS_LIST:
            self.already_downloaded_imgs[f'{run_settings["filter_name"]}'] = list()


if __name__ == '__main__':
    image_downloader = ImageDownloader()
    asyncio.get_event_loop().run_until_complete(image_downloader.start())
