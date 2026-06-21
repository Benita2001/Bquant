import os

from dotenv import load_dotenv

from bnbagent import ERC8004Agent, AgentEndpoint, EVMWalletProvider

load_dotenv()

wallet = EVMWalletProvider(
    password=os.getenv("WALLET_PASSWORD", "bquant-hackathon-2026"),
    private_key=os.getenv("PRIVATE_KEY"),
)

sdk = ERC8004Agent(network="bsc-testnet", wallet_provider=wallet)

agent_uri = sdk.generate_agent_uri(
    name="bquant-weekend-drift",
    description="Detects and signals on the price-discovery gap between bStocks (24/7 on-chain trading) and their closed-market NYSE/Nasdaq reference price across NVDAB, TSLAB, CRCLB, MUB, SNDKB.",
    endpoints=[
        AgentEndpoint(
            name="signal-registry",
            endpoint="https://testnet.bscscan.com/address/0xFFCC472c47cf0a8168545a8318832950f7C6F453",
            version="1.0.0",
        ),
    ],
)

result = sdk.register_agent(agent_uri=agent_uri)

print(f"Agent registered! ID: {result['agentId']}, TX: {result['transactionHash']}")
