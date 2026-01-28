#!/usr/bin/env python
"""Quick script to check fuzzy matching similarity scores."""

from fuzzywuzzy import fuzz
import re

def normalize(name):
    """Normalize name for comparison."""
    normalized = name.casefold().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    # Remove articles
    normalized = re.sub(r"^the\s+", "", normalized)
    normalized = re.sub(r"^a\s+", "", normalized)
    normalized = re.sub(r"^an\s+", "", normalized)
    return normalized

# Test case 1: Oriam names
n1 = "Oriam Scotland"
n2 = "ORIAM - Scotland's Sports Performance Centre"
norm1 = normalize(n1)
norm2 = normalize(n2)
score1 = fuzz.token_set_ratio(norm1, norm2)

print(f"Test 1: Oriam")
print(f"  Name 1: '{n1}' → normalized: '{norm1}'")
print(f"  Name 2: '{n2}' → normalized: '{norm2}'")
print(f"  Score: {score1} (threshold: 85)")
print(f"  Match: {score1 >= 85}\n")

# Test case 2: Craiglockhart names
names = [
    "Edinburgh Leisure Craiglockhart",
    "Craiglockhart Sports Centre - Edinburgh Leisure",
    "Craiglockhart Sports Centre"
]

print("Test 2: Craiglockhart")
for i, name1 in enumerate(names):
    for j, name2 in enumerate(names):
        if i >= j:
            continue
        norm1 = normalize(name1)
        norm2 = normalize(name2)
        score = fuzz.token_set_ratio(norm1, norm2)
        print(f"  '{name1}' vs '{name2}'")
        print(f"    Normalized: '{norm1}' vs '{norm2}'")
        print(f"    Score: {score} (match: {score >= 85})")
