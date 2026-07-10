import re

def stdCityName(city: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", city)