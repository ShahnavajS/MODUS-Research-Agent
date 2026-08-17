import ipaddress
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Private and reserved IP networks for SSRF protection
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

BLOCKED_HOSTNAMES = {"localhost", "loopback", "internal", "local", "metadata.google.internal"}


def is_safe_external_url(url: str) -> tuple[bool, str]:
    """
    Validates whether a URL is a safe external HTTP/HTTPS URL.
    Blocks SSRF attempts to internal networks, localhost, file:// schemes, and private IP ranges.
    """
    if not url:
        return False, "URL is empty"

    try:
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            return False, f"Invalid scheme '{scheme}': only HTTP/HTTPS allowed"

        hostname = parsed.hostname
        if not hostname:
            return False, "Missing hostname in URL"

        hostname_clean = hostname.lower().strip()

        # Check hostname blacklists
        if hostname_clean in BLOCKED_HOSTNAMES or hostname_clean.endswith(".local") or hostname_clean.endswith(".internal"):
            return False, f"Blocked internal hostname '{hostname_clean}'"

        # Check IP address targets
        try:
            ip_obj = ipaddress.ip_address(hostname_clean)
            for net in BLOCKED_IP_NETWORKS:
                if ip_obj in net:
                    return False, f"Blocked private/internal IP address '{ip_obj}'"
        except ValueError:
            # Hostname is a domain name, not a literal IP, which is allowed
            pass

        return True, "URL is safe"

    except Exception as e:
        logger.warning(f"URL security check error for '{url}': {e}")
        return False, f"Invalid URL structure: {e}"
