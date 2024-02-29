import pydantic

class Str(pydantic.BaseModel):
    value: str

def split_list(lst, n):
    division = len(lst) / float(n)
    return [lst[int(round(division * i)): int(round(division * (i + 1)))] for i in range(n)]