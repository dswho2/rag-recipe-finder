import pandas as pd

# Load the full cleaned CSV
df = pd.read_csv("recipes_cleaned.csv")

# Take just the top 200,000 rows
subset = df.head(200_000)

# Save to a new file
subset.to_csv("recipes_200k.csv", index=False)

print("Saved top 200,000 recipes to recipes_200k.csv")
