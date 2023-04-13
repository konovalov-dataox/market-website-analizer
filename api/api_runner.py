import requests


def send_api_task(
        ip_address: str,
) -> None:
    response = requests.post(
        url=f'http://{ip_address}:8000/start',
        headers={
            'accept': 'application/json',
            'admin-run': 'true',
        }
    )
    print(response.json())


if __name__ == '__main__':
    send_api_task(
        ip_address='localhost',
    )
