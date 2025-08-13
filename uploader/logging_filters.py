import logging
import re
import time


SENSITIVE_COOKIE_NAMES = (
	'authorization', 'sessionid', 'csrftoken', 'ds_user_id', 'x-mid', 'mid',
	'ig-u-ds-user-id', 'ig-intended-user-id', 'ig-u-rur', 'rur', 'x-ig-www-claim'
)


def _mask_cookie_values(text: str) -> str:
	if not text:
		return text
	masked = text
	try:
		# Authorization=Bearer IGT:... -> Authorization=Bearer IGT:***
		masked = re.sub(r'(Authorization\s*=\s*Bearer\s+IGT:)[^;\s]+', r'\1***', masked, flags=re.IGNORECASE)
		# Common cookies: name=value -> name=*** (only for sensitive names)
		def _mask_match(m: re.Match) -> str:
			name = m.group(1)
			sep = m.group(2)
			return f"{name}{sep}***"
		pattern_names = r'(' + r'|'.join([re.escape(n) for n in SENSITIVE_COOKIE_NAMES]) + r')'
		masked = re.sub(pattern_names + r'(\s*=\s*)[^;\s]+', _mask_match, masked, flags=re.IGNORECASE)
		return masked
	except Exception:
		return text


def _ascii_sanitize(text: str) -> str:
	try:
		return text.encode('ascii', 'ignore').decode('ascii')
	except Exception:
		return str(text)


class MaskSecretsFilter(logging.Filter):
	"""Mask sensitive tokens and sanitize to ASCII."""
	def filter(self, record: logging.LogRecord) -> bool:
		try:
			msg = str(record.getMessage())
			msg = _mask_cookie_values(msg)
			msg = _ascii_sanitize(msg)
			# Replace the original message safely
			record.msg = msg
			record.args = ()
		except Exception:
			pass
		return True


class TruncateLongFilter(logging.Filter):
	"""Truncate overly long log messages to keep console readable."""
	def __init__(self, name: str = '', max_len: int = 400):
		super().__init__(name)
		self.max_len = max_len
	def filter(self, record: logging.LogRecord) -> bool:
		try:
			msg = str(record.msg)
			if len(msg) > self.max_len:
				record.msg = msg[: self.max_len] + ' ...[truncated]'
				record.args = ()
		except Exception:
			pass
		return True


class DeduplicateFilter(logging.Filter):
	"""Suppress consecutive duplicate messages within a short time window."""
	_last_msg = None
	_last_ts = 0.0
	_window_sec = 1.0
	def filter(self, record: logging.LogRecord) -> bool:
		try:
			msg = str(record.msg)
			now = time.time()
			if self.__class__._last_msg == msg and (now - self.__class__._last_ts) <= self.__class__._window_sec:
				return False
			self.__class__._last_msg = msg
			self.__class__._last_ts = now
		except Exception:
			pass
		return True 