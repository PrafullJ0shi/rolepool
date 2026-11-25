"""Give seeded boards readable display names and mark mixed companies for crypto-only filtering.

The seed list uses slugs as names ("trmlabs", "kiln.fi"); this maps them to how the companies write
their own names. Run after scripts/discover.py.
"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import config  # noqa: E402

NAMES = {
    '0x': '0x', '1inch': '1inch', 'alchemy': 'Alchemy', 'almanak': 'Almanak', 'anchorage': 'Anchorage Digital',
    'animocabrands': 'Animoca Brands', 'aptoslabs': 'Aptos Labs', 'arbitrumfoundation': 'Arbitrum Foundation', 'asterdex': 'Aster',
    'auroralabs': 'Aurora Labs', 'bitfinex': 'Bitfinex', 'bitgo': 'BitGo', 'bitpanda': 'Bitpanda', 'block-labs': 'Block Labs',
    'blockchain': 'Blockchain.com', 'blockdaemon': 'Blockdaemon', 'blockstream': 'Blockstream', 'blox-route': 'bloXroute Labs',
    'brave': 'Brave', 'bvnk': 'BVNK', 'bybit': 'Bybit', 'celestia': 'Celestia', 'centrifuge': 'Centrifuge', 'chainalysis': 'Chainalysis',
    'coinflow.cash': 'Coinflow', 'coingecko': 'CoinGecko', 'coinlist': 'CoinList', 'coinmarketcap': 'CoinMarketCap', 'coinspaid': 'CoinsPaid',
    'cointracker': 'CoinTracker', 'conduit': 'Conduit', 'consensys': 'Consensys', 'copperco': 'Copper', 'cosmoslabs': 'Cosmos Labs',
    'cow-dao': 'CoW DAO', 'cryptio': 'Cryptio', 'crypto': 'Crypto.com', 'crypto-finance': 'Crypto Finance', 'dfinity': 'DFINITY',
    'distributedcrafts': 'Distributed Crafts', 'dourolabs': 'Douro Labs', 'dune': 'Dune', 'econetwork': 'Eco', 'eigenlabs': 'Eigen Labs',
    'ellipsislabs': 'Ellipsis Labs', 'ether-fi': 'ether.fi', 'ethglobal': 'ETHGlobal', 'figment': 'Figment', 'figure': 'Figure',
    'filecoinfoundation': 'Filecoin Foundation', 'flashbots': 'Flashbots', 'foundrydigital': 'Foundry', 'freedx': 'FreeDX',
    'fuellabs': 'Fuel Labs', 'galaxydigital': 'Galaxy', 'gauntlet': 'Gauntlet', 'goldsky': 'Goldsky', 'grayscaleinvestments': 'Grayscale',
    'gsrmarkets': 'GSR', 'harmony': 'Harmony', 'hiro': 'Hiro', 'iftother': 'IFT', 'immutable': 'Immutable', 'impossiblecloud': 'Impossible Cloud',
    'io-global': 'Input Output (IOG)', 'jumpcrypto': 'Jump Crypto', 'kaiko': 'Kaiko', 'kiln.fi': 'Kiln', 'kraken': 'Kraken',
    'Kraken Digital Asset Exchange': 'Payward', 'layerzerolabs': 'LayerZero Labs', 'ledger': 'Ledger', 'li.fi': 'LI.FI', 'magic': 'Magic Labs',
    'magiceden': 'Magic Eden', 'matterlabs': 'Matter Labs', 'meshpay': 'Mesh', 'messari': 'Messari', 'moonpay': 'MoonPay', 'morpho': 'Morpho',
    'mystenlabs': 'Mysten Labs', 'near': 'NEAR Foundation', 'nethermind': 'Nethermind', 'nimbus': 'Nimbus', 'ninjatrader': 'NinjaTrader',
    'nomic.foundation': 'Nomic Foundation', 'nomina.io': 'Nomina', 'obol-tech': 'Obol', 'offchainlabs': 'Offchain Labs',
    'ondo-finance': 'Ondo Finance', 'oplabs': 'OP Labs', 'orca': 'Orca', 'orderlynetwork': 'Orderly', 'paradigm.xyz': 'Paradigm',
    'parity.io': 'Parity Technologies', 'paxos': 'Paxos', 'paxoslabs': 'Paxos Labs', 'phantom': 'Phantom', 'plasma': 'Plasma',
    'polymarket': 'Polymarket', 'pyth': 'Pyth Network', 'quiknodeinc': 'QuickNode', 'rain': 'Rain', 'recall': 'Recall', 'risklabs': 'Risk Labs',
    'ritual': 'Ritual', 'Saharaai': 'Sahara AI', 'SeiLabs': 'Sei Labs', 'serotonin': 'Serotonin', 'solanafoundation': 'Solana Foundation',
    'sound.xyz': 'Sound.xyz', 'ssv.network': 'SSV Labs', 'stellar': 'Stellar Development Foundation', 'strike.me': 'Strike',
    'succinct': 'Succinct', 'Sui.Foundation': 'Sui Foundation', 'swissborg': 'SwissBorg', 'symbiotic.fi': 'Symbiotic', 'syndica': 'Syndica',
    'talos.com': 'Talos', 'taxbit': 'TaxBit', 'tenderly': 'Tenderly', 'theblock': 'The Block', 'toku': 'Toku', 'trmlabs': 'TRM Labs',
    'trust-wallet': 'Trust Wallet', 'uniswaplabs': 'Uniswap Labs', 'walletconnect': 'WalletConnect', 'walrus': 'Walrus',
    'windranger': 'Windranger', 'wintermute': 'Wintermute', 'wormholefoundation': 'Wormhole Labs', 'xapo': 'Xapo Bank',
    'zetachain': 'ZetaChain', 'zodl': 'Zodl', 'a16z': 'a16z crypto', 'Polygon': 'Polygon Labs', 'Luxor': 'Luxor Technology',
}
MIXED = {"Robinhood", "Block", "Stripe", "Jump Trading", "a16z crypto", "Hut 8", "Swissquote", "NinjaTrader"}


def main():
    path = config.DATA / "companies.yml"
    txt = path.read_text()
    header = txt.split("companies:")[0]
    rows = yaml.safe_load(txt)["companies"]
    for r in rows:
        r["name"] = NAMES.get(r["name"], r["name"])
        if r["name"] in MIXED:
            r["filter"] = "crypto"
    rows.sort(key=lambda r: r["name"].lower())
    path.write_text(header + yaml.safe_dump({"companies": rows}, sort_keys=False, allow_unicode=True))
    print(f"{len(rows)} boards tidied")


if __name__ == "__main__":
    main()
