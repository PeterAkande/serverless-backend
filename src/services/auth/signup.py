import datetime
import json
import logging
import traceback

from pydantic import ValidationError

from proxy_response_handler.api_exception import APIServerError
from models.user import UserSignUp, User
from proxy_response_handler.simple_response import SimpleResponse
from decorators.authentication_n_authorizer_decorator import cordin8_api
from utils.cognito_utils import Cordin8CognitoHandler
from utils.dynamo_db_handlers.user_db_handler import save_user_details

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@cordin8_api(authorized=False)
def lambda_handler(event, context, access_token=None):
    try:
        body = json.loads(event.get("body", {}))
    except Exception as e:
        traceback.print_exc()

        return APIServerError("Bad Request, Cant parse body", status_code=400)
    try:
        user_sign_up_model = UserSignUp(**body)
    except ValidationError as e:
        traceback.print_exc()
        return APIServerError("Bad Request, Cant parse body", status_code=400)

    except Exception as e:
        traceback.print_exc()

        return APIServerError("Bad Request, Cant parse body", status_code=400)

    cognito_handler = Cordin8CognitoHandler()

    signed_up, error = cognito_handler.sign_up_user(user=user_sign_up_model)

    if not signed_up:
        logger.info(f'Error signing up is {error}')
        return APIServerError(error, status_code=400)
    (
        email_verified,
        user_id,
        phone_verified,
    ) = cognito_handler.get_user_details_from_cognito(email=user_sign_up_model.email)

    if user_id is None:
        return APIServerError("An Error occurred", status_code=400)

    date_created = datetime.datetime.now().isoformat()
    user_details = {**user_sign_up_model.model_dump(), "user_id": user_id, 'date_created': date_created,
                    'is_verified': False}

    logger.info(f"User Details ot be parses is: {user_details}")
    user = User(**user_details)
    saved_successfully = save_user_details(user)

    if not saved_successfully:
        return APIServerError("An Unknown Error occurred", status_code=500)

    return SimpleResponse(
        body={"message": "User Registered, check email for verification code", "user": user.model_dump()},
        status_code=200,
    )
