from helpers.interfaces import Network, NetworkRole

# Networks

MAINNET = Network(
    technology="ethereum",
    blockchain="ethereum",
    network="mainnet",
    role=NetworkRole.MAINNET,
    title="Ethereum Mainnet",
    currency=None,
)
