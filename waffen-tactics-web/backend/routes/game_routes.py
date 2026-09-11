

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import jwt
import datetime
import os
import sys
import asyncio
import ipaddress
import logging
import socket
import tempfile
from urllib.parse import urljoin, urlsplit
from pathlib import Path
from functools import wraps
from flask import Blueprint, request, jsonify

try:
    from dotenv import load_dotenv
except Exception:
    # If python-dotenv is not available in the current runtime, provide a
    # harmless fallback so the service can still start (useful in CI or
    # containers where env is provided externally).
    def load_dotenv(path=None):
        print('⚠️ python-dotenv not available; skipping .env load')
        return False

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'waffen-tactics' / 'src'))
# Auth exchange endpoint moved to `routes.auth` (registered at `/auth/exchange`)
from waffen_tactics.services.database import DatabaseManager
from waffen_tactics.services.game_manager import GameManager
from waffen_tactics.models.player_state import PlayerState

from routes.auth import auth_bp, require_auth, verify_token

# Import refactored modules
from .game_state_utils import run_async, enrich_player_state
from .game_management import get_state, start_game, reset_game, surrender_game, init_sample_bots
from .game_actions import buy_unit, sell_unit, move_to_board, switch_line, move_to_bench, reroll_shop, buy_xp, toggle_shop_lock, get_items, equip_item_route, combine_item_route
from .game_data import get_leaderboard, get_leaderboard_data, get_units, get_traits
from .game_combat import start_combat

# Persistent stacking rules
HP_STACK_PER_STAR = 5  # default
DB_PATH = str(Path(__file__).parent.parent.parent.parent / 'waffen-tactics' / 'waffen_tactics_game.db')
db_manager = DatabaseManager(DB_PATH)
game_manager = GameManager()
game_bp = Blueprint('game', __name__)
logger = logging.getLogger(__name__)
AVATAR_DIRECTORY = Path(__file__).parent.parent.parent / 'public' / 'avatars' / 'players'
AVATAR_MAX_BYTES = int(os.getenv('AVATAR_MAX_BYTES', str(5 * 1024 * 1024)))
AVATAR_MAX_REDIRECTS = int(os.getenv('AVATAR_MAX_REDIRECTS', '3'))
AVATAR_TIMEOUT = (
    float(os.getenv('AVATAR_CONNECT_TIMEOUT_SECONDS', '3.05')),
    float(os.getenv('AVATAR_READ_TIMEOUT_SECONDS', '5')),
)


class AvatarFetchError(RuntimeError):
    """Safe internal error for rejected or incomplete avatar downloads."""

    def __init__(self, reason: str, *, upstream_status: int | None = None):
        super().__init__(reason)
        self.reason = reason
        self.upstream_status = upstream_status


def _avatar_allowed_hosts():
    configured = os.getenv('AVATAR_ALLOWED_HOSTS', 'cdn.discordapp.com')
    return {
        host.strip().lower().rstrip('.')
        for host in configured.split(',')
        if host.strip()
    }


def _validate_avatar_url(url: str, allowed_hosts=None):
    """Validate scheme, host, port and every resolved address before fetch."""
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise AvatarFetchError('invalid_url') from exc
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
        raise AvatarFetchError('unsupported_url')
    if parsed.username or parsed.password:
        raise AvatarFetchError('credentials_in_url')
    host = parsed.hostname.lower().rstrip('.')
    allowed = allowed_hosts if allowed_hosts is not None else _avatar_allowed_hosts()
    if host not in allowed:
        raise AvatarFetchError('host_not_allowed')
    try:
        port = parsed.port
    except ValueError as exc:
        raise AvatarFetchError('invalid_port') from exc
    if port is not None and port != (443 if parsed.scheme == 'https' else 80):
        raise AvatarFetchError('port_not_allowed')
    try:
        addresses = socket.getaddrinfo(
            host,
            port or (443 if parsed.scheme == 'https' else 80),
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise AvatarFetchError('host_unresolvable') from exc
    if not addresses:
        raise AvatarFetchError('host_unresolvable')
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address[4][0])
        except (ValueError, IndexError) as exc:
            raise AvatarFetchError('invalid_resolved_address') from exc
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
            or str(ip) in {'100.100.100.200', '169.254.169.254'}
        ):
            raise AvatarFetchError('private_address')
    return parsed


def _image_bytes_from_response(response):
    if response.status_code != 200:
        raise AvatarFetchError('upstream_status', upstream_status=response.status_code)
    content_type = response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
    allowed_types = {
        'image/png': b'\x89PNG\r\n\x1a\n',
        'image/jpeg': b'\xff\xd8\xff',
        'image/gif': (b'GIF87a', b'GIF89a'),
        'image/webp': b'RIFF',
    }
    signature = allowed_types.get(content_type)
    if signature is None:
        raise AvatarFetchError('content_type_not_allowed')
    try:
        declared_length = response.headers.get('Content-Length')
        if declared_length is not None and int(declared_length) > AVATAR_MAX_BYTES:
            raise AvatarFetchError('response_too_large')
    except (TypeError, ValueError) as exc:
        raise AvatarFetchError('invalid_content_length') from exc

    data = bytearray()
    try:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            data.extend(chunk)
            if len(data) > AVATAR_MAX_BYTES:
                raise AvatarFetchError('response_too_large')
    except AvatarFetchError:
        raise
    except requests.RequestException as exc:
        raise AvatarFetchError('download_failed') from exc
    if not data or (declared_length is not None and len(data) != int(declared_length)):
        raise AvatarFetchError('incomplete_response')
    if isinstance(signature, tuple):
        valid_signature = any(data.startswith(item) for item in signature)
    else:
        valid_signature = data.startswith(signature)
    if not valid_signature:
        raise AvatarFetchError('invalid_image')
    return bytes(data)


def _fetch_avatar_bytes(url: str):
    current_url = url
    for _ in range(AVATAR_MAX_REDIRECTS + 1):
        _validate_avatar_url(current_url)
        try:
            response = requests.get(
                current_url,
                timeout=AVATAR_TIMEOUT,
                allow_redirects=False,
                stream=True,
            )
        except requests.RequestException as exc:
            raise AvatarFetchError('download_failed') from exc
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get('Location')
            close_response = getattr(response, 'close', None)
            if close_response:
                close_response()
            if not location:
                raise AvatarFetchError('redirect_missing_location')
            current_url = urljoin(current_url, location)
            continue
        try:
            return _image_bytes_from_response(response)
        finally:
            close_response = getattr(response, 'close', None)
            if close_response:
                close_response()
    raise AvatarFetchError('too_many_redirects')


def _write_avatar_atomically(data: bytes, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    root = destination.parent.resolve()
    resolved_destination = destination.resolve()
    if resolved_destination.parent != root:
        raise AvatarFetchError('invalid_destination')
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='wb', dir=root, prefix=f'.{destination.stem}.', suffix='.tmp', delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, resolved_destination)
    except OSError as exc:
        raise AvatarFetchError('local_write_failed') from exc
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink(missing_ok=True)

# Routes

@game_bp.route('/state', methods=['GET'])
@require_auth
def get_state_route(user_id):
    print(f"🎯 get_state_route called with user_id: {user_id}")
    return get_state(user_id)

@game_bp.route('/start', methods=['POST'])
@require_auth
def start_game_route(user_id):
    return start_game(user_id)

@game_bp.route('/buy', methods=['POST'])
@require_auth
def buy_unit_route(user_id):
    return buy_unit(user_id)

@game_bp.route('/sell', methods=['POST'])
@require_auth
def sell_unit_route(user_id):
    return sell_unit(user_id)

@game_bp.route('/move-to-board', methods=['POST'])
@require_auth
def move_to_board_route(user_id):
    return move_to_board(user_id)

@game_bp.route('/switch-line', methods=['POST'])
@require_auth
def switch_line_route(user_id):
    return switch_line(user_id)

@game_bp.route('/move-to-bench', methods=['POST'])
@require_auth
def move_to_bench_route(user_id):
    return move_to_bench(user_id)

@game_bp.route('/reroll', methods=['POST'])
@require_auth
def reroll_shop_route(user_id):
    return reroll_shop(user_id)

@game_bp.route('/buy-xp', methods=['POST'])
@require_auth
def buy_xp_route(user_id):
    return buy_xp(user_id)

@game_bp.route('/toggle-lock', methods=['POST'])
@require_auth
def toggle_shop_lock_route(user_id):
    return toggle_shop_lock(user_id)

@game_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard_route():
    # Support optional ?period=24h|all (default to last 24h)
    period = request.args.get('period', '24h')
    try:
        leaderboard = get_leaderboard_data(period=period)
        return jsonify(leaderboard)
    except Exception as e:
        print('Error fetching leaderboard:', e)
        return jsonify([]), 500

@game_bp.route('/units', methods=['GET'])
def get_units_route():
    return get_units()

@game_bp.route('/traits', methods=['GET'])
def get_traits_route():
    return get_traits()

@game_bp.route('/items', methods=['GET'])
def get_items_route():
    return get_items()

@game_bp.route('/equip-item', methods=['POST'])
@require_auth
def equip_item_route_api(user_id):
    return equip_item_route(user_id)

@game_bp.route('/combine-item', methods=['POST'])
@require_auth
def combine_item_route_api(user_id):
    return combine_item_route(user_id)

@game_bp.route('/combat', methods=['POST'])
def start_combat_route():
    return start_combat()

@game_bp.route('/reset', methods=['POST'])
@require_auth
def reset_game_route(user_id):
    return reset_game(user_id)

@game_bp.route('/surrender', methods=['POST'])
@require_auth
def surrender_game_route(user_id):
    # Get payload for username
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    payload = verify_token(token)
    return surrender_game(user_id, payload)


# Player avatar caching endpoint
@game_bp.route('/player-avatar', methods=['POST'])
@require_auth
def player_avatar_route(user_id):
    """Ensure player's avatar PNG is downloaded into `public/avatars/players/{user_id}.png`.
    If file already exists, returns cached path. Otherwise downloads from provided
    `avatarUrl` (or derives it from the JWT payload) and saves it.
    """
    request_id = getattr(request, 'request_id', 'unknown')
    try:
        data = request.get_json(silent=True)
        if data is None:
            # An empty body is valid: the verified JWT may provide the
            # avatar hash.  A non-empty undecodable body must fail at the
            # request boundary instead of entering the derived-avatar path.
            if request.get_data(cache=True):
                logger.warning(
                    'avatar request rejected request_id=%s reason=invalid_json_object',
                    request_id,
                )
                return jsonify({
                    'error': 'Avatar unavailable',
                    'code': 'avatar_fetch_failed',
                    'request_id': request_id,
                }), 400
            data = {}
        elif not isinstance(data, dict):
            logger.warning(
                'avatar request rejected request_id=%s reason=invalid_json_object',
                request_id,
            )
            return jsonify({
                'error': 'Avatar unavailable',
                'code': 'avatar_fetch_failed',
                'request_id': request_id,
            }), 400
        avatar_url = data.get('avatarUrl')

        # Try to obtain avatar hash from token payload if URL not provided
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        payload = verify_token(token)
        avatar_hash = payload.get('avatar')
        if not avatar_url and avatar_hash:
            # Build Discord CDN URL
            avatar_url = f"https://cdn.discordapp.com/avatars/{payload.get('user_id')}/{avatar_hash}.png?size=256"

        if not avatar_url:
            return jsonify({
                'avatarUrl': None,
                'cached': False,
                'available': False,
                'code': 'avatar_not_configured',
                'request_id': request_id,
            }), 200

        # Validate even when a local cache exists so a caller cannot use the
        # endpoint as an SSRF oracle by swapping the URL on a cached user.
        _validate_avatar_url(str(avatar_url))

        # Prepare destination directory
        public_dir = AVATAR_DIRECTORY
        public_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{int(user_id)}.png"
        dest = (public_dir / filename).resolve()
        if dest.parent != public_dir.resolve():
            raise AvatarFetchError('invalid_destination')

        if dest.exists():
            # Update DB reference to local avatar path as well
            try:
                run_async(db_manager.set_opponent_avatar_local(int(user_id), f"players/{filename}"))
            except Exception:
                pass
            return jsonify({
                'avatarUrl': f"/avatars/players/{filename}",
                'cached': True,
                'available': True,
                'code': 'avatar_available',
                'request_id': request_id,
            })

        # Download and validate the complete body before creating the file.
        avatar_bytes = _fetch_avatar_bytes(str(avatar_url))
        _write_avatar_atomically(avatar_bytes, dest)
        # Persist DB mapping to avatar_local for this user
        try:
            run_async(db_manager.set_opponent_avatar_local(int(user_id), f"players/{filename}"))
        except Exception:
            pass

        return jsonify({
            'avatarUrl': f"/avatars/players/{filename}",
            'cached': False,
            'available': True,
            'code': 'avatar_available',
            'request_id': request_id,
        })
    except AvatarFetchError as exc:
        request_reasons = {
            'invalid_url',
            'unsupported_url',
            'credentials_in_url',
            'host_not_allowed',
            'invalid_port',
            'private_address',
            'invalid_resolved_address',
        }
        if exc.reason in request_reasons:
            status = 400
            code = 'avatar_request_invalid'
        elif exc.reason in {'invalid_destination', 'local_write_failed'}:
            status = 503
            code = 'avatar_service_unavailable'
        else:
            status = 502
            code = 'avatar_unavailable'
        logger.warning(
            'avatar fetch rejected request_id=%s reason=%s upstream_status=%s',
            request_id,
            exc.reason,
            exc.upstream_status,
        )
        payload = {
            'error': 'Avatar unavailable',
            'code': code,
            'reason': exc.reason,
            'request_id': request_id,
        }
        if exc.upstream_status is not None:
            payload['upstream_status'] = exc.upstream_status
        return jsonify(payload), status
    except (TypeError, ValueError, KeyError):
        logger.warning('avatar request rejected request_id=%s reason=invalid_request', request_id)
        return jsonify({
            'error': 'Avatar unavailable',
            'code': 'avatar_fetch_failed',
            'request_id': request_id,
        }), 400
    except Exception:
        logger.exception('avatar endpoint failed request_id=%s', request_id)
        return jsonify({
            'error': 'Avatar service unavailable',
            'code': 'avatar_fetch_failed',
            'request_id': request_id,
        }), 502
