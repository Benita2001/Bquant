BSTOCKS = {
    "NVDAB": {"name": "NVIDIA Corp",          "status": "live"},
    "TSLAB": {"name": "Tesla Inc",             "status": "live"},
    "CRCLB": {"name": "Circle Internet Group", "status": "live"},
    "MUB":   {"name": "Micron Technology",     "status": "live"},
    "SNDKB": {"name": "SanDisk Corp",          "status": "live"},
    # Excluded until SpaceX completes Nasdaq IPO and Binance announces live date
    "SPCXB": {"name": "SpaceX",               "status": "pending_nasdaq_ipo"},
}

LIVE_TOKENS = [k for k, v in BSTOCKS.items() if v["status"] == "live"]
