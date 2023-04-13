import io
import json
import os
import time
from copy import deepcopy
from logging import INFO
from urllib.parse import (
    urlparse,
    unquote,
)

import PIL.Image as Image
import fake_useragent
import requests

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
from image_downloader.constants import (
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
            name='Image Downloader',
            log_level=INFO,
        )
        self.proxy = Proxy.from_string(PROXY_STRING)
        self.user_agent_faker = fake_useragent.UserAgent()
        self.redis_client = RedisClient()

    def start(self) -> None:
        self.__preset_images_dict()

        while True:
            for run_settings in RUN_SETTINGS_LIST:

                if self.__check_if_already_downloaded(
                    filter_name=run_settings["filter_name"],
                ):
                    continue

                self.__download_images(
                    run_settings=run_settings,
                )

            time.sleep(5)

    def __download_images(
            self,
            run_settings: dict,
    ) -> None:
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
                downloaded = self.__download_the_image(
                    img_dict=img_dict,
                )

                if not downloaded:
                    self.__increment_unique_adverts_amount(
                        main_key=run_settings["filter_name"],
                    )
            elif not img_dict_as_str and is_last_page_handled:
                self.__notify_images_downloaded(
                    filter_name=run_settings["filter_name"],
                )
                break
            else:
                break

    def __download_the_image(
            self,
            img_dict: dict,
    ) -> bool:
        for retry_number in range(IMAGES_DOWNLOADER_MAX_REQUEST_RETRIES):
            try:
                self.logger.info(f'DOWNLOAD: {img_dict["image_url"]} | {img_dict["filter_name"]}')
                img_unique_name = unquote(
                    urlparse(img_dict["image_url"])
                        .path
                        .split("/")[-1]
                )
                filename = f'{img_dict["filter_name"]}/{img_unique_name}'
                response = requests.get(
                    url=img_dict["image_url"],
                    headers=self.__create_request_headers(),
                )

                image = Image.open(
                    io.BytesIO(response.content)
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
