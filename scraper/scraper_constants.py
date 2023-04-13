# URLS

GRAPHQL_URL = 'https://sa.aqar.fm/graphql'


# URLS CONTAINERS

SA_AQAR_IMAGE_URL_CONTAINER = 'https://images.aqar.fm/webp/300x0/props/{image_id}'


# PAYLOADS

JSON = {
    "operationName": "findListings",
    "variables": {
        "size": 50,
        "from": 0,
        "sort": {
            "create_time": "desc",
            "has_img": "desc",
        },
        "where": {
            "category": {
                "eq": 3,
            },
            "city_id": {
                "eq": 21,
            }
        }
    },
    "query": "query findListings($size: Int, $from: Int, $sort: SortInput, $where: WhereInput, "
             "$polygon: [LocationInput!]) {\n  Web {\n    find(size: $size, from: $from, sort: $sort, "
             "where: $where, polygon: $polygon) {\n      ...WebResults\n      __typename\n    }\n    "
             "__typename\n  }\n}\n\nfragment WebResults on WebResults {\n  listings {\n    user_id\n"
             "    id\n    uri\n    title\n    price\n    content\n    imgs\n    refresh\n    category\n"
             "    beds\n    livings\n    wc\n    area\n    type\n    street_width\n    age\n    "
             "last_update\n    street_direction\n    ketchen\n    ac\n    furnished\n    location"
             " {\n      lat\n      lng\n      __typename\n    }\n    path\n    user {\n      "
             "review\n      img\n      name\n      phone\n      iam_verified\n      rega_id\n"
             "      __typename\n    }\n    native {\n      logo\n      title\n      image\n"
             "      description\n      external_url\n      __typename\n    }\n    "
             "rent_period\n    city\n    district\n    width\n    length\n    "
             "advertiser_type\n    create_time\n    __typename\n  }\n  "
             "total\n  __typename\n}\n"}


# HEADERS

HEADERS = {
    'authority': 'sa.aqar.fm',
    'accept': '*/*',
    'accept-language': 'en-US;q=0.9,en;q=0.8',
    'app-version': '0.16.18',
    'cache-control': 'no-cache',
    'content-type': 'application/json',
    'dpr': '1.25',
    'origin': 'https://sa.aqar.fm',
    'pragma': 'no-cache',
    'referer': 'https://sa.aqar.fm/%D9%81%D9%84%D9%84-%D9%84%D9%84%D8%A8%D9%8A%D8%B9/'
               '%D8%A7%D9%84%D8%B1%D9%8A%D8%A7%D8%B6/{}',
    'req-app': 'web',
    'req-device-token': '0a202155-f253-4aba-878c-70eaa72c54d6',
    'sec-ch-ua': '"Opera";v="89", "Chromium";v="103", "_Not:A-Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'viewport-width': '572',
}


# SCRAPER CONSTANTS

ADVERTS_PER_REQUEST_AMOUNT = 50

ADVERTS_SKIP_INCREMENT_VALUE = 50

UNIQUE_ADVERTS_INIT_VALUE = 0
