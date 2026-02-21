"""
LinkedIn API client pour OAuth et publication de posts
"""
import os
import requests
from typing import Dict, Any, Optional
from urllib.parse import urlencode


class LinkedInClient:
    """Client pour publier sur LinkedIn via OAuth 2.0"""

    def __init__(self):
        """
        Initialize LinkedIn client with credentials from environment

        Required env vars:
            LINKEDIN_CLIENT_ID: OAuth client ID
            LINKEDIN_CLIENT_SECRET: OAuth client secret
            LINKEDIN_REDIRECT_URI: OAuth redirect URI
            LINKEDIN_ACCESS_TOKEN: Access token (obtained via OAuth flow)
        """
        self.client_id = os.getenv('LINKEDIN_CLIENT_ID')
        self.client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
        self.redirect_uri = os.getenv('LINKEDIN_REDIRECT_URI')
        self.access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')

        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError(
                "LinkedIn OAuth not configured. Required env vars: "
                "LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_REDIRECT_URI"
            )

    def is_configured(self) -> bool:
        """Check if LinkedIn API is fully configured with access token"""
        return bool(self.access_token)

    def get_auth_url(self, state: str = "random_state") -> str:
        """
        Generate LinkedIn OAuth authorization URL

        Args:
            state: Random state for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'w_member_social r_liteprofile',
            'state': state
        }

        auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"
        return auth_url

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Dict with access_token, expires_in, etc.

        Raises:
            requests.HTTPError: If token exchange fails
        """
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"

        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        response = requests.post(token_url, data=data)
        response.raise_for_status()

        token_data = response.json()
        self.access_token = token_data['access_token']

        return token_data

    def get_person_id(self) -> str:
        """
        Get the authenticated user person ID (URN)

        Returns:
            Person ID (e.g., "urn:li:person:XXXXXXX")

        Raises:
            requests.HTTPError: If API call fails
        """
        if not self.access_token:
            raise ValueError("No access token. Complete OAuth flow first.")

        url = "https://api.linkedin.com/v2/me"
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()
        person_id = data.get('id')

        return f"urn:li:person:{person_id}"

    def publish_post(
        self,
        text: str,
        visibility: str = "PUBLIC"
    ) -> Dict[str, Any]:
        """
        Publish a post to LinkedIn

        Args:
            text: Post content (max 3000 characters)
            visibility: "PUBLIC" or "CONNECTIONS"

        Returns:
            Dict with post ID and status

        Raises:
            ValueError: If not configured or text too long
            requests.HTTPError: If API call fails
        """
        if not self.access_token:
            raise ValueError(
                "No access token configured. "
                "Set LINKEDIN_ACCESS_TOKEN in .env or complete OAuth flow."
            )

        # Validate text length
        if len(text) > 3000:
            raise ValueError(
                f"Post text too long ({len(text)} chars). "
                "LinkedIn limit is 3000 characters."
            )

        # Get person ID
        try:
            author_urn = self.get_person_id()
        except Exception as e:
            raise ValueError(f"Failed to get person ID: {str(e)}")

        # Build request
        url = "https://api.linkedin.com/v2/ugcPosts"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }

        body = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            }
        }

        # Send request
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()

        result = response.json()
        post_id = result.get('id', '')

        return {
            'id': post_id,
            'status': 'published',
            'url': f"https://www.linkedin.com/feed/update/{post_id}" if post_id else None
        }


def is_linkedin_configured() -> bool:
    """
    Check if LinkedIn API is configured in environment

    Returns:
        True if all required credentials are present
    """
    required_vars = [
        'LINKEDIN_CLIENT_ID',
        'LINKEDIN_CLIENT_SECRET',
        'LINKEDIN_REDIRECT_URI'
    ]

    return all(os.getenv(var) for var in required_vars)


def has_linkedin_access_token() -> bool:
    """
    Check if LinkedIn access token is available

    Returns:
        True if LINKEDIN_ACCESS_TOKEN is set
    """
    return bool(os.getenv('LINKEDIN_ACCESS_TOKEN'))
