import pandas as pd
from paisa_agent.config import Settings
from paisa_agent.optimizer import allocate_capital

candidates = pd.DataFrame({
    "ticker": ["AAA", "BBB", "CCC", "DDD", "EEE"],
    "score": [80, 70, 60, 50, 40],
    "price": [10.0, 5.0, 2.5, 1.0, 0.5]
})
settings = Settings()
allocation = allocate_capital(candidates, settings)
print(allocation)
