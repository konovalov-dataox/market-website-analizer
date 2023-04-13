import json
from typing import Any

import redis

from config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_PASSWORD,
    REDIS_WORK_DB,
    REDIS_KEYS_EXPIRE_TIME,
)


class RedisClient:

    def __init__(self):
        self._controller = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_WORK_DB,
            password=REDIS_PASSWORD,
        )

    def set(
            self,
            key: str,
            value: Any,
    ) -> None:
        bytes_value = self.__value_to_bytes(
            value=value,
        )
        self._controller.set(
            name=key,
            value=bytes_value,
            ex=REDIS_KEYS_EXPIRE_TIME,
        )

    def hash_set(
            self,
            main_key: str,
            inner_key: str,
            value: Any,
    ):
        bytes_value = self.__value_to_bytes(
            value=value,
        )
        self._controller.hset(
            main_key,
            inner_key,
            bytes_value,
        )

    def hash_increase(
            self,
            main_key: str,
            inner_key: str,
            value: int,
    ):
        if isinstance(value, int):
            self._controller.hincrby(
                main_key,
                inner_key,
                value,
            )

    def left_push(
            self,
            key: str,
            value: Any,
    ):
        bytes_value = self.__value_to_bytes(
            value=value,
        )
        self._controller.lpush(
            key,
            bytes_value,
        )

    def hash_get(
            self,
            main_key: str,
            inner_key: str,
    ) -> Any:
        bytes_value = self._controller.hget(
            name=main_key,
            key=inner_key,
        )

        if bytes_value:
            return json.loads(bytes_value)

    def left_pop(
            self,
            key: str,
            count: int = 1,
    ) -> Any:
        bytes_value = self._controller.lpop(
            name=key,
            count=count,
        )

        if bytes_value:

            if type(bytes_value) == list:
                return json.loads(bytes_value[0]) if count == 1 else bytes_value

            return json.loads(bytes_value)

    def check_if_task_exists(
            self,
            key: str,
    ) -> bool:
        return self._controller.exists(key)

    def remove(
            self,
            key: str,
    ) -> None:
        self._controller.delete(key)

    @staticmethod
    def __value_to_bytes(
            value: Any,
    ) -> bytes:
        return bytes(
            json.dumps(value).encode()
        )
