import os
import shutil
import time
from logging import INFO
from typing import (
    List,
    Any,
)
import threading
import cv2
import matplotlib.pyplot as plt
from skimage.metrics import structural_similarity

from config import (
    MINIMUM_UNIQUENESS_COEFFICIENT,
    POST_MODERATION_FOLDER,
)
from constants import (
    RUN_SETTINGS_LIST,
    IS_IMAGES_DOWNLOADED_KEY,
    IS_FOLDER_ANALYZED_KEY,
    UNIQUE_ADVERTS_KEY,
)
from utils.logger import LoggerFactory
from utils.redis_client import RedisClient


class ImageAnalyzer:

    def __init__(self):
        self.logger = LoggerFactory.get_logger(
            name='ANALYZER',
            log_level=INFO,
            log_file='ANALYZER.log',
        )
        self.redis_client = RedisClient()
        self.__clean_folder()

    def start(self) -> None:
        while True:
            for run_settings in RUN_SETTINGS_LIST:

                if self.__check_if_already_downloaded_and_not_analyzed(
                    filter_name=run_settings["filter_name"],
                ):
                    self.__notify_folder_analyze_started(
                        filter_name=run_settings['filter_name'],
                    )
                    analyze_thread = threading.Thread(
                        target=self.__analyze_folder_and_get_unique_adverts_number,
                        name=f"Analyzer | {run_settings['filter_name']}",
                        args=(run_settings["filter_name"], ),
                    )
                    analyze_thread.start()

            time.sleep(5)

    def __analyze_folder_and_get_unique_adverts_number(
            self,
            folder_name: str,
    ) -> None:
        images_list = self.__create_images_list_from_folder_files(
            folder_name=folder_name,
        )
        self.logger.info(f'CREATED THE IMAGES INSTANCES FROM FOLDER | {folder_name}')
        images_list = self.__change_images_color_to_gray(
            images_list=images_list,
        )
        self.logger.info(f'CHANGED THE IMAGES COLOR TO GRAY | {folder_name}')
        unique_adverts_count = self.__get_unique_images_number(
            images_list=images_list,
            filter_name=folder_name,
        )
        self.logger.info(f'UNIQUE ADVERTS FOUND: {unique_adverts_count} | {folder_name}')
        self.__notify_folder_analyzed(
            filter_name=folder_name,
            unique_adverts_count=unique_adverts_count,
        )
        self.logger.info(f'ANALYZE COMPLETED | {folder_name}')

    def __get_unique_images_number(
            self,
            images_list: list,
            filter_name: str,
    ) -> int:
        self.logger.info(f'STARTED TO COMPARE THE IMAGES | {filter_name}')
        len_of_image_list_with_possible_duplicates = len(images_list)
        duplicates_amount = 0

        while len(images_list) != 0:
            for _ in range(len(images_list)):
                for comparable_image_index in range(len(images_list[1:])):
                    try:
                        current_image_index = 0
                        s_sim_coefficient = self.__is_images_identical(
                            first_image=images_list[current_image_index]['image'],
                            second_image=images_list[comparable_image_index + 1]['image'],
                        )

                        if s_sim_coefficient >= MINIMUM_UNIQUENESS_COEFFICIENT:
                            duplicates_amount += 1
                            post_moderation_file_name = (
                                f'{images_list[current_image_index]["image_file"].split(".")[0]}_'
                                f'{images_list[comparable_image_index + 1]["image_file"].split(".")[0]}.png'
                            )
                            filepath = f'{POST_MODERATION_FOLDER}/{filter_name}_{post_moderation_file_name}'
                            self.__create_post_moderation_view(
                                first_image=images_list[current_image_index]['image'],
                                second_image=images_list[comparable_image_index + 1]['image'],
                                s_sim_coefficient=s_sim_coefficient,
                                filepath=filepath,
                            )
                            images_list.pop(comparable_image_index + 1)
                            break
                    except BaseException as e:
                        self.logger.exception(e)
                else:
                    images_list.pop(0)

        return len_of_image_list_with_possible_duplicates - duplicates_amount

    @staticmethod
    def __create_post_moderation_view(
            first_image: Any,
            second_image: Any,
            s_sim_coefficient: float,
            filepath: str,
            title: str = 'Similar images',
    ) -> None:
        try:
            for image_index, image in enumerate([first_image, second_image]):
                figure = plt.figure(title)
                plt.suptitle(f"Structural similarity coefficient: {s_sim_coefficient}")
                figure.add_subplot(1, 2, image_index + 1)
                plt.imshow(image, cmap=plt.cm.gray)
                plt.axis("off")
                plt.savefig(filepath)
        except BaseException:
            pass

    @staticmethod
    def __is_images_identical(
            first_image: Any,
            second_image: Any,
    ) -> float:
        return structural_similarity(
            im1=first_image,
            im2=second_image,
        )

    @staticmethod
    def __create_images_list_from_folder_files(
            folder_name: str,
    ) -> List[dict]:
        images_list = list()

        for image_file in os.listdir(folder_name):
            images_list.append(
                {
                    'image_file': image_file,
                    'image': cv2.imread(f'{folder_name}/{image_file}'),
                }
            )

        return images_list

    @staticmethod
    def __change_images_color_to_gray(
            images_list: List[dict],
    ) -> list:
        for image_dict in images_list:
            image_dict['image'] = cv2.cvtColor(
                image_dict['image'],
                cv2.COLOR_BGR2GRAY,
            )

        return images_list

    def __notify_folder_analyze_started(
            self,
            filter_name: str,
    ) -> None:
        self.redis_client.hash_set(
            main_key=filter_name,
            inner_key=IS_FOLDER_ANALYZED_KEY,
            value='started',
        )
        self.logger.info(f'STARTED TO ANALYZE THE FOLDER | {filter_name}')

    def __notify_folder_analyzed(
            self,
            filter_name: str,
            unique_adverts_count: int,
    ) -> None:
        self.redis_client.hash_set(
            main_key=filter_name,
            inner_key=IS_FOLDER_ANALYZED_KEY,
            value=True,
        )
        self.redis_client.hash_increase(
            main_key=filter_name,
            inner_key=UNIQUE_ADVERTS_KEY,
            value=unique_adverts_count,
        )
        self.logger.info(f'UNIQUE ADVERTS FOUND: {unique_adverts_count} | {filter_name}')

    def __check_if_already_downloaded_and_not_analyzed(
            self,
            filter_name: str,
    ) -> bool:
        images_downloaded = self.redis_client.hash_get(
            main_key=filter_name,
            inner_key=IS_IMAGES_DOWNLOADED_KEY,
        )
        folder_analyzed = self.redis_client.hash_get(
            main_key=filter_name,
            inner_key=IS_FOLDER_ANALYZED_KEY,
        )
        if images_downloaded and not folder_analyzed:
            return True
        else:
            return False

    def __clean_folder(self) -> None:
        self.__remove_folder()
        self.__create_empty_folder()

    @staticmethod
    def __remove_folder() -> None:
        try:
            shutil.rmtree(POST_MODERATION_FOLDER)
        except FileNotFoundError:
            pass
        except shutil.Error:
            pass

    @staticmethod
    def __create_empty_folder() -> None:
        try:
            os.mkdir(POST_MODERATION_FOLDER)
        except OSError:
            pass

