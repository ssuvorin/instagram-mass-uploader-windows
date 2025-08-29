from typing import TYPE_CHECKING
import os
import random
import time
import asyncio
from typing import Dict, List, Tuple, Optional, Callable

from uploader.logging_utils import log_info, log_error, log_success, attach_instagrapi_web_bridge

# instagrapi imports (runtime)
try:
	from instagrapi import Client  # type: ignore
	from instagrapi.types import Usertag, Location  # type: ignore
except Exception:
	Client = None  # type: ignore
	Usertag = None  # type: ignore
	Location = None  # type: ignore

# typing-time aliases to satisfy Pylance
if TYPE_CHECKING:
	from instagrapi import Client as IGClient  # type: ignore
	from instagrapi.types import Usertag as IGUsertag, Location as IGLocation  # type: ignore
else:
	IGClient = object  # type: ignore
	IGUsertag = object  # type: ignore
	IGLocation = object  # type: ignore

# our services
from instgrapi_func.services.client_factory import IGClientFactory
from instgrapi_func.services.proxy import build_proxy_url
from instgrapi_func.services.auth_service import IGAuthService
from instgrapi_func.services.code_providers import (
	CompositeProvider,
	TOTPProvider,
	AutoIMAPEmailProvider,
)
from instgrapi_func.services.session_store import DjangoDeviceSessionStore
from instgrapi_func.services.geo import resolve_location_coordinates
from instgrapi_func.services.device_service import ensure_persistent_device


def _extract_mentions(mentions_text: Optional[str]) -> List[str]:
	if not mentions_text:
		return []
	# split by whitespace/newlines, normalize @username → username
	raw = [p.strip() for p in mentions_text.replace("\r", "\n").split("\n")]
	parts: List[str] = []
	for line in raw:
		if not line:
			continue
		for token in line.split():
			t = token.strip()
			if not t:
				continue
			if t.startswith('@'):
				t = t[1:]
			# filter obviously invalid
			if 1 <= len(t) <= 30:
				parts.append(t)
	# dedupe preserving order
	seen = set()
	result: List[str] = []
	for p in parts:
		if p.lower() not in seen:
			seen.add(p.lower())
			result.append(p)
	return result


def _build_usertags(cl: 'IGClient', usernames: List[str]) -> List['IGUsertag']:
	user_tags: List['IGUsertag'] = []
	if not usernames:
		return user_tags
	for uname in usernames:
		try:
			user = cl.user_info_by_username(uname)  # type: ignore[attr-defined]
			# Some instagrapi versions require UserShort; attempt to adapt
			try:
				from instagrapi.types import UserShort  # type: ignore
				if hasattr(user, 'pk'):
					user = UserShort(pk=getattr(user, 'pk'), username=getattr(user, 'username'))  # type: ignore
			except Exception:
				pass
			# random but centered tag position
			x = round(random.uniform(0.35, 0.65), 2)
			y = round(random.uniform(0.35, 0.65), 2)
			user_tags.append(Usertag(user=user, x=x, y=y))  # runtime type
			log_info(f"[USERS] usertag prepared for @{uname} at ({x},{y})")
		except Exception as e:
			log_error(f"[USERS] failed to resolve @{uname}: {e}")
	return user_tags


def _resolve_location(cl: 'IGClient', location_text: Optional[str]) -> Optional['IGLocation']:
	"""Best-effort location resolver by text. If not found, return None.
	Avoids external geocoding; tries instagrapi search endpoints when available.
	"""
	if not location_text:
		return None
	query = (location_text or '').strip()
	if not query:
		return None
	# Accept "lat,lng | Name" direct format
	try:
		parts = [p.strip() for p in query.split('|', 1)]
		coords = parts[0]
		if ',' in coords:
			lat_s, lng_s = [c.strip() for c in coords.split(',', 1)]
			lat_v = float(lat_s)
			lng_v = float(lng_s)
			name_v = parts[1] if len(parts) > 1 else query
			return Location(name=str(name_v), lat=lat_v, lng=lng_v)  # type: ignore
	except Exception:
		pass
	# Try a couple of known methods guarded by try/except, degrade to None
	try:
		# Some instagrapi builds expose .locations_search or .location_search
		search_methods = [
			getattr(cl, 'locations_search', None),
			getattr(cl, 'location_search', None),
			getattr(cl, 'search_location', None),
		]
		for m in search_methods:
			if not callable(m):
				continue
			try:
				res = m(query)  # type: ignore[misc]
				if not res:
					continue
				# res can be list of locations or dicts; pick first sensible
				cand = None
				if isinstance(res, list) and res:
					cand = res[0]
				if cand is not None:
					lat = getattr(cand, 'lat', None) or getattr(cand, 'latitude', None)
					lng = getattr(cand, 'lng', None) or getattr(cand, 'longitude', None)
					name = getattr(cand, 'name', None) or query
					if lat is not None and lng is not None:
						log_info(f"[LOCATION] resolved '{query}' → ({lat},{lng}) :: {name}")
						return Location(name=str(name), lat=float(lat), lng=float(lng))  # runtime type
			except Exception:
				pass
		# Fallback: try our geocoder (Nominatim + dictionary)
		try:
			coords = resolve_location_coordinates(query)
			if coords:
				name2, lat2, lon2 = coords
				log_info(f"[LOCATION] geocoded '{query}' → ({lat2},{lon2}) :: {name2}")
				return Location(name=str(name2), lat=float(lat2), lng=float(lon2))  # type: ignore
		except Exception:
			pass
		# Else give up gracefully
		log_error(f"[LOCATION] could not resolve '{query}' to coordinates; skipping API location")
	except Exception:
		return None
	return None


def _sync_upload_impl(account_details: Dict, videos: List, video_files_to_upload: List[str], task_id: int, account_task_id: int, on_log: Optional[Callable[[str], None]] = None) -> Tuple[str, int, int]:
	if Client is None:
		log_error("[API] instagrapi not available")
		return ("failed", 0, 1)

	# Attach bridge so instagrapi/public/private logs appear in UI
	attach_instagrapi_web_bridge()

	username = account_details.get('username')
	password = account_details.get('password')
	tfa_secret = (account_details.get('tfa_secret') or '')
	# Accept both 'email_login' and legacy 'email' key
	email_login = (account_details.get('email_login') or account_details.get('email') or '')
	email_password = (account_details.get('email_password') or '')
	proxy_dict = account_details.get('proxy') or {}
	proxy_url = build_proxy_url(proxy_dict)

	log_info(f"[API] Starting instagrapi upload for {username}")
	if on_log:
		on_log(f"Starting instagrapi upload for {username}")

	# Load persisted device + session if available
	session_store = DjangoDeviceSessionStore()
	persisted_settings = session_store.load(username) or None

	# Ensure per-account persistent device (from DB/session or generate once)
	device_settings, ua_hint = ensure_persistent_device(username, persisted_settings)

	# Build client
	try:
		cl: 'IGClient' = IGClientFactory.create_client(
			device_config={
				"cpu": device_settings.get("cpu", "exynos9820"),
				"dpi": device_settings.get("dpi", "640dpi"),
				"model": device_settings.get("model", "SM-G973F"),
				"device": device_settings.get("device", "beyond1"),
				"resolution": device_settings.get("resolution", "1440x3040"),
				"app_version": device_settings.get("app_version", "269.0.0.18.75"),
				"manufacturer": device_settings.get("manufacturer", "samsung"),
				"version_code": device_settings.get("version_code", "314665256"),
				"android_release": device_settings.get("android_release", "10"),
				"android_version": device_settings.get("android_version", 29),
				# optional ids: if provided once, we keep them stable via InstagramDevice
				"uuid": device_settings.get("uuid"),
				"android_device_id": device_settings.get("android_device_id"),
				"phone_id": device_settings.get("phone_id"),
				"client_session_id": device_settings.get("client_session_id"),
			},
			proxy_url=proxy_url,
			session_settings=persisted_settings,
			user_agent=(device_settings.get("user_agent") or ua_hint),
			country=device_settings.get("country"),
			locale=device_settings.get("locale"),
			proxy_dict=proxy_dict,
		)
		try:
			cl.delay_range = [1, 3]  # type: ignore[attr-defined]
		except Exception:
			pass
	except Exception as e:
		log_error(f"[API] failed to create client: {e}")
		if on_log:
			on_log(f"Failed to create client: {e}")
		return ("failed", 0, 1)

	# Auth: prefer existing session; fallback to login with TOTP/email
	provider = CompositeProvider([
		TOTPProvider(tfa_secret or None),
		AutoIMAPEmailProvider(email_login, email_password, on_log=on_log),
	])
	auth = IGAuthService(provider)
	if not auth.ensure_logged_in(cl, username, password, on_log=on_log):
		if on_log:
			on_log("Authentication failed")
		return ("failed", 0, 1)

	# Save refreshed session after auth and backfill device/user_agent if missing
	try:
		settings = cl.get_settings()  # type: ignore[attr-defined]
		session_store.save(username, settings)
		log_info("[API] session saved")
		if on_log:
			on_log("Session saved")
		# backfill user_agent into device if empty
		try:
			from uploader.models import InstagramAccount
			acc = InstagramAccount.objects.filter(username=username).first()
			if acc and getattr(acc, 'device', None):
				dev = acc.device
				updates = []
				if not dev.user_agent and settings.get('user_agent'):
					dev.user_agent = settings.get('user_agent')
					updates.append('user_agent')
				if not dev.device_settings:
					dev.device_settings = device_settings
					updates.append('device_settings')
				if updates:
					dev.save(update_fields=updates)
		except Exception:
			pass
	except Exception:
		pass

	# Upload loop
	completed = 0
	failed = 0

	for idx, path in enumerate(video_files_to_upload):
		try:
			caption = ""
			try:
				caption = str(videos[idx].title or "")
			except Exception:
				caption = ""

			# Mentions as separate usertags
			mentions_text = None
			try:
				mentions_text = getattr(videos[idx], 'mentions', None)
			except Exception:
				mentions_text = None
			mention_names = _extract_mentions(mentions_text)
			usertags: List['IGUsertag'] = []
			if mention_names:
				usertags = _build_usertags(cl, mention_names)

			# Location optional
			location_obj: Optional['IGLocation'] = None
			try:
				location_text = getattr(videos[idx], 'location', None)
				location_obj = _resolve_location(cl, location_text)
			except Exception:
				location_obj = None

			log_info(f"[UPLOAD] Reels {idx+1}/{len(video_files_to_upload)}: {os.path.basename(path)}")
			if on_log:
				on_log(f"Starting upload {idx+1}/{len(video_files_to_upload)}: {os.path.basename(path)}")
			# Human-like pause before upload
			time.sleep(random.uniform(1.5, 5.0))

			# Optional thumbnail support: if file '<path>.jpg' exists, pass it
			thumb_path = None
			try:
				cand = f"{path}.jpg"
				if os.path.exists(cand):
					thumb_path = cand
			except Exception:
				thumb_path = None
			media = cl.clip_upload(  # type: ignore[attr-defined]
				path=path,
				caption=caption,
				thumbnail=thumb_path,
				usertags=usertags or None,
				location=location_obj,
			)
			code = getattr(media, 'code', None)
			completed += 1
			if code:
				log_success(f"[OK] Published: https://www.instagram.com/p/{code}/")
				if on_log:
					on_log(f"Upload successful: https://www.instagram.com/p/{code}/")
			else:
				log_success("[OK] Published a clip")
				if on_log:
					on_log("Upload successful")
			# Human-like pause after upload
			time.sleep(random.uniform(2.0, 8.0))
		except Exception as e:
			failed += 1
			log_error(f"[FAIL] clip upload error: {e}")
			if on_log:
				on_log(f"Upload failed: {e}")
			# small backoff
			time.sleep(random.uniform(4.0, 12.0))

	return ("success" if completed > 0 else "failed", completed, failed)


async def run_instagrapi_upload_async(account_details: Dict, videos: List, video_files_to_upload: List[str], task_id: int, account_task_id: int, on_log: Optional[Callable[[str], None]] = None) -> Tuple[str, int, int]:
	"""Async wrapper for the sync instagrapi upload implementation."""
	return await asyncio.to_thread(
		_sync_upload_impl,
		account_details,
		videos,
		video_files_to_upload,
		task_id,
		account_task_id,
		on_log,
	) 