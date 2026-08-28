class ConditionEvaluator:
    def evaluate(self, condition: str) -> bool:
        """
        Evaluates a condition for a deferred task.
        For demo purposes, this uses stubbed data sources.
        """
        if not condition:
            return True # If no specific condition was given, assume it's ready

        condition_lower = condition.lower()

        # Stub: flight prices
        if "flight" in condition_lower or "price" in condition_lower:
            # We'll toggle it based on the presence of certain letters or just randomly.
            # To be deterministic for the demo, we can just say "if 'bangalore' it's true"
            if "bangalore" in condition_lower:
                return True
            return False

        # Stub: weather
        if "weather" in condition_lower or "rain" in condition_lower:
            return False
        return True
