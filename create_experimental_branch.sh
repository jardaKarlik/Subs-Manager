#!/bin/bash

# Create experimental branch for local testing
cd C:\_dev\subscription_manager

echo "🌿 Creating experimental branch..."

# Create and switch to experimental branch
git checkout -b experimental/local-db-output

echo "✅ Branch created: experimental/local-db-output"
echo ""
echo "📝 Branch purpose:"
echo "   - Test email parsing with local SQLite database"
echo "   - Output all fetched data to local files"
echo "   - Lower confidence threshold for more matches"
echo "   - Run multiple times without affecting Railway"
echo ""
echo "📂 Changes on this branch:"
echo "   - email_fetcher_fixed.py (sequential batches)"
echo "   - email_parser_enhanced.py (lower threshold, full body)"
echo "   - test_local_with_fixes.py (test runner)"
echo ""
echo "🎯 To run experiment:"
echo "   python test_local_with_fixes.py"
echo ""
echo "🔄 To go back to main:"
echo "   git checkout main"
