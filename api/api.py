import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter

from constants import RUN_SETTINGS_LIST
from scraper.tasks import collect_photos

app = FastAPI()
router = InferringRouter()


@cbv(router)
class TaskAPI:
    SUCCESSFUL_RESPONSE = {
        'started': 'YES',
    }
    UNSUCCESSFUL_RESPONSE = {
        'started': 'NO',
        'reason': 'MISSING_HEADERS',
    }
    UNIQUE_HEADER = 'admin-run'

    @router.get("/")
    async def docs_redirect(self):
        return RedirectResponse(url='/docs')

    @router.post(
        path="/start",
        status_code=200,
    )
    async def start(
            self,
            data: Request,
    ):
        if self.UNIQUE_HEADER not in data.headers.keys():
            return self.UNSUCCESSFUL_RESPONSE

        for run_settings in RUN_SETTINGS_LIST:
            collect_photos.delay(
                filter_name=run_settings['filter_name'],
                category_id=run_settings['category_id'],
                city_id=run_settings['city_id'],
            )

        return self.SUCCESSFUL_RESPONSE


app.include_router(router)

if __name__ == '__main__':
    uvicorn.run(app)
