from decimal import Decimal
from typing import Annotated

from pydantic import Field, StringConstraints

# THE FIELD RULES OF A RESORT, SHARED BY THE CREATE AND THE UPDATE REQUESTS SO THEY CANNOT DRIFT APART.

ResortName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]

ResortDescription = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]

ResortAddress = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]

# THE PRICE COLUMNS ARE NUMERIC(12, 4), WHICH HOLDS AT MOST 8 DIGITS BEFORE THE DECIMAL POINT.
# max_digits ALONE WOULD LET 123456789012 THROUGH AND THE DATABASE WOULD FAIL WITH A 500.

ResortPrice = Annotated[Decimal, Field(gt=0, lt=Decimal("10000000"), decimal_places=4)]

ResortMaxGuests = Annotated[int, Field(ge=1, le=1000)]

ResortRoomCount = Annotated[int, Field(ge=1, le=100)]

Latitude = Annotated[Decimal, Field(ge=-90, le=90)]

Longitude = Annotated[Decimal, Field(ge=-180, le=180)]
