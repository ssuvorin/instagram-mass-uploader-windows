from __future__ import annotations
from typing import Dict, Optional, Tuple
import random
import uuid


APP_VERSION = "269.0.0.18.75"
VERSION_CODE = "314665256"


def _generate_uuid() -> str:
	return str(uuid.uuid4())


def _generate_android_device_id() -> str:
	# Typical format: android-<16 hex chars>
	return "android-" + uuid.uuid4().hex[:16]


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


def generate_random_device_settings() -> Dict:
	"""Return a realistic random device_settings dict with stable identifiers."""
	base = random.choice(_DEVICE_POOL).copy()
	settings: Dict = {
		"cpu": base["cpu"],
		"dpi": base["dpi"],
		"model": base["model"],
		"device": base["device"],
		"resolution": base["resolution"],
		"app_version": APP_VERSION,
		"manufacturer": base["manufacturer"],
		"version_code": VERSION_CODE,
		"android_release": base["android_release"],
		"android_version": base["android_version"],
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


def _derive_from_session_settings(persisted_settings: Dict) -> Tuple[Optional[Dict], Optional[str]]:
	"""Try to build device_settings and user_agent from stored session settings."""
	if not persisted_settings:
		return None, None
	dev = persisted_settings.get("device_settings") or None
	ua = persisted_settings.get("user_agent") or None
	uuids = persisted_settings.get("uuids") or {}
	if dev:
		dev = dev.copy()
		dev.setdefault("app_version", APP_VERSION)
		dev.setdefault("version_code", VERSION_CODE)
		dev = _merge_uuids(dev, uuids)
		return dev, ua
	# No explicit device_settings in session → build from random base but keep uuids
	dev = generate_random_device_settings()
	dev = _merge_uuids(dev, uuids)
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
		adopted, ua = _derive_from_session_settings(persisted_settings or {})
		device_settings = adopted
		user_agent = ua or user_agent

	# Fallback to random
	if not device_settings:
		device_settings = generate_random_device_settings()

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