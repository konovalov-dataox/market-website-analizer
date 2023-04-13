import json
import os
import random
import shutil
from copy import deepcopy
from logging import INFO

import fake_useragent
import requests

from config import (
    SCRAPER_MAX_REQUEST_RETRIES,
    PROXY_STRING,
)
from constants import (
    IS_LAST_PAGE_HANDLED_KEY,
    UNIQUE_ADVERTS_KEY,
    INCREMENT_VALUE,
    IS_IMAGES_DOWNLOADED_KEY,
    IS_FOLDER_ANALYZED_KEY,
)
from scraper.scraper_constants import (
    ADVERTS_SKIP_INCREMENT_VALUE,
    SA_AQAR_IMAGE_URL_CONTAINER,
    ADVERTS_PER_REQUEST_AMOUNT,
    UNIQUE_ADVERTS_INIT_VALUE,
    GRAPHQL_URL,
    HEADERS,
    JSON,
)
from utils.logger import LoggerFactory
from utils.proxy import Proxy
from utils.redis_client import RedisClient


class Scraper:

    def __init__(
            self,
            filter_name: str,
            category_id: int,
            city_id: int,
    ):
        self.logger = LoggerFactory.get_logger(
            name='SCRAPER',
            log_level=INFO,
        )
        self.filter_name = filter_name
        self.adverts_images_list_key = f'{self.filter_name}_images'
        self.category_id = category_id
        self.city_id = city_id
        self.redis_client = RedisClient()
        self.proxy = Proxy.from_string(PROXY_STRING)
        self.user_agent_faker = fake_useragent.UserAgent()
        self.__clean_folder()
        self.__load_preset()
        self.logger.info('SCRAPER CREATED')

    def collect_photos(
            self,
            skip: int = 0,
            page: int = 0,
    ) -> None:
        while True:
            try:
                self.logger.info(f'{self.filter_name.upper()}: HANDLING PAGE: {page}')
                response = self.__send_page_request(
                    skip=skip,
                )
                response_json_body = response.json()
                adverts_list = response_json_body\
                    .get('data', {})\
                    .get('Web', {})\
                    .get('find', {})\
                    .get('listings', [])
                total_adverts_amount = response_json_body\
                    .get('data', {})\
                    .get('Web', {})\
                    .get('find', {})\
                    .get('total')
                self.logger.info(f'{self.filter_name.upper()}: TOTAL ADVERTS AMOUNT: {total_adverts_amount}')
            except ValueError:
                continue

            for advert in adverts_list:
                self.handle_advert(
                    advert=advert,
                )

            skip += ADVERTS_SKIP_INCREMENT_VALUE
            page += 1

            if not adverts_list:
                self.__notify_last_page()
                break

    def handle_advert(
            self,
            advert: dict,
    ) -> None:
        advert_images = advert.get('imgs', list())
        if advert_images:
            img_dict = {
                'filter_name': self.filter_name,
                'image_url': SA_AQAR_IMAGE_URL_CONTAINER.format(image_id=advert_images[0]),
            }
            self.redis_client.left_push(
                key=self.adverts_images_list_key,
                value=json.dumps(img_dict),
            )
        else:
            self.redis_client.hash_increase(
                main_key=self.filter_name,
                inner_key=UNIQUE_ADVERTS_KEY,
                value=INCREMENT_VALUE,
            )

    def __send_page_request(
            self,
            skip: int,
    ) -> requests.Response:
        for retry_number in range(SCRAPER_MAX_REQUEST_RETRIES):
            try:
                return requests.post(
                    url=GRAPHQL_URL,
                    headers=self.__create_request_headers(),
                    proxies=self.proxy.as_dict(),
                    data=self.__create_request_payload(
                        skip=skip,
                    ),
                )
            except BaseException as e:
                if retry_number + 1 >= SCRAPER_MAX_REQUEST_RETRIES:
                    raise e

    def __load_preset(self) -> None:
        self.redis_client.remove(
            key=self.adverts_images_list_key,
        )
        self.redis_client.hash_set(
            main_key=self.filter_name,
            inner_key=UNIQUE_ADVERTS_KEY,
            value=UNIQUE_ADVERTS_INIT_VALUE,
        )
        self.redis_client.hash_set(
            main_key=self.filter_name,
            inner_key=IS_LAST_PAGE_HANDLED_KEY,
            value=False,
        )
        self.redis_client.hash_set(
            main_key=self.filter_name,
            inner_key=IS_IMAGES_DOWNLOADED_KEY,
            value=False,
        )
        self.redis_client.hash_set(
            main_key=self.filter_name,
            inner_key=IS_FOLDER_ANALYZED_KEY,
            value=False,
        )
        self.logger.info('PRESET IS LOADED TO REDIS DB')

    def __clean_folder(self) -> None:
        self.__remove_folder()
        self.__create_empty_folder()

    def __remove_folder(self) -> None:
        try:
            for filename in os.listdir(self.filter_name):
                file_path = os.path.join(self.filter_name, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception:
                    pass
        except FileNotFoundError:
            pass
        except shutil.Error:
            pass

    def __create_empty_folder(self) -> None:
        try:
            if not os.path.isdir(self.filter_name):
                os.mkdir(self.filter_name)
        except OSError:
            pass

    def __notify_last_page(self) -> None:
        self.redis_client.hash_set(
            main_key=self.filter_name,
            inner_key=IS_LAST_PAGE_HANDLED_KEY,
            value=True,
        )

    def __create_request_headers(self) -> dict:
        headers = deepcopy(HEADERS)
        headers['referer'] = headers['referer'].format(random.randint(1, 2500))
        headers['user-agent'] = self.user_agent_faker.random
        return headers

    def __create_request_payload(
            self,
            skip: int,
    ) -> str:
        payload_dict = deepcopy(JSON)
        payload_dict['variables']['size'] = ADVERTS_PER_REQUEST_AMOUNT
        payload_dict['variables']['from'] = skip
        payload_dict['variables']['where']['category']['eq'] = self.category_id
        payload_dict['variables']['where']['city_id']['eq'] = self.city_id
        return json.dumps(payload_dict)
