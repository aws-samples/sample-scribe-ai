import os
import time
import threading
from typing import Optional, List, Tuple
from flask import Blueprint, redirect, session, request, url_for, current_app, abort
from functools import wraps
from authlib.integrations.flask_client import OAuth
from datetime import timedelta
import boto3
from botocore.exceptions import ClientError
import logging

from shared.config import config
from shared.data.data_models import User, Interview


auth_bp = Blueprint('auth', __name__)

# Initialize Cognito Identity Provider client
cognito = boto3.client('cognito-idp')
secrets_client = boto3.client('secretsmanager')

# OAuth instance
oauth = None

# Cache for Cognito users
# Structure: (users_list, timestamp)
_users_cache: Tuple[List[User], float] = ([], 0)
_cache_lock = threading.Lock()
_CACHE_TTL_SECONDS = 15 * 60  # 15 minutes


def configure_auth(app):
    """Configure authentication settings and register the auth blueprint"""
    global oauth

    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Retrieve Flask secret key from AWS Secrets Manager
    response = secrets_client.get_secret_value(
        SecretId=config.flask_secret_key_name)
    app.secret_key = response['SecretString']
    logging.info(
        "Successfully retrieved Flask secret key from Secrets Manager")

    # Configure cookie-based sessions
    app.config['SESSION_COOKIE_NAME'] = 'scribe_session'
    app.config['SESSION_COOKIE_SECURE'] = os.getenv(
        'FLASK_ENV') != 'development'  # Secure in production
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Prevent CSRF
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
        days=1)  # Session expiry

    # Initialize OAuth
    oauth = OAuth(app)
    authority = f"https://cognito-idp.{config.region}.amazonaws.com/{config.cognito_pool_id}"

    oauth.register(
        name="oidc",
        authority=authority,
        client_id=config.client_id,
        client_secret=config.client_secret,
        server_metadata_url=f"{authority}/.well-known/openid-configuration",
        client_kwargs={'scope': 'email openid profile'}
    )

    # Register OAuth routes
    @app.route('/login')
    def login():
        return oauth.oidc.authorize_redirect(config.redirect_uri)

    @app.route('/auth/callback')
    def authorize():
        token = oauth.oidc.authorize_access_token()
        user = token['userinfo']
        user["username"] = user["cognito:username"]
        session['user'] = user
        return redirect(url_for('index'))

    @app.route('/logout')
    def logout():
        # Clear Flask session
        session.pop('user', None)
        session.clear()

        # post-logout redirect URL
        # note: this must exactly match cognito's logout_urls
        scheme = "http"
        if not ('localhost' in request.host_url or '127.0.0.1' in request.host_url):
            scheme = "https"
        logout_uri = url_for('index', _external=True, _scheme=scheme)

        # Construct the Cognito logout URL
        logout_url = f"https://{config.cognito_domain}/logout?client_id={config.client_id}&logout_uri={logout_uri}"

        # Redirect to Cognito logout
        return redirect(logout_url)


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin privileges for routes
    Must be used after @login_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if not is_admin():
                logging.warning(
                    f"Non-admin user attempted to access admin route: {request.path}")
                # todo: fix this
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in admin_required decorator: {str(e)}")
            abort(500)
    return decorated_function


def get_current_user():
    """Get the current logged in user information"""
    if 'user' in session:
        return session['user']
    return None


def get_current_user_id() -> Optional[str]:
    """
    Get the currently logged in user's ID from Cognito claims

    Returns:
        str: The user's Cognito sub (unique identifier) or None if not authenticated
    """
    try:
        user = get_current_user()
        if user and 'sub' in user:
            return user['sub']
        return None
    except Exception as e:
        logging.error(f"Error getting user ID: {str(e)}")
        return None


def is_admin():
    """Check if the current user has admin role"""
    user = get_current_user()
    if user and 'cognito:groups' in user:
        return 'admin' in user['cognito:groups']
    return False


def get_cognito_users() -> List[User]:
    """
    Retrieves all active users from Cognito User Pool
    Returns a list of user dictionaries containing email, name, and status
    as well as sorted by email

    Uses a 15-minute cache to reduce API calls to Cognito
    """
    global _users_cache
    current_time = time.time()

    # Check if cache is valid (not expired)
    if current_time - _users_cache[1] < _CACHE_TTL_SECONDS:
        return _users_cache[0]

    # Cache is expired, need to refresh
    # Use a lock to prevent multiple threads from refreshing simultaneously
    with _cache_lock:
        # Double-check that another thread hasn't already refreshed the cache
        if current_time - _users_cache[1] < _CACHE_TTL_SECONDS:
            return _users_cache[0]

        # Actually fetch the users from Cognito
        try:
            users = []
            pagination_token = None

            # Paginate through all users in the user pool
            while True:
                if pagination_token:
                    response = cognito.list_users(
                        UserPoolId=config.cognito_pool_id,
                        AttributesToGet=['sub', 'email'],
                        PaginationToken=pagination_token
                    )
                else:
                    response = cognito.list_users(
                        AttributesToGet=['sub', 'email'],
                        UserPoolId=config.cognito_pool_id
                    )

                # Process each user in the current page
                for user in response['Users']:
                    user_attrs = {attr['Name']: attr['Value']
                                  for attr in user['Attributes']}

                    # Create a simplified user object
                    user_data = User(
                        id=user_attrs.get('sub', ''),
                        username=user['Username'],
                        status=user['UserStatus'],
                        enabled=user['Enabled'],
                        created_at=user['UserCreateDate'].isoformat(),
                        last_modified=user['UserLastModifiedDate'].isoformat(),
                        email=user_attrs.get('email', ''),
                    )
                    users.append(user_data)

                # sort the list of users by username
                users.sort(key=lambda x: x.username)

                # Check if there are more users to fetch
                pagination_token = response.get('PaginationToken')
                if not pagination_token:
                    break

            # Update the cache with new data and timestamp
            _users_cache = (users, time.time())
            return users

        except ClientError as e:
            logging.error(f"Error retrieving Cognito users: {str(e)}")
            # If we have cached data, return it even if expired rather than failing
            if _users_cache[0]:
                logging.warning(
                    "Returning expired cache data due to Cognito API error")
                return _users_cache[0]
            raise
        except Exception as e:
            logging.error(
                f"Unexpected error retrieving Cognito users: {str(e)}")
            # If we have cached data, return it even if expired rather than failing
            if _users_cache[0]:
                logging.warning(
                    "Returning expired cache data due to unexpected error")
                return _users_cache[0]
            raise


def get_user_groups(cognito, username: str) -> List[str]:
    """
    Get the groups a user belongs to
    """
    try:
        response = cognito.admin_list_groups_for_user(
            Username=username,
            UserPoolId=config.cognito_pool_id
        )
        return [group['GroupName'] for group in response['Groups']]
    except ClientError as e:
        logging.error(f"Error retrieving groups for user {username}: {str(e)}")
        return []


def get_user_by_id(user_id: str) -> Optional[User]:
    """
    Get a user by their ID from Cognito

    Args:
        user_id: The user's Cognito sub (unique identifier)

    Returns:
        User object if found, None otherwise
    """
    users = get_cognito_users()
    for user in users:
        if user.id == user_id:
            return user
    return None


def decorate_interview_with_username(interview):
    """
    Decorates an interview object with the username from Cognito

    Args:
        interview: The interview object to decorate

    Returns:
        The decorated interview object
    """
    logging.info("Decorating interview with username")
    users = get_cognito_users()

    for user in users:
        if interview.user_id == user.id:
            interview.user_name = user.username
            break

    return interview


def decorate_interviews_with_usernames(interviews) -> List[Interview]:
    """
    Decorates a list of interview objects with usernames from Cognito

    Args:
        interviews: List of interview objects to decorate

    Returns:
        The decorated list of interview objects
    """
    logging.info("Decorating interviews with usernames")
    users = get_cognito_users()

    for user in users:
        print(f"evaling {user.id}, {user.username}")
        for interview in interviews:
            # Set interviewer username
            if interview.user_id == user.id:
                interview.user_name = user.username

            # Set approver username if approved_by_user_id exists
            if hasattr(interview, 'approved_by_user_id') and interview.approved_by_user_id == user.id:
                interview.approved_by_user_name = user.username

    return interviews
