import pandas as pd

df = pd.read_csv("recipes_50k_trimmed.csv")

df_trimmed = df.iloc[7000:]

df_trimmed.to_csv("recipes_50k_trimmed_2.csv", index=False)