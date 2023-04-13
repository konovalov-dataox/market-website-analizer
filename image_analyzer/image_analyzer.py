import os
import shutil
import threading
import time
from logging import INFO

import cv2
import fiftyone as fo
import fiftyone.zoo as foz
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

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
        self.logger.info('ANALYZER CREATED')

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
        images_dataset = self.__create_dataset_list_from_folder_files(
            folder_name=folder_name,
        )
        self.logger.info(f'CREATED THE IMAGES DATASET FROM FOLDER | {folder_name}')
        unique_adverts_count = self.__get_unique_images_number(
            images_dataset=images_dataset,
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
            images_dataset: fo.Dataset,
            filter_name: str,
    ) -> int:
        self.logger.info(f'STARTED TO COMPARE THE IMAGES | {filter_name}')
        samples_to_remove = set()
        samples_to_keep = set()
        model = foz.load_zoo_model("inception-v3-imagenet-torch")
        embeddings = images_dataset.compute_embeddings(model)
        similarity_matrix = cosine_similarity(embeddings)
        similarity_matrix_length = len(similarity_matrix)
        similarity_matrix = similarity_matrix - np.identity(similarity_matrix_length)
        id_map = [s.id for s in images_dataset.select_fields(["id"])]
        filepath_map = {s.id: s.filepath for s in images_dataset.select_fields(["id", "filepath"])}

        for idx, sample in enumerate(images_dataset):
            if sample.id not in samples_to_remove:

                if idx % 100 == 0:
                    self.logger.info(f'HANDLING THE IMAGE #: {idx}  | {filter_name}')

                samples_to_keep.add(sample.id)

                dup_idxs = np.where(similarity_matrix[idx] > MINIMUM_UNIQUENESS_COEFFICIENT)[0]

                for dup in dup_idxs:
                    post_moderation_file_name = (
                        f'{sample.filepath.split("/")[-1].split(".")[0]}_'
                        f'{filepath_map[id_map[dup]].split("/")[-1].split(".")[0]}.png'
                    )
                    filepath = f'{POST_MODERATION_FOLDER}/{filter_name}_{post_moderation_file_name}'
                    self.__create_post_moderation_view(
                        first_image_path=sample.filepath,
                        second_image_path=filepath_map[id_map[dup]],
                        filepath=filepath,
                    )
                    samples_to_remove.add(id_map[dup])

                if len(dup_idxs) > 0:
                    sample.tags.append("has_duplicates")
                    sample.save()
            else:
                sample.tags.append("duplicate")
                sample.save()

        return len(samples_to_keep)

    @staticmethod
    def __create_post_moderation_view(
            first_image_path: str,
            second_image_path: str,
            filepath: str,
            title: str = 'Similar images',
    ) -> None:
        try:
            for image_index, image_path in enumerate([first_image_path, second_image_path]):
                image = cv2.imread(image_path)
                figure = plt.figure(title)
                figure.add_subplot(1, 2, image_index + 1)
                plt.imshow(image, cmap=plt.cm.gray)
                plt.axis("off")
                plt.savefig(filepath)
        except BaseException:
            pass

    @staticmethod
    def __create_dataset_list_from_folder_files(
            folder_name: str,
    ) -> fo.Dataset:
        return fo.Dataset.from_dir(
            dataset_dir=folder_name,
            dataset_type=fo.types.ImageDirectory,
        )

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


if __name__ == '__main__':
    image_analyzer = ImageAnalyzer()
    image_analyzer.start()
