from pydantic import BaseModel


class PreprocessRequest(BaseModel):
    image: str
    boundary: str


class PreprocessResponse(BaseModel):
    status: str
    output_dir: str
    ndvi: str
    steps: list[str]
