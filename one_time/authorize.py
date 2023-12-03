import asyncio

from glQiwiApi import YooMoneyAPI


async def get_url_to_auth() -> None:
    # Get a link for authorization, follow it if we get invalid_request or some kind of error
    # means either the scope parameter is incorrectly passed, you need to reduce the list of rights or try to recreate the application
    print(await YooMoneyAPI.build_url_for_auth(
        # For payments, account verification and payment history, you need to specify scope = ["account-info", "operation-history", "operation-details", "payment-p2p"]
        scope=["account-info", "operation-history"],
        client_id='ID received when registering the application above',
        redirect_uri='the link specified during registration above in the Redirect URI field'
    ))


asyncio.run(get_url_to_auth())