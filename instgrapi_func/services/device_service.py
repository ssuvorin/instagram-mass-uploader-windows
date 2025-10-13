from __future__ import annotations
from typing import Dict, Optional, Tuple
import random
import uuid


# Pool of Instagram app versions for randomization
# Each tuple contains (app_version, version_code)
INSTAGRAM_VERSION_POOL = [
	("400.0.0.49.68", "400049068"),    # Latest
	("395.0.0.56.165", "395056165"),  # Recent stable
	("394.0.0.46.81", "394046081"),   # Recent stable
	("390.0.0.43.81", "390043081"),   # Recent stable
	("385.0.0.47.74", "385047074"),   # Recent stable
	("383.1.0.48.78", "383148078"),   # Recent stable
	("382.0.0.49.84", "382049084"),   # Recent stable
	("381.2.0.53.84", "381253084"),   # Recent stable
	("380.0.0.49.84", "380049084"),   # Recent stable
	("379.1.0.43.80", "379143080"),   # Recent stable
	("379.0.0.41.80", "379041080"),   # Recent stable
	("377.1.0.48.63", "377148063"),   # Recent stable
	("377.0.0.40.63", "377040063"),   # Recent stable
	("376.1.0.55.68", "376155068"),   # Recent stable
	("375.0.0.38.66", "375038066"),   # Recent stable
	("374.0.0.43.67", "374043067"),   # Recent stable
	("373.0.0.46.67", "373046067"),   # Recent stable
	("372.0.0.48.60", "372048060"),   # Recent stable
	("371.0.0.36.89", "371036089"),   # Recent stable
	("370.0.0.42.96", "370042096"),   # Recent stable
	("369.0.0.46.101", "369046101"),  # Recent stable
	("368.0.0.40.96", "368040096"),   # Recent stable
	("367.0.0.43.89", "367043089"),   # Recent stable
	("366.0.0.34.86", "366034086"),   # Recent stable
	("365.0.0.40.94", "365040094"),   # Recent stable
	("364.0.0.35.86", "364035086"),   # Recent stable
	("363.0.0.29.80", "363029080"),   # Recent stable
	("362.0.0.33.241", "362033241"),  # Recent stable
	("361.0.0.46.88", "361046088"),   # Recent stable
	("360.0.0.52.192", "360052192"), # Recent stable
	("359.2.0.64.89", "359264089"),  # Recent stable
	("359.0.0.59.89", "359059089"),  # Recent stable
	("358.0.0.51.97", "358051097"),  # Recent stable
	("357.1.0.52.100", "357152100"), # Recent stable
	("356.0.0.41.101", "356041101"), # Recent stable
	("355.0.0.42.103", "355042103"), # Recent stable
	("354.2.0.47.100", "354247100"), # Recent stable
	("353.1.0.47.90", "353147090"),  # Recent stable
	("352.0.0.38.100", "352038100"), # Recent stable
	("351.0.0.41.106", "351041106"), # Recent stable
	("350.1.0.46.93", "350146093"), # Recent stable
	("349.3.0.42.104", "349342104"), # Recent stable
	("348.0.0.46.105", "348046105"), # Recent stable
	("347.3.0.41.103", "347341103"), # Recent stable
	("346.0.0.45.104", "346045104"), # Recent stable
	("345.0.0.48.95", "345048095"),  # Recent stable
	("344.1.0.42.92", "344142092"), # Recent stable
	("342.0.0.33.103", "342033103"), # Recent stable
	("341.0.0.45.100", "341045100"), # Recent stable
	("340.0.0.22.109", "340022109"), # Recent stable
	("339.0.0.30.105", "339030105"), # Recent stable
	("337.0.0.35.102", "337035102"), # Recent stable
	("336.0.0.35.90", "336035090"),  # Recent stable
	("335.0.0.39.93", "335039093"),  # Recent stable
	("334.0.0.42.95", "334042095"),  # Recent stable
	("333.0.0.42.91", "333042091"),  # Recent stable
	("332.0.0.38.90", "332038090"),  # Recent stable
	("331.0.0.37.90", "331037090"),  # Recent stable
	("330.0.0.40.92", "330040092"),  # Recent stable
	("329.0.0.41.93", "329041093"),  # Recent stable
	("328.0.0.42.90", "328042090"),  # Recent stable
	("327.2.0.50.93", "327250093"),  # Recent stable
	("326.0.0.42.90", "326042090"),  # Recent stable
	("325.0.0.35.91", "325035091"),  # Recent stable
	("324.0.0.27.50", "324027050"),  # Recent stable
	("323.0.0.35.65", "323035065"),  # Recent stable
	("269.0.0.18.75", "314665256"),  # Legacy fallback
]

# Default versions (fallback)
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


_DEVICE_POOL = [
	{
		"manufacturer": "samsung",
		"brand": "samsung",
		"model": "SM-G973F",            # Galaxy S10
		"device": "beyond1",
		"cpu": "exynos9820",
		"dpi": "640dpi",
		"resolution": "1440x3040",
		"android_release": "10",
		"android_version": 29,
	},
	{
		"manufacturer": "OnePlus",
		"brand": "OnePlus",
		"model": "ONEPLUS A6013",       # OnePlus 6T
		"device": "OnePlus6T",
		"cpu": "qcom",
		"dpi": "420dpi",
		"resolution": "1080x2340",
		"android_release": "10",
		"android_version": 29,
	},
	{
		"manufacturer": "Google",
		"brand": "google",
		"model": "Pixel 5",
		"device": "redfin",
		"cpu": "qcom",
		"dpi": "440dpi",
		"resolution": "1080x2340",
		"android_release": "11",
		"android_version": 30,
	},
	{
		"manufacturer": "Xiaomi",
		"brand": "Xiaomi",
		"model": "Redmi Note 8 Pro",
		"device": "begonia",
		"cpu": "mtk",
		"dpi": "440dpi",
		"resolution": "1080x2340",
		"android_release": "10",
		"android_version": 29,
	},
	{
		"manufacturer": "Huawei",
		"brand": "HUAWEI",
		"model": "P30",
		"device": "ELE-L29",
		"cpu": "kirin980",
		"dpi": "480dpi",
		"resolution": "1080x2340",
		"android_release": "10",
		"android_version": 29,
	},
	{
		"manufacturer": "samsung",
		"brand": "samsung",
		"model": "SM-A515F",           # Galaxy A51
		"device": "a51",
		"cpu": "exynos9611",
		"dpi": "420dpi",
		"resolution": "1080x2400",
		"android_release": "11",
		"android_version": 30,
	},
	{
		"manufacturer": "samsung",
		"brand": "samsung",
		"model": "SM-A715F",           # Galaxy A71
		"device": "a71",
		"cpu": "qcom",
		"dpi": "420dpi",
		"resolution": "1080x2400",
		"android_release": "11",
		"android_version": 30,
	},
	{
		"manufacturer": "Xiaomi",
		"brand": "Redmi",
		"model": "M2004J19C",          # Redmi 9
		"device": "lancelot",
		"cpu": "mtk",
		"dpi": "440dpi",
		"resolution": "1080x2340",
		"android_release": "10",
		"android_version": 29,
	},
	{
		"manufacturer": "Xiaomi",
		"brand": "POCO",
		"model": "M2010J19CG",         # POCO M3
		"device": "citrus",
		"cpu": "qcom",
		"dpi": "440dpi",
		"resolution": "1080x2340",
		"android_release": "10",
		"android_version": 29,
	},
	{
		"manufacturer": "HUAWEI",
		"brand": "HUAWEI",
		"model": "P20 Pro",
		"device": "CLT-L29",
		"cpu": "kirin970",
		"dpi": "480dpi",
		"resolution": "1080x2240",
		"android_release": "10",
		"android_version": 29,
	},
	{
		"manufacturer": "OPPO",
		"brand": "OPPO",
		"model": "CPH2211",            # OPPO A74
		"device": "ocean",
		"cpu": "qcom",
		"dpi": "480dpi",
		"resolution": "1080x2400",
		"android_release": "11",
		"android_version": 30,
	},
	{
		"manufacturer": "Vivo",
		"brand": "vivo",
		"model": "V2027",
		"device": "PD2020F",
		"cpu": "qcom",
		"dpi": "480dpi",
		"resolution": "1080x2400",
		"android_release": "11",
		"android_version": 30,
	},
	{
		"manufacturer": "Realme",
		"brand": "realme",
		"model": "RMX2020",            # realme C3
		"device": "RMX2020",
		"cpu": "mtk",
		"dpi": "440dpi",
		"resolution": "720x1600",
		"android_release": "10",
		"android_version": 29,
	},
	{
		"manufacturer": "Motorola",
		"brand": "motorola",
		"model": "moto g(8) power",
		"device": "sofia",
		"cpu": "qcom",
		"dpi": "400dpi",
		"resolution": "1080x2300",
		"android_release": "10",
		"android_version": 29,
	},
]


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
	
	# CRITICAL: Check if user agent is iPhone and convert to Android
	if _is_iphone_user_agent(ua):
		dev, ua = _convert_iphone_to_android_device_settings(dev, ua, username)
	
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
				
				# CRITICAL: Check if user agent is iPhone and convert to Android
				if _is_iphone_user_agent(user_agent):
					device_settings, user_agent = _convert_iphone_to_android_device_settings(device_settings, user_agent, username)
					# Update database with converted Android settings
					try:
						dev_obj.device_settings = device_settings
						dev_obj.user_agent = user_agent
						dev_obj.save(update_fields=['device_settings', 'user_agent'])
					except Exception:
						pass  # Continue even if DB update fails
				
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

	# Fallback to random
	if not device_settings:
		device_settings = generate_random_device_settings(username)

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