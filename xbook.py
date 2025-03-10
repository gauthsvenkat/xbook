import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

import typer
from dateparser import parse
from google.oauth2 import service_account
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from requests import Response, Session, get
from requests.exceptions import HTTPError
from rich.logging import RichHandler
from typer import Option, Typer
from typing_extensions import Annotated, Optional
from zoneinfo import ZoneInfo

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)

LOGGER = logging.getLogger("rich")

DOMAIN: str = "backbone-web-api.production.delft.delcom.nl"
HOST: str = f"https://{DOMAIN}"
AUTH_ENDPOINT: str = f"{HOST}/auth?cf=0"
BOOKING_ENDPOINT: str = f"{HOST}/participations"


def validate_when(when: str) -> datetime:
    slot_time: Optional[datetime] = parse(
        when, settings={"PREFER_DATES_FROM": "future"}
    )

    if not slot_time:
        raise typer.BadParameter("Couldn't parse datetime.")

    if any([slot_time.minute, slot_time.second, slot_time.microsecond]):
        raise typer.BadParameter("Please specify upto the hour.")

    if not slot_time.tzinfo:
        slot_time = slot_time.replace(tzinfo=ZoneInfo("Europe/Amsterdam"))

    if slot_time < datetime.now(tz=slot_time.tzinfo):
        raise typer.BadParameter("Please specify a time in the future.")

    return slot_time


def day_start(some_datetime: datetime) -> datetime:
    return some_datetime.replace(hour=0, minute=0, second=0, microsecond=0)


def day_end(some_datetime: datetime) -> datetime:
    return some_datetime.replace(hour=23, minute=0, second=0, microsecond=0)


def to_utc_str(some_datetime: datetime) -> str:
    return (
        some_datetime.astimezone(ZoneInfo("UTC"))
        .replace(tzinfo=None)
        .isoformat(timespec="milliseconds")
        + "Z"
    )


def raise_for_status(response: Response) -> None:
    try:
        response.raise_for_status()
    except HTTPError as e:
        LOGGER.error(f"Response: {response.text}")
        raise e


def available_slots_for_day(slot_time: datetime) -> list[dict]:
    now_str: str = to_utc_str(datetime.now())
    start_str: str = to_utc_str(day_start(slot_time))
    end_str: str = to_utc_str(day_end(slot_time))

    LOGGER.info(f"Get available slots between {start_str} and {end_str} at {now_str}")

    url: str = (
        "https://backbone-web-api.production.delft.delcom.nl/bookable-s"
        + f"lots?s=%7B%22startDate%22:%22{start_str}%22,%22endDate%22"
        + f":%22{end_str}%22,%22tagIds%22:%7B%22$in%22:%5B28%5D%7D,%2"
        + f"2availableFromDate%22:%7B%22$gt%22:%22{now_str}%22%7D,%22"
        + f"availableTillDate%22:%7B%22$gte%22:%22{now_str}%22%7D%7D"
    )

    response: Response = get(url)
    raise_for_status(response)

    slots: list[dict] = response.json()["data"]

    return slots


def get_slot_if_available(slot_time: datetime) -> Optional[dict]:
    slot: dict = next(
        slot
        for slot in available_slots_for_day(slot_time)
        if slot["startDate"] == to_utc_str(slot_time)
    )

    return slot if slot["isAvailable"] else None


def attempt_booking(slot_time: datetime, username: str, password: str) -> bool:
    LOGGER.info(f"Attempting to book slot on {slot_time.date()} at {slot_time.hour}h.")

    if not (slot := get_slot_if_available(slot_time)):
        LOGGER.info("Requested slot is not available... yet.")
        return False

    LOGGER.info("Requested slot seems available.")

    with Session() as sess:
        response: Response = sess.post(
            AUTH_ENDPOINT, data={"email": username, "password": password}
        )
        raise_for_status(response)
        LOGGER.info("Authenticated successfully. Getting member ID...")

        sess.headers.update(
            {
                "authorization": f"Bearer {response.json()['access_token']}",
                "authority": DOMAIN,
            }
        )

        response = sess.get(AUTH_ENDPOINT)
        raise_for_status(response)

        member_id: str = response.json()["id"]

        LOGGER.info(f"Received member ID: {member_id}. Attempting to book slot...")

        response = sess.post(
            BOOKING_ENDPOINT,
            json={
                "memberId": member_id,
                "bookingId": slot["bookingId"],
                "params": {
                    "startDate": slot["startDate"],
                    "endDate": slot["endDate"],
                    "bookableProductId": slot["bookableProductId"],
                    "bookableLinkedProductId": slot["linkedProductId"],
                    "bookingID": slot["bookingId"],
                    "invitedMemberEmails": [],
                    "invitedGuests": [],
                    "invitedOthers": [],
                },
            },
        )

        raise_for_status(response)

    return response.ok


@(app := Typer()).command()
def xbook(
    username: Annotated[str, Option(envvar="X_USERNAME", prompt=True)],
    password: Annotated[str, Option(envvar="X_PASSWORD", prompt=True)],
    when: Annotated[str, Option(prompt=True, callback=validate_when)] = "7am",
    sleep_interval: int = 60 * 1,
    service_account_file: Optional[str] = "credentials.json",
) -> None:
    slot_time: datetime = cast(datetime, when)

    while not attempt_booking(slot_time, username, password):
        LOGGER.info(f"Retrying in {sleep_interval} seconds.")
        time.sleep(sleep_interval)

    LOGGER.info(
        f"Successfully booked slot {slot_time.date()} at {slot_time.hour}h (Europe/Amsterdam)"
    )

    if (
        service_account_file
        and Path(service_account_file).exists()
        and (
            calendar := build(
                "calendar",
                "v3",
                credentials=service_account.Credentials.from_service_account_file(
                    service_account_file
                ),
            )
        )
    ):
        LOGGER.info("Attempting to add event to calendar.")

        calendar.events().insert(
            calendarId=username,
            body={
                "summary": "Gym",
                "location": "Mekelweg 8-10, 2628 CD Delft",
                "start": {"dateTime": to_utc_str(slot_time), "timeZone": "UTC"},
                "end": {
                    "dateTime": to_utc_str(slot_time + timedelta(hours=1, minutes=30)),
                    "timeZone": "UTC",
                },
            },
        ).execute()

        LOGGER.info(f"Event added to calendar {username}")


if __name__ == "__main__":
    app()
