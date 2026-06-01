import pytest

from core.models.resort_amenity import ResortAmenity, ResortAmenityCategoryEnum
from core.models.resort_review import ResortReview


@pytest.fixture
def resort_review(db_session, resort, guest):
    db_session.add(
        fake_resort_review := ResortReview(
            resort_id=resort.id,
            guest_id=guest.id,
            overall_rating=4,
            cleanliness_rating=4,
            value_rating=4,
        )
    )

    db_session.commit()

    yield fake_resort_review


@pytest.fixture
def resort_amenities_entertainment(db_session, resort):
    entertainment = ["videoke", "billiards", "dart"]

    entertainment_amenities = None

    for name in entertainment:
        db_session.add(
            entertainment_amenities := ResortAmenity(
                resort_id=resort.id,
                category=ResortAmenityCategoryEnum.ENTERTAINMENT,
                name=name,
            )
        )

    db_session.commit()

    yield entertainment_amenities


@pytest.fixture
def resort_amenities_pool(db_session, resort):
    pool = ["kiddie pool", "adult pool", "pool slide"]

    pool_amenities = None

    for name in pool:
        db_session.add(
            pool_amenities := ResortAmenity(
                resort_id=resort.id,
                category=ResortAmenityCategoryEnum.POOL,
                name=name,
            )
        )

    db_session.commit()

    yield pool_amenities


@pytest.fixture
def resort_amenities_dining(db_session, resort):
    dining = ["dirty kitchen", "bbq grill", "dining kitchen"]

    dining_amenities = None

    for name in dining:
        db_session.add(
            dining_amenities := ResortAmenity(
                resort_id=resort.id,
                category=ResortAmenityCategoryEnum.DINING,
                name=name,
            )
        )

    db_session.commit()

    yield dining_amenities


@pytest.fixture
def resort_amenities_utility(db_session, resort):
    utilities = ["internet wifi", "parking", "staff"]

    utility_amenities = None

    for name in utilities:
        db_session.add(
            utility_amenities := ResortAmenity(
                resort_id=resort.id,
                category=ResortAmenityCategoryEnum.UTILITIES,
                name=name,
            )
        )

    db_session.commit()

    yield utility_amenities
