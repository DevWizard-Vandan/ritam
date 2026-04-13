from src.reasoning.gemma_client import deep_reason

class AnalogExplainer:
    def explain(self, current_candles: list[dict], analogs: list[dict], regime: str, sentiment_score: float) -> str:
        prompt = f"Current Regime: {regime}\nSentiment Score: {sentiment_score}\nTop Analogs:\n"
        for i, analog in enumerate(analogs[:3]):
            prompt += f"{i+1}. {analog['start_date']} to {analog['end_date']} (Similarity: {analog['similarity_score']}) -> Next 5-day return: {analog['next_5day_return']}%\n"
        prompt += "\nGiven these historical analogs and current conditions, what is the most likely market direction over the next 5 days and why? Reply in 3 sentences max."
        return deep_reason(prompt)
