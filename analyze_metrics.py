import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Load the data
df = pd.read_csv("track_metrics.csv")

# Print basic summary
print("=== Data Summary ===")
print(df.describe())
print("\n=== Top 5 entries ===")
print(df.head())

# Sort by efficiency and purity
top_eff = df.sort_values("efficiency", ascending=False).head(5)
top_pur = df.sort_values("purity", ascending=False).head(5)

print("\n=== Top by Efficiency ===")
print(top_eff)

print("\n=== Top by Purity ===")
print(top_pur)

# Optional: Combine efficiency and purity using harmonic mean or average
df["score"] = 2 * (df["efficiency"] * df["purity"]) / (df["efficiency"] + df["purity"])
top_score = df.sort_values("score", ascending=False).head(5)

print("\n=== Top by Combined Score ===")
print(top_score)

# Plot efficiency vs purity
plt.figure(figsize=(8, 6))
sns.scatterplot(data=df, x="efficiency", y="purity", hue="finalstate", palette="Set2")
plt.title("Tracking Efficiency vs Purity")
plt.xlabel("Efficiency")
plt.ylabel("Purity")
plt.grid(True)
plt.tight_layout()
plt.savefig("efficiency_vs_purity.png")

# Optional: pairplot to see relationships between all params
sns.pairplot(df, vars=df.columns[:-2], hue="finalstate")
plt.suptitle("Parameter Pairwise Relationships", y=1.02)
plt.tight_layout()
plt.savefig("param_pairplot.png")
