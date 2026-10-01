from dataclasses import dataclass
from pydantic import BaseModel

@dataclass
class FileContext:
    path:str
    content:str
    language:str



class CodeChunk(BaseModel):
    file_path: str
    chunk_type: str
    name: str
    content: str
    line_start:int
    line_end: int

    