# Step 5: Create visualizations for rent, earnings, and affordability trends
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

from config import get_postgres_connection

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10

OUTPUT_DIR = Path('../visualizations')
OUTPUT_DIR.mkdir(exist_ok=True)


def get_data():
    conn = get_postgres_connection()
    df = pd.read_sql_query(
        "SELECT * FROM rent_affordability_analysis ORDER BY county, year", conn
    )
    conn.close()
    return df


#Member A: Rent visualisations 

def plot_rent_trends(df, top_n=5):
    """Shows the top N counties with HIGHEST rents - these are the
    counties most affected by the affordability crisis."""
    latest = df['year'].max()
    counties = df[df['year'] == latest].nlargest(top_n, 'avg_monthly_rent')['county'].values

    fig, ax = plt.subplots(figsize=(14, 7))
    for county in counties:
        d = df[df['county'] == county]
        ax.plot(d['year'], d['avg_monthly_rent'], marker='o', linewidth=2, label=county)

    ax.set_xlabel('Year', fontweight='bold')
    ax.set_ylabel('Average Monthly Rent (€)', fontweight='bold')
    ax.set_title(f'Rent Trends: Top {top_n} Highest-Rent Counties',
                 fontsize=14, fontweight='bold')
    ax.legend(title='County', bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'member_A_rent_trends.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: member_A_rent_trends.png")


def plot_rent_distribution(df):
    latest = df['year'].max()
    df_latest = df[df['year'] == latest].sort_values('avg_monthly_rent', ascending=False)

    fig, ax = plt.subplots(figsize=(14, 8))
    bars = ax.barh(df_latest['county'], df_latest['avg_monthly_rent'], color='steelblue')
    for bar in bars:
        w = bar.get_width()
        ax.text(w, bar.get_y() + bar.get_height() / 2,
                f'€{w:.0f}', ha='left', va='center', fontsize=9)

    ax.set_xlabel('Average Monthly Rent (€)', fontweight='bold')
    ax.set_ylabel('County', fontweight='bold')
    ax.set_title(f'Average Monthly Rent by County ({latest})', fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'member_A_rent_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: member_A_rent_distribution.png")


#Member B: Earnings visualisations 

def plot_earnings_trends(df, top_n=5):
    """Shows the top N counties with HIGHEST earnings."""
    latest = df['year'].max()
    counties = df[df['year'] == latest].nlargest(top_n, 'avg_monthly_earnings')['county'].values

    fig, ax = plt.subplots(figsize=(14, 7))
    for county in counties:
        d = df[df['county'] == county]
        ax.plot(d['year'], d['avg_monthly_earnings'], marker='s', linewidth=2, label=county)

    ax.set_xlabel('Year', fontweight='bold')
    ax.set_ylabel('Average Monthly Earnings (€)', fontweight='bold')
    ax.set_title(f'Earnings Trends: Top {top_n} Counties', fontsize=14, fontweight='bold')
    ax.legend(title='County', bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'member_B_earnings_trends.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: member_B_earnings_trends.png")


def plot_earnings_distribution(df):
    latest = df['year'].max()
    df_latest = df[df['year'] == latest].sort_values('avg_monthly_earnings', ascending=False)

    fig, ax = plt.subplots(figsize=(14, 8))
    bars = ax.barh(df_latest['county'], df_latest['avg_monthly_earnings'], color='forestgreen')
    for bar in bars:
        w = bar.get_width()
        ax.text(w, bar.get_y() + bar.get_height() / 2,
                f'€{w:.0f}', ha='left', va='center', fontsize=9)

    ax.set_xlabel('Average Monthly Earnings (€)', fontweight='bold')
    ax.set_ylabel('County', fontweight='bold')
    ax.set_title(f'Average Monthly Earnings by County ({latest})', fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'member_B_earnings_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: member_B_earnings_distribution.png")


#Shared: Affordability visualisations

def plot_affordability_trends(df):
    key_counties = ['Dublin', 'Cork', 'Galway', 'Limerick', 'Waterford']
    df_filtered = df[df['county'].isin(key_counties)]

    fig, ax = plt.subplots(figsize=(14, 7))
    for county in key_counties:
        d = df_filtered[df_filtered['county'] == county]
        ax.plot(d['year'], d['rent_to_income_ratio'], marker='o', linewidth=2.5, label=county)

    ax.axhline(y=30, color='red', linestyle='--', linewidth=2,
               label='Affordable Threshold (30%)', alpha=0.7)
    ax.set_xlabel('Year', fontweight='bold')
    ax.set_ylabel('Rent-to-Income Ratio (%)', fontweight='bold')
    ax.set_title('Rent Affordability Trends: Major Irish Cities', fontsize=14, fontweight='bold')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'shared_affordability_trends.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: shared_affordability_trends.png")


def plot_affordability_heatmap(df):
    pivot = df.pivot(index='county', columns='year', values='rent_to_income_ratio')

    fig, ax = plt.subplots(figsize=(16, 10))
    sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn_r',
                cbar_kws={'label': 'Rent-to-Income Ratio (%)'}, ax=ax)
    ax.set_title('Rent Affordability Heatmap: All Counties', fontsize=14, fontweight='bold')
    ax.set_xlabel('Year', fontweight='bold')
    ax.set_ylabel('County', fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'shared_affordability_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: shared_affordability_heatmap.png")


def plot_rent_vs_earnings_scatter(df):
    latest = df['year'].max()
    df_latest = df[df['year'] == latest]

    fig, ax = plt.subplots(figsize=(12, 8))
    scatter = ax.scatter(
        df_latest['avg_monthly_earnings'], df_latest['avg_monthly_rent'],
        s=200, alpha=0.6, c=df_latest['rent_to_income_ratio'],
        cmap='RdYlGn_r', edgecolors='black', linewidth=1
    )
    for _, row in df_latest.iterrows():
        ax.annotate(row['county'],
                    (row['avg_monthly_earnings'], row['avg_monthly_rent']),
                    xytext=(5, 5), textcoords='offset points', fontsize=8)

    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Rent-to-Income Ratio (%)', fontsize=11)
    ax.set_xlabel('Average Monthly Earnings (€)', fontweight='bold')
    ax.set_ylabel('Average Monthly Rent (€)', fontweight='bold')
    ax.set_title(f'Rent vs Earnings by County ({latest})', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'shared_rent_vs_earnings_scatter.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: shared_rent_vs_earnings_scatter.png")


def plot_affordability_categories(df):
    latest = df['year'].max()
    counts = df[df['year'] == latest]['affordability_category'].value_counts()
    counts = counts.reindex(['Affordable', 'Burdened', 'Severely Burdened']).dropna()
    colors = ['#2ecc71', '#f39c12', '#e74c3c']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    ax1.pie(counts.values, labels=counts.index, autopct='%1.1f%%',
            colors=colors, startangle=90, textprops={'fontsize': 11})
    ax1.set_title(f'Affordability Distribution ({latest})', fontsize=13, fontweight='bold')

    bars = ax2.bar(counts.index, counts.values, color=colors)
    for bar in bars:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, h,
                 str(int(h)), ha='center', va='bottom', fontsize=11)
    ax2.set_ylabel('Number of Counties', fontweight='bold')
    ax2.set_title(f'Counties by Category ({latest})', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'shared_affordability_categories.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved: shared_affordability_categories.png")


if __name__ == "__main__":
    print("Loading data...")
    df = get_data()
    print(f"Loaded {len(df)} records")

    print("\nMember A visualisations:")
    plot_rent_trends(df)
    plot_rent_distribution(df)

    print("\nMember B visualisations:")
    plot_earnings_trends(df)
    plot_earnings_distribution(df)

    print("\nShared visualisations:")
    plot_affordability_trends(df)
    plot_affordability_heatmap(df)
    plot_rent_vs_earnings_scatter(df)
    plot_affordability_categories(df)

    print(f"\nAll done. Files saved to: {OUTPUT_DIR.absolute()}")
