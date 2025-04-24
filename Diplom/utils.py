from collections import defaultdict

def analyze_expenses_by_category(transactions):
    """Analyzes expenses by category."""
    expenses = defaultdict(float)
    for transaction in transactions:
        if not transaction.category.is_income:  # Only expenses
            expenses[transaction.category.name] += float(transaction.amount)
    return expenses
