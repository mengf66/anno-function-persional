def main(text: str, limit: int = 3) -> dict:
    return {"accepted": len(text) <= limit, "scores": [len(text), limit]}
