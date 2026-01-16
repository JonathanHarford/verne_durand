from jules_agent_sdk.base import BaseClient
import logging

def apply_patch():
    """
    Monkeypatches jules_agent_sdk.base.BaseClient to send the API key
    as a query parameter ('key') instead of (or in addition to) the header.

    This fixes the issue where the API rejects the request with 'API keys are not supported'
    when the key is only in the X-Goog-Api-Key header.
    """
    # Check if already patched to avoid recursion/double patching
    if getattr(BaseClient, "_is_patched_for_api_key", False):
        return

    _original_request = BaseClient._request

    def _patched_request(self, method, path, *args, **kwargs):
        params = kwargs.get("params")
        if params is None:
            params = {}

        # Inject API key if not present
        if "key" not in params and self.api_key:
             params["key"] = self.api_key

        kwargs["params"] = params
        return _original_request(self, method, path, *args, **kwargs)

    BaseClient._request = _patched_request
    BaseClient._is_patched_for_api_key = True
    # We use a logger if configured, otherwise print might interfere with script output,
    # but since this is a patch, we probably shouldn't be too noisy.
