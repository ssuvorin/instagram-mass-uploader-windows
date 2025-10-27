from __future__ import annotations
from typing import Dict, Optional, Tuple
import random
import uuid

# Import device pool from separate file
from .device_pool import INSTAGRAM_VERSION_POOL, _DEVICE_POOL


# Default versions (fallback) - imported from device_pool.py
DEFAULT_APP_VERSION = "269.0.0.18.75"
DEFAULT_VERSION_CODE = "314665256"


def _generate_uuid() -> str:
	return str(uuid.uuid4())


def _generate_android_device_id() -> str:
	# Typical format: android-<16 hex chars>
	return "android-" + uuid.uuid4().hex[:16]


def get_random_instagram_version() -> Tuple[str, str]:
	"""Get a random Instagram app version and version code."""
	return random.choice(INSTAGRAM_VERSION_POOL)


def get_version_for_account(username: str) -> Tuple[str, str]:
	"""
	Get Instagram version for specific account.
	Uses deterministic randomization based on username hash for consistency.
	"""
	if not username:
		return get_random_instagram_version()
	
	# Use username hash for deterministic but random-looking selection
	hash_value = hash(username) % len(INSTAGRAM_VERSION_POOL)
	return INSTAGRAM_VERSION_POOL[hash_value]




def generate_random_device_settings(username: Optional[str] = None) -> Dict:
	"""Return a realistic random device_settings dict with stable identifiers."""
	base = random.choice(_DEVICE_POOL).copy()
	
	# Get version for this account (deterministic based on username)
	app_version, version_code = get_version_for_account(username) if username else get_random_instagram_version()
	
	# Default locale and country (can be overridden later)
	default_locale = "ru_BY"
	default_country = "BY"
	
	settings: Dict = {
		"cpu": base["cpu"],
		"dpi": base["dpi"],
		"model": base["model"],
		"device": base["device"],
		"resolution": base["resolution"],
		"app_version": app_version,
		"manufacturer": base["manufacturer"],
		"version_code": version_code,
		"android_release": base["android_release"],
		"android_version": base["android_version"],
		# Geo settings
		"locale": default_locale,
		"country": default_country,
		# unique ids
		"uuid": _generate_uuid(),
		"android_device_id": _generate_android_device_id(),
		"phone_id": _generate_uuid(),
		"client_session_id": _generate_uuid(),
	}
	return settings


def _merge_uuids(target: Dict, uuids: Dict) -> Dict:
	if not uuids:
		return target
	for key in ("uuid", "android_device_id", "phone_id", "client_session_id"):
		val = uuids.get(key)
		if val and not target.get(key):
			target[key] = val
	return target


def generate_user_agent_from_device_settings(device_settings: Dict, username: Optional[str] = None) -> str:
	"""
	Generate Instagram User Agent string from device settings.

	This creates a realistic UA that matches the device fingerprint.
	"""
	if not device_settings:
		# Fallback to random device UA
		random_device = generate_random_device_settings(username)
		return generate_user_agent_from_device_settings(random_device, username)

	# Get version info
	app_version, version_code = get_version_for_account(username) if username else get_random_instagram_version()

	# Build UA components - use device_settings values with fallbacks
	android_version = device_settings.get("android_version", 29)
	android_release = device_settings.get("android_release", "10")
	dpi = device_settings.get("dpi", "640dpi")
	resolution = device_settings.get("resolution", "1440x3040")
	manufacturer = device_settings.get("manufacturer", "samsung")
	model = device_settings.get("model", "SM-G973F")
	device = device_settings.get("device", "beyond1")
	cpu = device_settings.get("cpu", "exynos9820")
	locale = device_settings.get("locale", "ru_BY")

	# Format: Instagram {app_version} Android ({android_version}/{android_release}; {dpi}; {resolution}; {manufacturer}; {model}; {device}; {cpu}; {locale}; {version_code})
	ua = f"Instagram {app_version} Android ({android_version}/{android_release}; {dpi}; {resolution}; {manufacturer}; {model}; {device}; {cpu}; {locale}; {version_code})"

	return ua


def _is_iphone_user_agent(user_agent: str) -> bool:
	"""Check if user agent is from iPhone/iOS device."""
	if not user_agent:
		return False
	iphone_indicators = ["iPhone", "iOS", "AppleWebKit"]
	return any(indicator in user_agent for indicator in iphone_indicators)


def _convert_iphone_to_android_device_settings(device_settings: Dict, user_agent: str, username: Optional[str] = None) -> Tuple[Dict, str]:
	"""
	Convert iPhone device settings to Android equivalent.
	
	Args:
		device_settings: Original device settings (may be iPhone)
		user_agent: Original user agent (may be iPhone)
		username: Username for deterministic version selection
		
	Returns:
		Tuple of (android_device_settings, android_user_agent)
"""
	# Generate new Android device settings with account-specific version
	android_device = generate_random_device_settings(username)
	
	# Preserve critical UUIDs from original device if available
	preserved_uuids = {}
	for key in ("uuid", "android_device_id", "phone_id", "client_session_id"):
		if device_settings.get(key):
			preserved_uuids[key] = device_settings[key]
	
	# Preserve locale and country from original device if available
	if device_settings.get("locale"):
		android_device["locale"] = device_settings["locale"]
	if device_settings.get("country"):
		android_device["country"] = device_settings["country"]
	
	# Merge preserved UUIDs into Android device
	android_device = _merge_uuids(android_device, preserved_uuids)
	
	# Generate Android user agent using device settings
	from instagrapi import config
	android_user_agent = config.USER_AGENT_BASE.format(**android_device)
	
	return android_device, android_user_agent


def _derive_from_session_settings(persisted_settings: Dict, username: Optional[str] = None) -> Tuple[Optional[Dict], Optional[str]]:
	"""Try to build device_settings and user_agent from stored session settings."""
	if not persisted_settings:
		return None, None
	dev = persisted_settings.get("device_settings") or None
	ua = persisted_settings.get("user_agent") or None
	uuids = persisted_settings.get("uuids") or {}
	
	if dev:
		dev = dev.copy()
		# Use account-specific version if not already set
		if not dev.get("app_version") or not dev.get("version_code"):
			app_version, version_code = get_version_for_account(username) if username else get_random_instagram_version()
			dev.setdefault("app_version", app_version)
			dev.setdefault("version_code", version_code)
		dev = _merge_uuids(dev, uuids)
		
		# CRITICAL: Check if user agent is iPhone and convert to Android
		if _is_iphone_user_agent(ua):
			dev, ua = _convert_iphone_to_android_device_settings(dev, ua, username)
		
		return dev, ua
	
	# No explicit device_settings in session → build from random base but keep uuids
	dev = generate_random_device_settings(username)
	dev = _merge_uuids(dev, uuids)
	
	# NOTE: iPhone devices are now supported by instagrapi, no conversion needed
	# if _is_iphone_user_agent(ua):
	#     dev, ua = _convert_iphone_to_android_device_settings(dev, ua, username)
	
	return dev, ua


def ensure_persistent_device(username: str, persisted_settings: Optional[Dict] = None) -> Tuple[Dict, Optional[str]]:
	"""Ensure an account has a persistent device.

	Return (device_settings, user_agent).
	Order of preference:
	1) Existing InstagramDevice.device_settings with UUIDs merged from session if available
	2) Adopt from persisted session settings (device_settings/uuids/user_agent)
	3) Generate a random new device and persist
	"""
	device_settings: Optional[Dict] = None
	user_agent: Optional[str] = None

	try:
		from uploader.models import InstagramAccount, InstagramDevice  # type: ignore
		acc = InstagramAccount.objects.filter(username=username).first()
		if acc:
			dev_obj = getattr(acc, 'device', None)
			if dev_obj and dev_obj.device_settings:
				device_settings = dict(dev_obj.device_settings)
				user_agent = (dev_obj.user_agent or None)
				print(f"[DEBUG] ensure_persistent_device: Found device_settings for {username}: {list(device_settings.keys())}")
				print(f"[DEBUG] ensure_persistent_device: User agent: {user_agent}")

				# NOTE: iPhone devices are now supported by instagrapi, no conversion needed
				# if _is_iphone_user_agent(user_agent):
				#     device_settings, user_agent = _convert_iphone_to_android_device_settings(device_settings, user_agent, username)

				# CRITICAL: Merge UUIDs from session settings if available (bundle data takes priority)
				if persisted_settings and persisted_settings.get('uuids'):
					session_uuids = persisted_settings['uuids']
					uuids_updated = False
					for key in ("uuid", "android_device_id", "phone_id", "client_session_id"):
						session_value = session_uuids.get(key)
						if session_value and device_settings.get(key) != session_value:
							device_settings[key] = session_value
							uuids_updated = True

					# Update database if UUIDs were merged from session
					if uuids_updated:
						try:
							dev_obj.device_settings = device_settings
							dev_obj.save(update_fields=['device_settings'])
						except Exception:
							pass  # Continue even if DB update fails

				return device_settings, user_agent
	except Exception:
		# DB not available or other error; continue with session/random
		pass

	# Try to adopt from session
	if not device_settings:
		adopted, ua = _derive_from_session_settings(persisted_settings or {}, username)
		device_settings = adopted
		user_agent = ua or user_agent

	# Generate UA from device_settings if we have them but no UA
	if device_settings and not user_agent:
		user_agent = generate_user_agent_from_device_settings(device_settings, username)
		print(f"[DEBUG] Generated UA from device_settings for {username}: {user_agent[:100]}...")

	# Fallback to random
	if not device_settings:
		device_settings = generate_random_device_settings(username)
		if not user_agent:
			user_agent = generate_user_agent_from_device_settings(device_settings, username)

	# Persist into DB if possible
	try:
		from uploader.models import InstagramAccount, InstagramDevice  # type: ignore
		acc = InstagramAccount.objects.filter(username=username).first()
		if acc:
			dev_obj = getattr(acc, 'device', None)
			if not dev_obj:
				InstagramDevice.objects.create(
					account=acc,
					device_settings=device_settings,
					user_agent=(user_agent or ""),
				)
			else:
				updates = []
				if not dev_obj.device_settings:
					dev_obj.device_settings = device_settings
					updates.append('device_settings')
				else:
					# Fill missing ids if any
					missing = False
					for key in ("uuid", "android_device_id", "phone_id", "client_session_id"):
						if not dev_obj.device_settings.get(key) and device_settings.get(key):
							dev_obj.device_settings[key] = device_settings[key]
							missing = True
					if missing:
						updates.append('device_settings')
				if user_agent and not dev_obj.user_agent:
					dev_obj.user_agent = user_agent
					updates.append('user_agent')
				if updates:
					dev_obj.save(update_fields=updates)
	except Exception:
		pass

	return device_settings, user_agent 