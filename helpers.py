import requests
from bech32 import bech32_decode, convertbits

from .nostr.key import PrivateKey


def parse_nostr_private_key(key: str) -> PrivateKey:
    if key.startswith("nsec"):
        return PrivateKey.from_nsec(key)
    else:
        return PrivateKey(bytes.fromhex(key))

def normalize_public_key(pubkey: str) -> str:
    if pubkey.startswith("npub1"):
        _, decoded_data = bech32_decode(pubkey)
        if not decoded_data:
            raise ValueError("Public Key is not valid npub")

        decoded_data_bits = convertbits(decoded_data, 5, 8, False)
        if not decoded_data_bits:
            raise ValueError("Public Key is not valid npub")
        return bytes(decoded_data_bits).hex()

    # allow for nip05 identifier as well, ex: bob@example.com
    if "@" in pubkey:
        local_part, domain = pubkey.split("@")

        request_url = f"https://{domain}/.well-known/nostr.json?name={local_part}"
        response = requests.get(request_url)
        if response.status_code != 200:
            raise ValueError("Public Key is not valid npub")

        response_json = response.json()
        if not response_json.get("names"):
            raise ValueError("Public Key not found")
        pubkey = response_json["names"].get(local_part)
        if not pubkey:
            raise ValueError("Public Key not found")

    # check if valid hex
    if len(pubkey) != 64:
        raise ValueError("Public Key is not valid hex")
    int(pubkey, 16)
    return pubkey
