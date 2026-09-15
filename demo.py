from piuudc.numbers import clamp
from piuudc.text import slugify


if __name__ == "__main__":
    print(slugify("Pii UDC Utility Demo"))
    print(clamp(14, 0, 10))
