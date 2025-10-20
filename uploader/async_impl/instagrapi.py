from typing import TYPE_CHECKING
import os
import random
import time
import asyncio
from typing import Dict, List, Tuple, Optional, Callable

from uploader.logging_utils import log_info, log_error, log_success, attach_instagrapi_web_bridge
from uploader.proxy_manager import ProxyManager
from uploader.models import InstagramAccount

# instagrapi imports (runtime)
try:
	from instagrapi import Client  # type: ignore
	from instagrapi.types import Usertag, Location  # type: ignore
	from instagrapi.exceptions import LoginRequired, RateLimitError, ChallengeError  # type: ignore
except Exception:
	Client = None  # type: ignore
	Usertag = None  # type: ignore
	Location = None  # type: ignore
	LoginRequired = Exception  # type: ignore
	RateLimitError = Exception  # type: ignore
	ChallengeError = Exception  # type: ignore

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
from ..rate_limiting_config import RateLimitingConfig, InstagramAPIErrorHandler
from ..logging_utils import log_info, log_success, log_error, log_warning, log_debug


def _extract_mentions(mentions_text: Optional[str]) -> List[str]:
	if not mentions_text or mentions_text is None:
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


def _build_usertags(cl: 'IGClient', usernames: List[str], reauth_cb: Optional[Callable[[], bool]] = None) -> List['IGUsertag']:
	user_tags: List['IGUsertag'] = []
	if not usernames or usernames is None:
		return user_tags
	
	for uname in usernames:
		max_retries = 3
		retry_count = 0
		user_resolved = False
		
		while retry_count < max_retries and not user_resolved:
			try:
				log_info(f"[USERS] Resolving @{uname} (attempt {retry_count + 1}/{max_retries})")
				
				# Add delay before user resolution to avoid rate limits
				if retry_count > 0:
					delay = RateLimitingConfig.get_retry_delay(retry_count, 'user_resolution')
					log_info(f"[USERS] Waiting {delay:.1f}s before retry for @{uname}...")
					time.sleep(delay)
				else:
					# Small delay even on first attempt
					delay = RateLimitingConfig.get_delay('user_resolution')
					time.sleep(delay)
				
				# Use strictly private API: resolve username → info via v1 endpoint only (disable public/GQL fallbacks)
				user_pk = None
				user = None
				# Force v1 for specific problematic usernames
				user_info_v1 = getattr(cl, 'user_info_by_username_v1', None)
				if callable(user_info_v1):
					info_obj = user_info_v1(uname)  # type: ignore[misc]
					user_pk = getattr(info_obj, 'pk', None)
					user = info_obj
				else:
					# Fallback to id then user_info
					user_pk = cl.user_id_from_username(uname)  # type: ignore[attr-defined]
				user_info_call = getattr(cl, 'user_info', None)
				if callable(user_info_call):
					try:
						user = user_info_call(user_pk)  # type: ignore[misc]
					except Exception:
						pass
				else:
					# As a last resort, construct a minimal user object without public/GQL fallbacks
					try:
						from instagrapi.types import UserShort  # type: ignore
						if user_pk:
							user = UserShort(pk=user_pk, username=uname)  # type: ignore
					except Exception:
						user = None
				
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
				user_resolved = True
				
			except Exception as e:
				retry_count += 1
				error_msg = str(e)
				
				# Check for specific error types using error handler
				error_category = InstagramAPIErrorHandler.get_error_category(e)
				
				if error_category == 'rate_limit':
					log_warning(f"[USERS] [RATE_LIMIT] Rate limit for @{uname}, waiting longer... (attempt {retry_count}/{max_retries})")
					wait_time = RateLimitingConfig.get_delay('user_resolution', is_retry=True, is_rate_limited=True)
					log_info(f"[USERS] [RATE_LIMIT] Waiting {wait_time:.1f}s before retry for @{uname}...")
					time.sleep(wait_time)
				elif "not found" in error_msg.lower() or "user not found" in error_msg.lower():
					log_warning(f"[USERS] User @{uname} not found, skipping...")
					break  # Don't retry for non-existent users
				elif error_category == 'challenge':
					log_warning(f"[USERS] Challenge required for @{uname}, skipping...")
					break  # Don't retry for challenges
				elif 'login_required' in error_msg.lower() or isinstance(e, LoginRequired):
					log_warning(f"[USERS] LoginRequired while resolving @{uname} - session lost during mention resolution")
					if callable(reauth_cb):
						ok = False
						try:
							ok = bool(reauth_cb())
						except Exception:
							ok = False
						if ok:
							log_info(f"[USERS] re-auth successful, retrying @{uname}...")
							# do not increment retry_count for successful reauth; continue loop to retry
							continue
						else:
							log_error(f"[USERS] re-auth failed for @{uname}, skipping mention resolution")
							break  # Skip this user if reauth fails
					else:
						log_error(f"[USERS] No reauth callback for @{uname}, skipping mention resolution")
						break  # Skip this user if no reauth callback
				else:
					log_warning(f"[USERS] Failed to resolve @{uname} (attempt {retry_count}/{max_retries}): {e}")
					# Use retry delay for other errors
					wait_time = RateLimitingConfig.get_retry_delay(retry_count, 'user_resolution')
					log_info(f"[USERS] Waiting {wait_time:.1f}s before retry for @{uname}...")
					time.sleep(wait_time)
				
				if retry_count >= max_retries:
					log_error(f"[USERS] Failed to resolve @{uname} after {max_retries} attempts: {e}")
					break
	
	return user_tags


def _resolve_location(cl: 'IGClient', location_text: Optional[str]) -> Optional['IGLocation']:
	"""Best-effort location resolver by text using Instagram's private API.
	Prioritizes fbsearch_places for better results.
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
	
	# Try Instagram's private location search first (most reliable)
	try:
		# Add delay before location search to avoid rate limits
		delay = RateLimitingConfig.get_delay('location_search')
		time.sleep(delay)
		
		# Use private fbsearch_places API for better results
		places = cl.fbsearch_places(query)  # type: ignore[attr-defined]
		if places and isinstance(places, list) and len(places) > 0:
			# Take the first/best match
			place = places[0]
			lat = getattr(place, 'lat', None) or getattr(place, 'latitude', None)
			lng = getattr(place, 'lng', None) or getattr(place, 'longitude', None)
			name = getattr(place, 'name', None) or getattr(place, 'title', None) or query
			
			if lat is not None and lng is not None:
				log_info(f"[LOCATION] fbsearch_places resolved '{query}' → ({lat},{lng}) :: {name}")
				return Location(name=str(name), lat=float(lat), lng=float(lng))  # type: ignore
			else:
				log_debug(f"[LOCATION] fbsearch_places found place '{name}' but missing coordinates")
		else:
			log_debug(f"[LOCATION] fbsearch_places returned no results for '{query}'")
	except Exception as e:
		error_category = InstagramAPIErrorHandler.get_error_category(e)
		if error_category == 'rate_limit':
			log_warning(f"[LOCATION] [RATE_LIMIT] Rate limit for fbsearch_places '{query}', trying fallback...")
		elif 'login_required' in str(e).lower() or isinstance(e, LoginRequired):
			log_warning(f"[LOCATION] Login required for fbsearch_places '{query}', trying fallback...")
		else:
			log_debug(f"[LOCATION] fbsearch_places failed for '{query}': {e}")
	
	# Fallback: try other instagrapi location search methods
	try:
		search_methods = [
			getattr(cl, 'locations_search', None),
			getattr(cl, 'location_search', None),
			getattr(cl, 'search_location', None),
		]
		for m in search_methods:
			if not callable(m):
				continue
			try:
				# Add delay before location search to avoid rate limits
				delay = RateLimitingConfig.get_delay('location_search')
				time.sleep(delay)
				
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
						log_info(f"[LOCATION] fallback method resolved '{query}' → ({lat},{lng}) :: {name}")
						return Location(name=str(name), lat=float(lat), lng=float(lng))  # runtime type
			except Exception as e:
				error_category = InstagramAPIErrorHandler.get_error_category(e)
				if error_category == 'rate_limit':
					log_warning(f"[LOCATION] [RATE_LIMIT] Rate limit for fallback search '{query}', skipping...")
					break  # Don't try other methods if rate limited
				else:
					log_debug(f"[LOCATION] Fallback search method failed for '{query}': {e}")
					continue
	except Exception:
		pass
	
	# Final fallback: try our geocoder (Nominatim + dictionary)
	try:
		coords = resolve_location_coordinates(query)
		if coords:
			name2, lat2, lon2 = coords
			log_info(f"[LOCATION] geocoded '{query}' → ({lat2},{lon2}) :: {name2}")
			return Location(name=str(name2), lat=float(lat2), lng=float(lon2))  # type: ignore
	except Exception:
		pass
	
	# Give up gracefully
	log_warning(f"[LOCATION] could not resolve '{query}' to coordinates; skipping location")
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

	# Initialize proxy manager for automatic proxy switching
	proxy_manager = ProxyManager()
	proxy_error_count = 0  # Track consecutive proxy errors
	max_proxy_switches = 3  # Maximum proxy switches per upload session

	# Load persisted device + session if available
	session_store = DjangoDeviceSessionStore()
	persisted_settings = session_store.load(username) or None
	
	# DEBUG: Log what was loaded from session store
	log_info(f"[DEBUG] session_store.load({username}) returned: {type(persisted_settings)}")
	if persisted_settings:
		log_info(f"[DEBUG] Loaded persisted_settings keys: {list(persisted_settings.keys())}")
	else:
		log_info(f"[DEBUG] No persisted_settings loaded for {username}")

	# Ensure per-account persistent device (from DB/session or generate once)
	device_settings, ua_hint = ensure_persistent_device(username, persisted_settings)

	# Resolve locale from proxy if not present in device_settings
	if not device_settings.get("locale"):
		try:
			from instgrapi_func.services.geo import resolve_geo
			geo_info = resolve_geo(proxy_dict)
			device_settings["locale"] = geo_info.get("locale", "ru_BY")
			log_info(f"[LOCALE] Resolved locale from proxy: {device_settings['locale']}")
		except Exception as geo_e:
			log_warning(f"[LOCALE] Failed to resolve locale from proxy: {geo_e}")
			device_settings["locale"] = "ru_BY"

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

	# CRITICAL: Lock proxy and device before any authentication
	# Ensure the same proxy and device are used throughout the entire session
	try:
		log_info(f"[LOCK] Locking proxy and device for {username}")
		
		# Lock proxy - ensure it's set and won't change
		if proxy_url:
			cl.set_proxy(proxy_url)
			log_info(f"[LOCK] Proxy locked: {proxy_url}")
		
		# NOTE: iPhone devices are now supported by instagrapi, no conversion needed
		user_agent = device_settings.get("user_agent") or ua_hint
		if user_agent and any(indicator in user_agent for indicator in ["iPhone", "iOS", "AppleWebKit"]):
			log_info(f"[DEVICE] Using iPhone device settings: {user_agent}")
			# iPhone devices are now supported, no conversion needed
		
		# Lock device settings - ensure they won't change during session
		device_cfg = {
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
			"uuid": device_settings.get("uuid"),
			"android_device_id": device_settings.get("android_device_id"),
			"phone_id": device_settings.get("phone_id"),
			"client_session_id": device_settings.get("client_session_id"),
			"country": device_settings.get("country"),
			"locale": device_settings.get("locale"),
		}
		cl.set_device(device_cfg)
		log_info(f"[LOCK] Device locked: {device_cfg.get('model')} {device_cfg.get('manufacturer')}")
		
		# Lock user agent if available
		if user_agent:
			# Set user agent in device config as well
			device_cfg["user_agent"] = user_agent
			cl.set_device(device_cfg)
			log_info(f"[LOCK] User agent locked: {user_agent[:50]}...")
		
		# Load persisted session settings if available (dict only)
		if persisted_settings:
			try:
				cl.set_settings(persisted_settings)  # type: ignore[attr-defined]
				log_info(f"[LOCK] Session settings loaded from persistence")
			except Exception as load_e:
				log_warning(f"[LOCK] Failed to load persisted settings: {load_e}")
		
		log_info(f"[LOCK] Proxy and device locked successfully for {username}")
			
	except Exception as lock_e:
		log_error(f"[LOCK] Failed to lock proxy/device for {username}: {lock_e}")
		if on_log:
			on_log(f"Failed to lock proxy/device: {lock_e}")
		return ("failed", 0, 1)

	# SMART SESSION RESTORATION: Use intelligent session restoration with auto-save
	session_restored = smart_session_restoration_with_save(cl, username, persisted_settings, session_store, on_log)
	
	# Initialize auth variable to None
	auth = None
	
	# Auth: use restored session or fallback to login with TOTP/email
	if not session_restored:
		auth_success, auth = perform_authentication_with_retry(cl, username, password, tfa_secret, email_login, email_password, on_log, 'authentication')
		if not auth_success:
			return ("failed", 0, 1)
	else:
		# Verify restored session is valid
		try:
			user_info = cl.user_info_v1(cl.user_id)
			if user_info and user_info.username == username:
				log_info(f"[SESSION] Session verified for {username}")
				if on_log:
					on_log("Session verified")
				# Create auth object for potential re-authentication during uploads
				provider = CompositeProvider([
					TOTPProvider(tfa_secret or None),
					AutoIMAPEmailProvider(email_login, email_password, on_log=on_log),
				])
				auth = IGAuthService(provider)
			else:
				log_warning(f"[SESSION] Session verification failed for {username}")
				if on_log:
					on_log("Session verification failed, falling back to login")
				# Fallback to login with retry logic
				auth_success, auth = perform_authentication_with_retry(cl, username, password, tfa_secret, email_login, email_password, on_log, 'fallback_authentication')
				if not auth_success:
					return ("failed", 0, 1)
		except Exception as e:
			log_warning(f"[SESSION] Session verification error for {username}: {e}")
			if on_log:
				on_log(f"Session verification error: {e}")
			# Fallback to login with retry logic
			auth_success, auth = perform_authentication_with_retry(cl, username, password, tfa_secret, email_login, email_password, on_log, 'exception_fallback_authentication')
			if not auth_success:
				return ("failed", 0, 1)
	
	# Ensure we're logged in before any API calls (mentions, locations, uploads)
	# Authentication was verified via account_info() - the gold standard
	log_info("[API] Authentication verified via account_info(), proceeding with uploads")
	if on_log:
		on_log("Authentication verified via account_info(), proceeding with uploads")

	# Save refreshed session after auth and backfill device/user_agent if missing
	try:
		settings = cl.get_settings()  # type: ignore[attr-defined]
		session_store.save(username, settings)
		log_info("[API] session saved")
		if on_log:
			on_log("Session saved")
		# Best-effort warmup to reduce rupload 403 after login
		try:
			launcher_sync = getattr(cl, 'launcher_sync', None)
			if callable(launcher_sync):
				launcher_sync()  # type: ignore[misc]
			qe_expose = getattr(cl, 'qe_expose', None)
			if callable(qe_expose):
				qe_expose()  # type: ignore[misc]
		except Exception:
			pass
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
	except Exception as e:
		log_debug(f"[API] failed to save session settings: {e}")

		# Upload loop with enhanced error handling
	completed = 0
	failed = 0

	for idx, path in enumerate(video_files_to_upload):
		max_retries = 3
		retry_count = 0
		upload_success = False
		
		# Add delay between videos (except first one)
		if idx > 0:
			inter_video_delay = random.uniform(30, 60)  # 30-60 seconds between videos
			log_info(f"[UPLOAD] Waiting {inter_video_delay:.1f}s between videos...")
			if on_log:
				on_log(f"Waiting {inter_video_delay:.1f}s between videos...")
			time.sleep(inter_video_delay)
		
		while retry_count < max_retries and not upload_success:
			try:
				# Check authentication before each upload attempt
				if retry_count > 0:
					log_info(f"[AUTH_CHECK] Re-checking authentication after retry {retry_count}")
					if on_log:
						on_log(f"Re-checking authentication after retry {retry_count}")
					
					# Re-authenticate if needed
					if not auth.ensure_logged_in(cl, username, password, on_log=on_log):
						log_error(f"[AUTH_FAIL] Authentication failed during retry {retry_count}")
						if on_log:
							on_log(f"Authentication failed during retry {retry_count}")
						break
				
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
				mention_names = _extract_mentions(mentions_text or "")
				usertags: List['IGUsertag'] = []
				if mention_names:
					def _reauth() -> bool:
						provider = CompositeProvider([
							TOTPProvider(tfa_secret or None),
							AutoIMAPEmailProvider(email_login, email_password, on_log=on_log),
						])
						return IGAuthService(provider).ensure_logged_in(cl, username, password, on_log=on_log)
					usertags = _build_usertags(cl, mention_names, reauth_cb=_reauth)

				# Location optional
				location_obj: Optional['IGLocation'] = None
				try:
					location_text = getattr(videos[idx], 'location', None)
					location_obj = _resolve_location(cl, location_text)
				except Exception:
					location_obj = None

				log_info(f"[UPLOAD] Reels {idx+1}/{len(video_files_to_upload)}: {os.path.basename(path)} (attempt {retry_count + 1}/{max_retries})")
				if on_log:
					on_log(f"Starting upload {idx+1}/{len(video_files_to_upload)}: {os.path.basename(path)} (attempt {retry_count + 1}/{max_retries})")
				
				# Enhanced human-like pause before upload (longer for retries)
				if retry_count > 0:
					delay = RateLimitingConfig.get_retry_delay(retry_count, 'upload_attempt')
				else:
					delay = RateLimitingConfig.get_delay('upload_attempt')
				log_info(f"[UPLOAD] Waiting {delay:.1f}s before upload...")
				time.sleep(delay)

				# Optional thumbnail support: if file '<path>.jpg' exists, pass it
				thumb_path = None
				try:
					cand = f"{path}.jpg"
					if os.path.exists(cand):
						thumb_path = cand
				except Exception:
					thumb_path = None
				
				# Enhanced clip_upload with better error handling
				media = cl.clip_upload(  # type: ignore[attr-defined]
					path=path,
					caption=caption,
					thumbnail=thumb_path,
					usertags=usertags if usertags else [],
					location=location_obj,
				)
				
				# Enhanced response validation
				if media is None:
					raise Exception("clip_upload returned None - no response from Instagram API")
				
				code = getattr(media, 'code', None)
				media_id = getattr(media, 'id', None)
				
				# Check if we got a valid response
				if not code and not media_id:
					raise Exception(f"Invalid response from Instagram API: {media}")
				
				completed += 1
				upload_success = True
				
				if code:
					log_success(f"[OK] Published: https://www.instagram.com/p/{code}/")
					if on_log:
						on_log(f"Upload successful: https://www.instagram.com/p/{code}/")
				else:
					log_success(f"[OK] Published a clip (ID: {media_id})")
					if on_log:
						on_log(f"Upload successful (ID: {media_id})")
				
				# Human-like pause after upload
				time.sleep(random.uniform(3.0, 10.0))
				
			except Exception as e:
				retry_count += 1
				error_msg = str(e).lower()
				
				# Enhanced error categorization and handling
				log_warning(f"[ERROR] Upload attempt {retry_count} failed: {e}")
				if on_log:
					on_log(f"Upload attempt {retry_count} failed: {e}")
				
				# Add detailed error logging for debugging
				error_type = type(e).__name__
				log_error(f"[ERROR_DETAILS] Error type: {error_type}, Message: {str(e)}")
				
				# Check for authentication errors first (using proper exception types)
				if isinstance(e, LoginRequired) or "login_required" in error_msg or "403" in error_msg or "unauthorized" in error_msg:
					log_error(f"[AUTH_ERROR] Authentication error detected: {e}")
					if on_log:
						on_log(f"Authentication error: {e}")
					
					# Try to re-authenticate
					if retry_count < max_retries and auth is not None:
						log_info(f"[AUTH_RETRY] Attempting to re-authenticate...")
						if on_log:
							on_log("Attempting to re-authenticate...")
						
						auth_delay = random.uniform(5.0, 15.0)
						time.sleep(auth_delay)
						
						if auth.ensure_logged_in(cl, username, password, on_log=on_log):
							log_info(f"[AUTH_SUCCESS] Re-authentication successful, retrying upload...")
							if on_log:
								on_log("Re-authentication successful, retrying upload...")
							continue  # Retry upload with fresh auth
						else:
							log_error(f"[AUTH_FAIL] Re-authentication failed, stopping retries")
							if on_log:
								on_log("Re-authentication failed, stopping retries")
							break
					else:
						log_error(f"[AUTH_FAIL] Cannot re-authenticate (auth object is None or max retries reached)")
						if on_log:
							on_log("Cannot re-authenticate, stopping retries")
						break
				
				# Check for rate limiting (using proper exception types)
				elif isinstance(e, RateLimitError) or "rate limit" in error_msg or "too many requests" in error_msg:
					log_warning(f"[RATE_LIMIT] Rate limit detected, waiting longer... (attempt {retry_count}/{max_retries})")
					if on_log:
						on_log(f"Rate limit detected, waiting longer...")
					
					# Exponential backoff for rate limits
					wait_time = min(300, 30 * (2 ** retry_count))  # Max 5 minutes
					log_info(f"[RATE_LIMIT] Waiting {wait_time:.1f}s before retry...")
					time.sleep(wait_time)
				
				# Check for challenges (using proper exception types)
				elif isinstance(e, ChallengeError) or "challenge" in error_msg or "checkpoint" in error_msg:
					log_error(f"[CHALLENGE] Challenge required: {e}")
					if on_log:
						on_log(f"Challenge required: {e}")
					
					# Check specifically for UFAC_WWW_BLOKS challenge which indicates account suspension
					if "UFAC_WWW_BLOKS" in str(e) or "ufac_www_bloks" in error_msg.lower():
						log_error(f"[SUSPENDED] UFAC_WWW_BLOKS challenge detected - marking account as suspended: {username}")
						if on_log:
							on_log(f"Account suspended due to UFAC_WWW_BLOKS challenge")
						
						# Update account status to SUSPENDED
						try:
							from uploader.models import InstagramAccount, BulkUploadAccount
							
							def update_account_status():
								try:
									# Update Instagram account status
									instagram_account = InstagramAccount.objects.get(username=username)
									instagram_account.status = 'SUSPENDED'
									instagram_account.save(update_fields=['status'])
									
									# Update BulkUploadAccount status for dashboard display
									try:
										bulk_accounts = BulkUploadAccount.objects.filter(account=instagram_account)
										if bulk_accounts.exists():
											bulk_accounts.update(status='SUSPENDED')
											log_info(f"[SUSPENDED] Updated {bulk_accounts.count()} BulkUploadAccount records")
									except Exception as bulk_error:
										log_warning(f"[SUSPENDED] Error updating BulkUploadAccount: {bulk_error}")
									
									return True
								except InstagramAccount.DoesNotExist:
									log_error(f"[SUSPENDED] Instagram account {username} not found")
									return False
								except Exception as db_error:
									log_error(f"[SUSPENDED] Database error updating account status: {db_error}")
									return False
							
							# Execute the status update synchronously
							update_account_status()
							
						except Exception as status_error:
							log_error(f"[SUSPENDED] Error updating account status: {status_error}")
					
					break  # Don't retry challenges
				
				# Check for proxy errors specifically
				elif "proxy" in error_msg or "ProxyError" in str(type(e)) or "RemoteDisconnected" in error_msg:
					proxy_error_count += 1
					log_warning(f"[PROXY] Proxy error detected ({proxy_error_count}/{max_proxy_switches}): {e}")
					if on_log:
						on_log(f"Proxy error ({proxy_error_count}/{max_proxy_switches}): {e}")
					
					# If we've had 3 consecutive proxy errors, try switching proxy
					if proxy_error_count >= 3 and proxy_error_count <= max_proxy_switches:
						try:
							# Get the Instagram account to switch proxy
							account = InstagramAccount.objects.get(username=username)
							log_info(f"[PROXY_SWITCH] Attempting to switch proxy for {username} (attempt {proxy_error_count})")
							if on_log:
								on_log(f"Switching proxy (attempt {proxy_error_count})...")
							
							# Get a new proxy from the same region
							new_proxy = proxy_manager.get_available_proxy(account, exclude_blocked=True)
							
							if new_proxy:
								# Update proxy in account_details for next retry
								account_details['proxy'] = {
									'host': new_proxy.host,
									'port': new_proxy.port,
									'username': new_proxy.username,
									'password': new_proxy.password,
									'type': new_proxy.proxy_type.lower()
								}
								
								log_success(f"[PROXY_SWITCH] Switched to new proxy: {new_proxy.host}:{new_proxy.port}")
								if on_log:
									on_log(f"Switched to new proxy: {new_proxy.host}:{new_proxy.port}")
								
								# Reset proxy error count after successful switch
								proxy_error_count = 0
								
								# Wait a bit before retrying with new proxy
								wait_time = random.uniform(10.0, 20.0)
								log_info(f"[PROXY_SWITCH] Waiting {wait_time:.1f}s before retry with new proxy...")
								time.sleep(wait_time)
								
								# Re-initialize client with new proxy
								proxy_url = build_proxy_url(account_details['proxy'])
								cl = Client(proxy=proxy_url)
								
								continue  # Retry with new proxy
							else:
								log_error(f"[PROXY_SWITCH] No available proxy found for {username}")
								if on_log:
									on_log("No available proxy found")
								
								# Mark current proxy as blocked
								if account.current_proxy:
									proxy_manager.mark_proxy_blocked(account.current_proxy, account, "consecutive proxy errors")
								
								# Wait longer if no proxy available
								wait_time = random.uniform(30.0, 60.0)
								log_info(f"[PROXY_SWITCH] Waiting {wait_time:.1f}s (no proxy available)...")
								time.sleep(wait_time)
								
						except Exception as proxy_switch_error:
							log_error(f"[PROXY_SWITCH] Error switching proxy: {proxy_switch_error}")
							if on_log:
								on_log(f"Error switching proxy: {proxy_switch_error}")
							
							# Fallback to regular proxy error handling
							wait_time = random.uniform(20.0, 60.0)
							log_info(f"[PROXY] Waiting {wait_time:.1f}s before retry...")
							time.sleep(wait_time)
					else:
						# Regular proxy error handling for first 2 errors
						wait_time = random.uniform(20.0, 60.0)
						log_info(f"[PROXY] Waiting {wait_time:.1f}s before retry...")
						time.sleep(wait_time)
				
				# Check for network/connection errors
				elif any(keyword in error_msg for keyword in ["connection", "timeout", "network", "dns", "RemoteDisconnected"]):
					log_warning(f"[NETWORK] Network error detected: {e}")
					if on_log:
						on_log(f"Network error: {e}")
					
					wait_time = random.uniform(15.0, 45.0)
					log_info(f"[NETWORK] Waiting {wait_time:.1f}s before retry...")
					time.sleep(wait_time)
				
				# Generic retry for other errors
				else:
					log_warning(f"[RETRY] Generic error, retrying... (attempt {retry_count}/{max_retries})")
					if on_log:
						on_log(f"Generic error, retrying...")
					
					# Exponential backoff with jitter
					wait_time = min(60, 5 * (2 ** retry_count)) + random.uniform(1.0, 5.0)
					log_info(f"[RETRY] Waiting {wait_time:.1f}s before retry...")
					time.sleep(wait_time)
				
				# Final check if we've exhausted retries
				if retry_count >= max_retries:
					failed += 1
					log_error(f"[FAIL] Upload failed after {max_retries} attempts: {e}")
					if on_log:
						on_log(f"Upload failed after {max_retries} attempts: {e}")
					
					# Final backoff after all retries failed
					final_delay = random.uniform(15.0, 45.0)
					log_info(f"[FINAL_BACKOFF] Waiting {final_delay:.1f}s before next video...")
					time.sleep(final_delay)

	# Check if all videos failed after 3 attempts - if so, mark account as suspended
	if completed == 0 and failed > 0 and len(video_files_to_upload) > 0:
		# All videos failed - check if this was due to account being inactive
		log_error(f"[ACCOUNT_STATUS] All {len(video_files_to_upload)} videos failed for account {username}")
		if on_log:
			on_log(f"All {len(video_files_to_upload)} videos failed for account {username}")
		
		# Update account status to SUSPENDED
		try:
			from uploader.models import InstagramAccount, BulkUploadAccount
			from django.utils import timezone
			
			account = InstagramAccount.objects.get(username=username)
			old_status = account.status
			account.status = 'SUSPENDED'
			account.save(update_fields=['status'])
			
			# Also update the BulkUploadAccount status if we have the account_task_id
			if account_task_id:
				try:
					bulk_account = BulkUploadAccount.objects.get(id=account_task_id)
					bulk_account.status = 'SUSPENDED'
					bulk_account.save(update_fields=['status'])
					log_error(f"[ACCOUNT_STATUS] Updated bulk upload account {account_task_id} status to SUSPENDED")
				except BulkUploadAccount.DoesNotExist:
					log_error(f"[ACCOUNT_STATUS] BulkUploadAccount with ID {account_task_id} not found")
			
			log_error(f"[ACCOUNT_STATUS] Updated account {username} status from {old_status} to SUSPENDED due to all video uploads failing")
			if on_log:
				on_log(f"Account {username} status updated to SUSPENDED due to all video uploads failing")
		except Exception as status_error:
			log_error(f"[ACCOUNT_STATUS] Failed to update account {username} status: {str(status_error)}")
			if on_log:
				on_log(f"Failed to update account {username} status: {str(status_error)}")

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


# =========================
# Authentication Helper Functions
# =========================

def perform_authentication_with_retry(cl, username: str, password: str, tfa_secret: Optional[str], email_login: Optional[str], email_password: Optional[str], on_log: Optional[Callable[[str], None]] = None, config_type: str = 'authentication') -> Tuple[bool, Optional[IGAuthService]]:
	"""
	Perform authentication with retry logic using configuration.
	
	Args:
		cl: Instagram client
		username: Username
		password: Password
		tfa_secret: TOTP secret
		email_login: Email login
		email_password: Email password
		on_log: Logging callback
		config_type: Configuration type for retry settings
		
	Returns:
		Tuple of (success, auth_service)
	"""
	# Import configuration
	try:
		from instgrapi_func.services.auth_retry_config import auth_retry_config
		config = auth_retry_config.get_authentication_config()
		if config_type == 'fallback_authentication':
			config = auth_retry_config.get_fallback_authentication_config()
		elif config_type == 'exception_fallback_authentication':
			config = auth_retry_config.get_exception_fallback_authentication_config()
		max_retries = config['max_retries']
	except ImportError:
		max_retries = 3
	
	auth_success = False
	auth_service = None
	
	for auth_attempt in range(max_retries):
		provider = CompositeProvider([
			TOTPProvider(tfa_secret or None),
			AutoIMAPEmailProvider(email_login, email_password, on_log=on_log),
		])
		auth_service = IGAuthService(provider)
		
		log_info(f"[AUTH] {config_type} attempt {auth_attempt + 1}/{max_retries} for {username}")
		if on_log:
			on_log(f"{config_type} attempt {auth_attempt + 1}/{max_retries}")
		
		if auth_service.ensure_logged_in(cl, username, password, on_log=on_log):
			log_info(f"[AUTH] {config_type} successful for {username}")
			if on_log:
				on_log(f"{config_type} successful")
			auth_success = True
			break
		else:
			log_warning(f"[AUTH] {config_type} failed for {username} (attempt {auth_attempt + 1}/{max_retries})")
			if on_log:
				on_log(f"{config_type} failed (attempt {auth_attempt + 1}/{max_retries})")
			
			# If not the last attempt, wait before retry
			if auth_attempt < max_retries - 1:
				import time
				import random
				try:
					delay = auth_retry_config.calculate_delay(auth_attempt, config_type)
				except:
					delay = random.uniform(5, 10) * (auth_attempt + 1)  # Fallback
				log_info(f"[AUTH] Waiting {delay:.1f}s before retry for {username}")
				if on_log:
					on_log(f"Waiting {delay:.1f}s before retry...")
				time.sleep(delay)
	
	if not auth_success:
		log_error(f"[AUTH] All {max_retries} {config_type} attempts failed for {username}")
		if on_log:
			on_log(f"All {max_retries} {config_type} attempts failed")
	
	return auth_success, auth_service


# =========================
# Smart Session Restoration with Auto-Save
# =========================

def smart_session_restoration_with_save(cl, username: str, persisted_settings: Optional[Dict], session_store, on_log: Optional[Callable[[str], None]] = None, max_retries: int = None) -> bool:
	"""
	Smart session restoration that:
	1. Attempts to restore from bundle if valid (single attempt - if invalid, retries won't help)
	2. Automatically saves refreshed session after successful restoration
	3. Returns True if session was successfully restored, False otherwise
	"""
	# Import configuration
	try:
		from instgrapi_func.services.auth_retry_config import auth_retry_config
		session_config = auth_retry_config.get_session_restoration_config()
		if max_retries is None:
			max_retries = session_config['max_retries']
	except ImportError:
		if max_retries is None:
			max_retries = 1  # Single attempt by default
	
	session_restored = False
	
	# Check if we have a valid session bundle
	if persisted_settings and persisted_settings.get('authorization_data', {}).get('sessionid'):
		sessionid = persisted_settings['authorization_data']['sessionid']
		import urllib.parse
		sessionid = urllib.parse.unquote(sessionid)
		
		if isinstance(sessionid, str) and len(sessionid) > 30:
			try:
				log_info(f"[SESSION] Attempting to restore session for {username}")
				if on_log:
					on_log(f"Restoring session from bundle...")
				
				result = cl.login_by_sessionid(sessionid)
				if result:
					log_info(f"[SESSION] Successfully restored session for {username}")
					if on_log:
						on_log("Session restored successfully")
					session_restored = True
					
					# CRITICAL: Save refreshed session after successful restoration
					try:
						settings = cl.get_settings()  # type: ignore[attr-defined]
						session_store.save(username, settings)
						log_info("[SESSION] Restored session saved to bundle")
						if on_log:
							on_log("Restored session saved")
					except Exception as e:
						log_warning(f"[SESSION] Failed to save restored session: {e}")
				else:
					log_warning(f"[SESSION] Failed to restore session for {username} - session is invalid")
					if on_log:
						on_log("Session restoration failed - session is invalid")
			except Exception as e:
				log_warning(f"[SESSION] Session restoration error for {username}: {e}")
				if on_log:
					on_log(f"Session restoration error: {e}")
	else:
		log_info(f"[SESSION] No persisted session data found for {username}")
	
	return session_restored


# =========================
# Photo upload implementation
# =========================

def _sync_photo_upload_impl(account_details: Dict, photo_files_to_upload: List[str], captions: Optional[List[str]], mentions_list: Optional[List[Optional[str]]], locations_list: Optional[List[Optional[str]]], on_log: Optional[Callable[[str], None]] = None) -> Tuple[str, int, int]:
	if Client is None:
		log_error("[API] instagrapi not available")
		return ("failed", 0, 1)

	# Attach bridge so instagrapi/public/private logs appear in UI
	attach_instagrapi_web_bridge()

	username = account_details.get('username')
	password = account_details.get('password')
	tfa_secret = (account_details.get('tfa_secret') or '')
	email_login = (account_details.get('email_login') or account_details.get('email') or '')
	email_password = (account_details.get('email_password') or '')
	proxy_dict = account_details.get('proxy') or {}
	proxy_url = build_proxy_url(proxy_dict)

	log_info(f"[API] Starting instagrapi photo upload for {username}")
	if on_log:
		on_log(f"Starting instagrapi photo upload for {username}")

	# Initialize proxy manager for automatic proxy switching
	proxy_manager = ProxyManager()
	proxy_error_count = 0  # Track consecutive proxy errors
	max_proxy_switches = 3  # Maximum proxy switches per upload session

	# Load persisted device + session if available
	session_store = DjangoDeviceSessionStore()
	persisted_settings = session_store.load(username) or None
	
	# DEBUG: Log what was loaded from session store
	log_info(f"[DEBUG] session_store.load({username}) returned: {type(persisted_settings)}")
	if persisted_settings:
		log_info(f"[DEBUG] Loaded persisted_settings keys: {list(persisted_settings.keys())}")
	else:
		log_info(f"[DEBUG] No persisted_settings loaded for {username}")

	# Ensure per-account persistent device (from DB/session or generate once)
	device_settings, ua_hint = ensure_persistent_device(username, persisted_settings)

	# Resolve locale from proxy if not present in device_settings
	if not device_settings.get("locale"):
		try:
			from instgrapi_func.services.geo import resolve_geo
			geo_info = resolve_geo(proxy_dict)
			device_settings["locale"] = geo_info.get("locale", "ru_BY")
			log_info(f"[LOCALE] Resolved locale from proxy: {device_settings['locale']}")
		except Exception as geo_e:
			log_warning(f"[LOCALE] Failed to resolve locale from proxy: {geo_e}")
			device_settings["locale"] = "ru_BY"

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

	# OPTIMIZED SESSION HANDLING: Try direct session use first, then restore if needed
	session_restored = False
	
	# First, try to use existing session directly if we have valid sessionid
	if persisted_settings and persisted_settings.get('authorization_data', {}).get('sessionid'):
		sessionid = persisted_settings['authorization_data']['sessionid']
		import urllib.parse
		sessionid = urllib.parse.unquote(sessionid)
		
		if isinstance(sessionid, str) and len(sessionid) > 30:
			try:
				# Try to use session directly without restoration
				cl.set_settings(persisted_settings)
				user_info = cl.user_info_v1(cl.user_id)
				if user_info and user_info.username == username:
					log_info(f"[SESSION] Using existing session directly for {username}")
					if on_log:
						on_log("Using existing session directly")
					session_restored = True
				else:
					log_info(f"[SESSION] Existing session invalid, attempting restoration for {username}")
					if on_log:
						on_log("Existing session invalid, attempting restoration")
			except Exception as e:
				log_info(f"[SESSION] Direct session use failed for {username}: {e}")
				if on_log:
					on_log(f"Direct session use failed: {e}")
	
	# If direct session use failed, try restoration
	if not session_restored:
		session_restored = smart_session_restoration_with_save(cl, username, persisted_settings, session_store, on_log)
	
	# Initialize auth variable to None
	auth = None
	
	# Auth: use restored session or fallback to login with TOTP/email
	if not session_restored:
		auth_success, auth = perform_authentication_with_retry(cl, username, password, tfa_secret, email_login, email_password, on_log, 'authentication')
		if not auth_success:
			return ("failed", 0, 1)
	else:
		# Verify restored session is valid
		try:
			user_info = cl.user_info_v1(cl.user_id)
			if user_info and user_info.username == username:
				log_info(f"[SESSION] Session verified for {username}")
				if on_log:
					on_log("Session verified")
				# Create auth object for potential re-authentication during uploads
				provider = CompositeProvider([
					TOTPProvider(tfa_secret or None),
					AutoIMAPEmailProvider(email_login, email_password, on_log=on_log),
				])
				auth = IGAuthService(provider)
			else:
				log_warning(f"[SESSION] Session verification failed for {username}")
				if on_log:
					on_log("Session verification failed, falling back to login")
				# Fallback to login with retry logic
				auth_success, auth = perform_authentication_with_retry(cl, username, password, tfa_secret, email_login, email_password, on_log, 'fallback_authentication')
				if not auth_success:
					return ("failed", 0, 1)
		except Exception as e:
			log_warning(f"[SESSION] Session verification error for {username}: {e}")
			if on_log:
				on_log(f"Session verification error: {e}")
			# Fallback to login with retry logic
			auth_success, auth = perform_authentication_with_retry(cl, username, password, tfa_secret, email_login, email_password, on_log, 'exception_fallback_authentication')
			if not auth_success:
				return ("failed", 0, 1)
	
	# Ensure we're logged in before any API calls (mentions, locations, uploads)
	# Authentication was verified via account_info() - the gold standard
	log_info("[API] Authentication verified via account_info(), proceeding with photo uploads")
	if on_log:
		on_log("Authentication verified via account_info(), proceeding with photo uploads")

	# Save refreshed session after auth
	try:
		settings = cl.get_settings()  # type: ignore[attr-defined]
		session_store.save(username, settings)
		log_info("[API] session saved")
		if on_log:
			on_log("Session saved")
	except Exception:
		pass

	completed = 0
	failure = 0

	for idx, path in enumerate(photo_files_to_upload):
		max_retries = 3
		retry_count = 0
		upload_success = False

		# Inter-photo human delay (skip for first)
		if idx > 0:
			inter_delay = random.uniform(15.0, 35.0)
			log_info(f"[UPLOAD] Waiting {inter_delay:.1f}s between photos...")
			if on_log:
				on_log(f"Waiting {inter_delay:.1f}s between photos...")
			time.sleep(inter_delay)

		while retry_count < max_retries and not upload_success:
			try:
				# On retries, re-check auth
				if retry_count > 0:
					log_info(f"[AUTH_CHECK] Re-checking authentication after retry {retry_count}")
					if on_log:
						on_log(f"Re-checking authentication after retry {retry_count}")
					if not auth.ensure_logged_in(cl, username, password, on_log=on_log):
						log_error("[AUTH_FAIL] Authentication failed during retry")
						if on_log:
							on_log("Authentication failed during retry")
						break

				caption = ""
				if captions and idx < len(captions):
					try:
						caption = str(captions[idx] or "")
					except Exception:
						caption = ""

				mention_text = None
				if mentions_list and idx < len(mentions_list):
					mention_text = mentions_list[idx]
				mention_names = _extract_mentions(mention_text or "")
				usertags: List['IGUsertag'] = []
				if mention_names:
					usertags = _build_usertags(cl, mention_names)

				location_obj: Optional['IGLocation'] = None
				if locations_list and idx < len(locations_list):
					try:
						location_obj = _resolve_location(cl, locations_list[idx])
					except Exception:
						location_obj = None

				log_info(f"[UPLOAD] Photo {idx+1}/{len(photo_files_to_upload)}: {os.path.basename(path)} (attempt {retry_count + 1}/{max_retries})")
				if on_log:
					on_log(f"Starting photo upload {idx+1}/{len(photo_files_to_upload)}: {os.path.basename(path)} (attempt {retry_count + 1}/{max_retries})")

				# Human-like pause before upload
				pre_delay = random.uniform(2.0, 6.0) if retry_count == 0 else min(20.0, 4.0 * (2 ** retry_count))
				log_info(f"[UPLOAD] Waiting {pre_delay:.1f}s before upload...")
				time.sleep(pre_delay)

				# Debug: log only basic info, not full JSON responses
				try:
					# Skip logging full JSON to avoid console spam
					pass
				except Exception:
					pass

				media = cl.photo_upload(  # type: ignore[attr-defined]
					path=path,
					caption=caption,
					usertags=usertags if usertags else [],
					location=location_obj,
				)

				if media is None:
					raise Exception("photo_upload returned None - no response from Instagram API")

				code = getattr(media, 'code', None)
				media_id = getattr(media, 'id', None)
				if not code and not media_id:
					raise Exception(f"Invalid response from Instagram API: {media}")

				upload_success = True
				completed += 1
				if code:
					log_success(f"[OK] Published: https://www.instagram.com/p/{code}/")
					if on_log:
						on_log(f"Upload successful: https://www.instagram.com/p/{code}/")
				else:
					log_success(f"[OK] Published a photo (ID: {media_id})")
					if on_log:
						on_log(f"Upload successful (ID: {media_id})")

				# brief pause after success
				time.sleep(random.uniform(2.0, 5.0))

			except Exception as e:
				retry_count += 1
				error_msg = str(e).lower()
				log_warning(f"[ERROR] Photo upload attempt {retry_count} failed: {e}")
				if on_log:
					on_log(f"Photo upload attempt {retry_count} failed: {e}")
				# Log only status codes for diagnostics, not full JSON responses
				try:
					lr = getattr(getattr(cl, 'private', None), 'last_response', None)
					if lr is not None:
						try:
							status = getattr(lr, 'status_code', '?')
							log_debug(f"[API] last_response.status: {status}")
							# Skip logging full response text to avoid huge JSON dumps
						except Exception:
							pass
				except Exception:
					pass

				if isinstance(e, LoginRequired) or "login_required" in error_msg or "403" in error_msg or "unauthorized" in error_msg:
					log_error(f"[AUTH_ERROR] Authentication error detected: {e}")
					if on_log:
						on_log(f"Authentication error: {e}")
					if retry_count < max_retries and auth.ensure_logged_in(cl, username, password, on_log=on_log):
						continue
					else:
						break
				elif isinstance(e, RateLimitError) or "rate limit" in error_msg or "too many requests" in error_msg:
					wait_time = min(180, 20 * (2 ** retry_count))
					log_warning(f"[RATE_LIMIT] Waiting {wait_time:.1f}s before retry...")
					time.sleep(wait_time)
				elif isinstance(e, ChallengeError) or "challenge" in error_msg or "checkpoint" in error_msg or "400" in error_msg:
					log_error(f"[CHALLENGE] Challenge required: {e}")
					if on_log:
						on_log(f"Challenge required: {e}")
					
					# Check specifically for UFAC_WWW_BLOKS challenge which indicates account suspension
					if "UFAC_WWW_BLOKS" in str(e) or "ufac_www_bloks" in error_msg.lower():
						log_error(f"[SUSPENDED] UFAC_WWW_BLOKS challenge detected - marking account as suspended: {username}")
						if on_log:
							on_log(f"Account suspended due to UFAC_WWW_BLOKS challenge")
						
						# Update account status to SUSPENDED
						try:
							from uploader.models import InstagramAccount, BulkUploadAccount
							
							def update_account_status():
								try:
									# Update Instagram account status
									instagram_account = InstagramAccount.objects.get(username=username)
									instagram_account.status = 'SUSPENDED'
									instagram_account.save(update_fields=['status'])
									
									# Update BulkUploadAccount status for dashboard display
									try:
										bulk_accounts = BulkUploadAccount.objects.filter(account=instagram_account)
										if bulk_accounts.exists():
											bulk_accounts.update(status='SUSPENDED')
											log_info(f"[SUSPENDED] Updated {bulk_accounts.count()} BulkUploadAccount records")
									except Exception as bulk_error:
										log_warning(f"[SUSPENDED] Error updating BulkUploadAccount: {bulk_error}")
									
									return True
								except InstagramAccount.DoesNotExist:
									log_error(f"[SUSPENDED] Instagram account {username} not found")
									return False
								except Exception as db_error:
									log_error(f"[SUSPENDED] Database error updating account status: {db_error}")
									return False
							
							# Execute the status update synchronously
							update_account_status()
							
						except Exception as status_error:
							log_error(f"[SUSPENDED] Error updating account status: {status_error}")
						
						break  # Don't retry suspended accounts
					
					# Log the actual response for debugging
					try:
						lr = getattr(getattr(cl, 'private', None), 'last_response', None)
						if lr is not None:
							log_debug(f"[CHALLENGE] Response text: {lr.text[:500]}")
							# Check if this is actually a challenge
							if "challenge" in lr.text.lower() or "checkpoint" in lr.text.lower():
								log_info(f"[CHALLENGE] Attempting to resolve challenge for {username}")
								if on_log:
									on_log("Attempting to resolve challenge...")
								try:
									# Try to resolve challenge
									cl.challenge_resolve(cl.last_json)
									log_info(f"[CHALLENGE] Challenge resolved for {username}, retrying upload")
									if on_log:
										on_log("Challenge resolved, retrying upload")
									continue  # Retry the upload
								except Exception as challenge_e:
									log_error(f"[CHALLENGE] Failed to resolve challenge for {username}: {challenge_e}")
									if on_log:
										on_log(f"Challenge resolution failed: {challenge_e}")
					except Exception:
						pass
					break
				elif "proxy" in error_msg or "ProxyError" in str(type(e)) or "RemoteDisconnected" in error_msg:
					proxy_error_count += 1
					log_warning(f"[PROXY] Proxy error detected ({proxy_error_count}/{max_proxy_switches}): {e}")
					if on_log:
						on_log(f"Proxy error ({proxy_error_count}/{max_proxy_switches}): {e}")
					
					# If we've had 3 consecutive proxy errors, try switching proxy
					if proxy_error_count >= 3 and proxy_error_count <= max_proxy_switches:
						try:
							# Get the Instagram account to switch proxy
							account = InstagramAccount.objects.get(username=username)
							log_info(f"[PROXY_SWITCH] Attempting to switch proxy for {username} (attempt {proxy_error_count})")
							if on_log:
								on_log(f"Switching proxy (attempt {proxy_error_count})...")
							
							# Get a new proxy from the same region
							new_proxy = proxy_manager.get_available_proxy(account, exclude_blocked=True)
							
							if new_proxy:
								# Update proxy in account_details for next retry
								account_details['proxy'] = {
									'host': new_proxy.host,
									'port': new_proxy.port,
									'username': new_proxy.username,
									'password': new_proxy.password,
									'type': new_proxy.proxy_type.lower()
								}
								
								log_success(f"[PROXY_SWITCH] Switched to new proxy: {new_proxy.host}:{new_proxy.port}")
								if on_log:
									on_log(f"Switched to new proxy: {new_proxy.host}:{new_proxy.port}")
								
								# Reset proxy error count after successful switch
								proxy_error_count = 0
								
								# Wait a bit before retrying with new proxy
								wait_time = random.uniform(10.0, 20.0)
								log_info(f"[PROXY_SWITCH] Waiting {wait_time:.1f}s before retry with new proxy...")
								time.sleep(wait_time)
								
								# Re-initialize client with new proxy
								proxy_url = build_proxy_url(account_details['proxy'])
								cl = Client(proxy=proxy_url)
								
								continue  # Retry with new proxy
							else:
								log_error(f"[PROXY_SWITCH] No available proxy found for {username}")
								if on_log:
									on_log("No available proxy found")
								
								# Mark current proxy as blocked
								if account.current_proxy:
									proxy_manager.mark_proxy_blocked(account.current_proxy, account, "consecutive proxy errors")
								
								# Wait longer if no proxy available
								wait_time = random.uniform(30.0, 60.0)
								log_info(f"[PROXY_SWITCH] Waiting {wait_time:.1f}s (no proxy available)...")
								time.sleep(wait_time)
								
						except Exception as proxy_switch_error:
							log_error(f"[PROXY_SWITCH] Error switching proxy: {proxy_switch_error}")
							if on_log:
								on_log(f"Error switching proxy: {proxy_switch_error}")
							
							# Fallback to regular proxy error handling
							wait_time = random.uniform(20.0, 60.0)
							log_info(f"[PROXY] Waiting {wait_time:.1f}s before retry...")
							time.sleep(wait_time)
					else:
						# Regular proxy error handling for first 2 errors
						wait_time = random.uniform(20.0, 60.0)
						log_info(f"[PROXY] Waiting {wait_time:.1f}s before retry...")
						time.sleep(wait_time)
				elif any(k in error_msg for k in ["connection", "timeout", "network", "dns", "RemoteDisconnected"]):
					wait_time = random.uniform(15.0, 45.0)
					log_warning(f"[NETWORK] Waiting {wait_time:.1f}s before retry...")
					time.sleep(wait_time)
				else:
					wait_time = min(60, 5 * (2 ** retry_count)) + random.uniform(1.0, 4.0)
					log_warning(f"[RETRY] Waiting {wait_time:.1f}s before retry...")
					time.sleep(wait_time)

				if retry_count >= max_retries:
					failure += 1
					log_error(f"[FAIL] Photo upload failed after {max_retries} attempts: {e}")
					if on_log:
						on_log(f"Photo upload failed after {max_retries} attempts: {e}")
					final_delay = random.uniform(10.0, 25.0)
					log_info(f"[FINAL_BACKOFF] Waiting {final_delay:.1f}s before next photo...")
					time.sleep(final_delay)

	# Check if all photos failed after 3 attempts - if so, mark account as suspended
	if completed == 0 and failure > 0 and len(photo_files_to_upload) > 0:
		# All photos failed - check if this was due to account being inactive
		log_error(f"[ACCOUNT_STATUS] All {len(photo_files_to_upload)} photos failed for account {username}")
		if on_log:
			on_log(f"All {len(photo_files_to_upload)} photos failed for account {username}")
		
		# Update account status to SUSPENDED
		try:
			from uploader.models import InstagramAccount
			from django.utils import timezone
			
			account = InstagramAccount.objects.get(username=username)
			old_status = account.status
			account.status = 'SUSPENDED'
			account.save(update_fields=['status'])
			
			log_error(f"[ACCOUNT_STATUS] Updated account {username} status from {old_status} to SUSPENDED due to all photo uploads failing")
			if on_log:
				on_log(f"Account {username} status updated to SUSPENDED due to all photo uploads failing")
		except Exception as status_error:
			log_error(f"[ACCOUNT_STATUS] Failed to update account {username} status: {str(status_error)}")
			if on_log:
				on_log(f"Failed to update account {username} status: {str(status_error)}")

	return ("success" if completed > 0 else "failed", completed, failure)


async def run_instagrapi_photo_upload_async(account_details: Dict, photo_files_to_upload: List[str], captions: Optional[List[str]] = None, mentions_list: Optional[List[Optional[str]]] = None, locations_list: Optional[List[Optional[str]]] = None, on_log: Optional[Callable[[str], None]] = None) -> Tuple[str, int, int]:
	"""Async wrapper for photo upload implementation.

	Arguments lengths align by index: each photo can have its own caption, mentions text, and location text.
	Missing entries default to empty/None.
	"""
	return await asyncio.to_thread(
		_sync_photo_upload_impl,
		account_details,
		photo_files_to_upload,
		captions,
		mentions_list,
		locations_list,
		on_log,
	)