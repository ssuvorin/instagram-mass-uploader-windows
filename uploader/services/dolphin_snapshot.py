"""
Service for managing Dolphin Profile Snapshots.
Saves full profile configuration for 1:1 recreation.
"""
import logging
from typing import Dict, Any, Optional
from django.utils import timezone

logger = logging.getLogger(__name__)


def save_dolphin_snapshot(account, profile_id: str, response: Dict[str, Any]) -> bool:
    """
    Save Dolphin profile snapshot to database for 1:1 recreation.
    
    Args:
        account: InstagramAccount or YouTubeAccount instance
        profile_id: Dolphin profile ID (string)
        response: Full response from Dolphin API create_profile call
        
    Returns:
        bool: True if snapshot was saved successfully, False otherwise
    """
    try:
        from uploader.models import DolphinProfileSnapshot
        
        # Extract payload and meta from response
        payload_json = response.get('_payload_used', {})
        meta_json = response.get('_meta', {})
        
        # Remove internal fields from response_json for cleaner storage
        response_json = {k: v for k, v in response.items() if not k.startswith('_')}
        
        # Determine account type and set appropriate field
        defaults = {
            'profile_id': str(profile_id),
            'payload_json': payload_json,
            'response_json': response_json,
            'meta_json': meta_json,
        }
        
        # Set the appropriate account field based on account type
        if hasattr(account, 'username'):  # InstagramAccount
            defaults['instagram_account'] = account
            account_name = account.username
        elif hasattr(account, 'email'):  # YouTubeAccount
            defaults['youtube_account'] = account
            account_name = account.email
        else:
            logger.error(f"[DOLPHIN SNAPSHOT] Unknown account type: {type(account)}")
            return False
        
        # Create or update snapshot
        snapshot, created = DolphinProfileSnapshot.objects.update_or_create(
            **{k: v for k, v in defaults.items() if k in ['instagram_account', 'youtube_account']},
            defaults=defaults
        )
        
        action = "Created" if created else "Updated"
        logger.info(f"[DOLPHIN SNAPSHOT] {action} snapshot for {account_name} (profile_id: {profile_id})")
        return True
        
    except Exception as e:
        account_name = getattr(account, 'username', getattr(account, 'email', 'unknown'))
        logger.error(f"[DOLPHIN SNAPSHOT] Failed to save snapshot for {account_name}: {str(e)}")
        return False


def get_profile_data_from_api(dolphin_api, profile_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch full profile data from Dolphin API.
    
    Args:
        dolphin_api: DolphinAnty API instance
        profile_id: Dolphin profile ID
        
    Returns:
        Dict with profile data or None if failed
    """
    try:
        response = dolphin_api.get_profile(profile_id)
        if response and isinstance(response, dict):
            logger.info(f"[DOLPHIN SNAPSHOT] Successfully fetched profile data for {profile_id}")
            return response
        else:
            logger.warning(f"[DOLPHIN SNAPSHOT] Empty or invalid response for profile {profile_id}")
            return None
    except Exception as e:
        logger.error(f"[DOLPHIN SNAPSHOT] Failed to fetch profile {profile_id}: {str(e)}")
        return None


def save_existing_profile_snapshot(account, dolphin_api) -> bool:
    """
    Fetch existing profile data from Dolphin API and save snapshot.
    
    Args:
        account: InstagramAccount or YouTubeAccount instance with dolphin_profile_id set
        dolphin_api: DolphinAnty API instance
        
    Returns:
        bool: True if snapshot was saved successfully, False otherwise
    """
    account_name = getattr(account, 'username', getattr(account, 'email', 'unknown'))
    
    if not account.dolphin_profile_id:
        logger.warning(f"[DOLPHIN SNAPSHOT] Account {account_name} has no dolphin_profile_id")
        return False
    
    try:
        from uploader.models import DolphinProfileSnapshot
        
        # Fetch profile data from Dolphin API
        profile_data = get_profile_data_from_api(dolphin_api, account.dolphin_profile_id)
        
        if not profile_data:
            return False
        
        # Extract profile_id from response
        profile_id = account.dolphin_profile_id
        
        # Determine account type and set appropriate field
        defaults = {
            'profile_id': str(profile_id),
            'payload_json': {},  # Empty as we don't have original payload
            'response_json': profile_data,
            'meta_json': {
                'fetched_at': timezone.now().isoformat(),
                'note': 'Snapshot created from existing profile (no original payload)'
            },
        }
        
        # Set the appropriate account field based on account type
        if hasattr(account, 'username'):  # InstagramAccount
            defaults['instagram_account'] = account
        elif hasattr(account, 'email'):  # YouTubeAccount
            defaults['youtube_account'] = account
        else:
            logger.error(f"[DOLPHIN SNAPSHOT] Unknown account type: {type(account)}")
            return False
        
        # Create snapshot from fetched data
        # Note: We don't have original _payload_used, so we reconstruct essential data
        snapshot, created = DolphinProfileSnapshot.objects.update_or_create(
            **{k: v for k, v in defaults.items() if k in ['instagram_account', 'youtube_account']},
            defaults=defaults
        )
        
        action = "Created" if created else "Updated"
        logger.info(f"[DOLPHIN SNAPSHOT] {action} snapshot from existing profile for {account_name}")
        return True
        
    except Exception as e:
        logger.error(f"[DOLPHIN SNAPSHOT] Failed to save existing profile snapshot for {account_name}: {str(e)}")
        return False

