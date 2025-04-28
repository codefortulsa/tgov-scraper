from typing import List, Tuple
from prefect import task

from src.download_minutes import download_minutes_pdfs
from src.models.minutes import Minutes


@task
async def get_new_minutes(last_minutes_page: int) -> Tuple[List[Minutes], int]:
    return download_minutes_pdfs(last_minutes_page)
