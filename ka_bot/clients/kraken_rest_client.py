# ==============================================================================
# File: kraken_rest_client.py
# UPDATED: Added a method for public GET requests.
# ==============================================================================
import time, hmac, hashlib, base64, urllib.parse, aiohttp


class KrakenRestClient:
    def __init__(self, config):
        self._config, self.api_key, self.private_key, self.base_url = config, config.KRAKEN_API_KEY, config.KRAKEN_PRIVATE_KEY, config.KRAKEN_REST_URL
        print("Trader Initialized (KrakenRestClient).")

    def _get_kraken_signature(self, urlpath, data):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(self.private_key), message, hashlib.sha512)
        return base64.b64encode(mac.digest()).decode()

    async def _private_request(self, uri_path, data=None):
        data = data or {}
        data['nonce'] = str(int(time.time() * 1000))
        headers = {'API-Key': self.api_key, 'API-Sign': self._get_kraken_signature(uri_path, data)}
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url + uri_path, headers=headers, data=data) as resp:
                result = await resp.json()
                if result.get('error'): print(f"API Error: {result['error']}"); return None
                return result.get('result')

    async def _public_request(self, uri_path, data=None):
        url = self.base_url + uri_path
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=data) as resp:
                result = await resp.json()
                if result.get('error'): return None
                return result.get('result')

    async def get_tradable_asset_pairs(self):
        return await self._public_request('/0/public/AssetPairs')

    async def get_balance(self):
        print("Fetching account balance...")
        return await self._private_request('/0/private/Balance')

    async def place_order(self, pair, order_type, side, volume, **kwargs):
        print(f"PLACING ORDER: {side} {volume} of {pair}...")
        return await self._private_request('/0/private/AddOrder',
                                           {'pair': pair, 'type': side, 'ordertype': order_type, 'volume': str(volume)})
