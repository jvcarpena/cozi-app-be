import logging
import os
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


if True:

    engine = create_engine(db_url, pool_pre_ping=True) if (db_url := os.environ.get("DB_URL")) else None

    logging.basicConfig()

    logging.getLogger("sqalchemy.engine").setLevel(logging.INFO)


def get_auto_session():

    with Session(engine) as session:

        yield session


AutoSession = Annotated[Session, Depends(get_auto_session)]
