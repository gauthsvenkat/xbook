import click
import urllib3
from auth import AuthMethod
from booking import login_and_book_slot

# The certificate for x.tudelft.nl is untrusted, which produces many warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@click.command()
@click.option(
    "--date",
    prompt="Date (YYYY-MM-DD)",
    help="The date on which you want to book a time slot.",
    type=str,
)
@click.option(
    "--hour",
    prompt="Hour",
    help="The hour at which your desired slot commences.",
    type=int,
)
@click.option(
    "--email",
    prompt="Email",
    help="The email you use to log in to X's website.",
    type=str,
    envvar="X_EMAIL",
)
@click.password_option(
    "--password",
    prompt="Password",
    help="The password you use to log in to X's website.",
    envvar="X_PASSWORD",
)
def cli(**kwargs):
    login_and_book_slot(
        kwargs["email"],
        kwargs["password"],
        "",
        AuthMethod.OTHER,
        kwargs["date"],
        kwargs["hour"],
        False,
    )


if __name__ == "__main__":
    cli()
