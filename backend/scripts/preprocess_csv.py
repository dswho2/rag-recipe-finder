import pandas as pd
import ast
import re

INPUT_FILE = "recipes.csv"
OUTPUT_FILE = "recipes_cleaned.csv"

# === Constants ===
BRAND_KEYWORDS = ['velveeta', 'philadelphia', 'kraft', 'betty crocker', 'pillsbury', 'hershey', 'oreo', 'king sooper', 'jello']
INSTRUCTION_NOISE_PHRASES = [
    'dinner kit', 'cheese pouch', 'product', 'microwave on high', 'package instructions',
    'packet', 'pouch', 'meal kit', 'follow kit instructions', 'boxed meal'
]
DISALLOWED_INGREDIENT_PATTERNS = re.compile(r"\\$|%|pkg\\.|oz\\.|king sooper|for \\$|less fat", re.IGNORECASE)

# === Clean line terminators ===
def clean_text_columns(df):
    for col in df.select_dtypes(include='object'):
        df[col] = (
            df[col]
            .astype(str)
            .str.replace('\u2028', ' ', regex=False)
            .str.replace('\u2029', ' ', regex=False)
            .str.replace('\r\n', '\n', regex=False)
            .str.replace('\r', '\n', regex=False)
        )
    return df

# === Filters ===
def is_valid_title(title: str) -> bool:
    if pd.isna(title):
        return False
    title = title.strip()
    if not (3 <= len(title) <= 30):
        return False
    if not title[0].isalpha():
        return False
    if re.search(r"[\"'*()\[\]{}]|[^a-zA-Z0-9\s\-]", title):
        return False
    if any(brand in title.lower() for brand in BRAND_KEYWORDS):
        return False
    return True

def parse_list_column(col_val: str):
    try:
        val = ast.literal_eval(col_val)
        if isinstance(val, list):
            return val
    except:
        pass
    return []

def is_valid_ingredients(ingredients_str: str) -> bool:
    ingredients = parse_list_column(ingredients_str)
    if not (3 <= len(ingredients) <= 25):
        return False

    for ing in ingredients:
        if not isinstance(ing, str):
            return False
        ing_clean = ing.strip().lower()
        if len(ing_clean.split()) < 2 or len(ing_clean.split()) > 12:
            return False
        if any(brand in ing_clean for brand in BRAND_KEYWORDS):
            return False
        if DISALLOWED_INGREDIENT_PATTERNS.search(ing_clean):
            return False

    return True

def is_valid_directions(directions_str: str) -> bool:
    directions = parse_list_column(directions_str)
    if len(directions) < 2:
        return False
    if any(len(step.strip()) < 10 for step in directions):
        return False
    if sum(len(step.strip()) for step in directions) < 250:
        return False
    if any(phrase in step.lower() for step in directions for phrase in INSTRUCTION_NOISE_PHRASES):
        return False
    return True

# === Run script ===
df = pd.read_csv(INPUT_FILE)
df = clean_text_columns(df)

initial_count = len(df)

filtered_df = df[
    df['title'].apply(is_valid_title) &
    df['ingredients'].apply(is_valid_ingredients) &
    df['directions'].apply(is_valid_directions)
]

final_count = len(filtered_df)
dropped = initial_count - final_count

filtered_df.to_csv(OUTPUT_FILE, index=False)

print(f"Cleaned recipes saved to '{OUTPUT_FILE}'")
print(f"Kept {final_count:,} recipes. Dropped {dropped:,} bad entries.")
