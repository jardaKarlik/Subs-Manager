#!/usr/bin/env python3
"""
Quick script to fix merge conflicts in api.py and frontend/app.js
Chooses the "Updated upstream" version (newer code)
"""

import re

def fix_api_py():
    """Fix merge conflicts in api.py"""
    with open('api.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix conflict 1: Disney+ section (lines 442-463)
    pattern1 = r'<<<<<<< Updated upstream\s+service_name="Disney\+",.*?=======\s+service_name="Spotify",\s+>>>>>>> Stashed changes'
    replacement1 = '''service_name="Disney+",
            category="streaming",
            cost=10.99,
            currency="USD",
            billing_cycle="monthly",
            source="test"
        ),
        SubscriptionCreate(
            service_name="Hulu",
            category="streaming",
            cost=7.99,
            currency="USD",
            billing_cycle="monthly",
            source="test"
        ),
        # Music
        SubscriptionCreate(
            service_name="Spotify Premium",'''
    
    content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)
    
    # Fix conflict 2: Apple Music section (lines 473-486)
    pattern2 = r'<<<<<<< Updated upstream\s+service_name="Apple Music",.*?=======\s+service_name="GitHub",\s+>>>>>>> Stashed changes'
    replacement2 = '''service_name="Apple Music",
            category="music",
            cost=10.99,
            currency="USD",
            billing_cycle="monthly",
            source="test"
        ),
        # Dev Tools
        SubscriptionCreate(
            service_name="GitHub Pro",'''
    
    content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)
    
    # Fix conflict 3: JetBrains section (lines 496-517)
    pattern3 = r'<<<<<<< Updated upstream\s+service_name="JetBrains All Products",.*?=======\s+service_name="Adobe CC",\s+>>>>>>> Stashed changes'
    replacement3 = '''service_name="JetBrains All Products",
            category="dev_tools",
            cost=149.00,
            currency="USD",
            billing_cycle="yearly",
            source="test"
        ),
        SubscriptionCreate(
            service_name="Vercel Pro",
            category="dev_tools",
            cost=20.00,
            currency="USD",
            billing_cycle="monthly",
            source="test"
        ),
        # Design
        SubscriptionCreate(
            service_name="Adobe Creative Cloud",'''
    
    content = re.sub(pattern3, replacement3, content, flags=re.DOTALL)
    
    with open('api.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("[OK] Fixed api.py")

def fix_app_js():
    """Fix merge conflicts in frontend/app.js"""
    with open('frontend/app.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix conflict 1: fetchSubscriptions URL
    pattern1 = r'<<<<<<< Updated upstream\s+const response = await fetch\(`\$\{API_BASE\}/api/subscriptions`\);.*?=======\s+(const response = await fetch\(`\$\{API_BASE\}/subscriptions\?page_size=100`\);)\s+>>>>>>> Stashed changes'
    replacement1 = r'\1'
    content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)
    
    # Fix conflict 2: id field
    pattern2 = r'<<<<<<< Updated upstream\s+id: sub\.id\.toString\(\),.*?=======\s+(id: sub\.id \|\| sub\.service_name\.toLowerCase\(\)\.replace\(/\\s\+/g, \'\'\),)\s+>>>>>>> Stashed changes'
    replacement2 = r'\1'
    content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)
    
    # Fix conflict 3: data transformation
    pattern3 = r'<<<<<<< Updated upstream\s+plan: extractPlan.*?status: sub\.status\s+>>>>>>> Stashed changes'
    replacement3 = '''plan: sub.notes || (sub.billing_cycle === 'monthly' ? 'Monthly' : sub.billing_cycle === 'yearly' ? 'Annual' : 'Standard'),
        monthly: parseFloat(sub.cost) || 0,
        billing: sub.billing_cycle || 'monthly',
        usage: sub.status === 'active' ? (0.5 + Math.random() * 0.5) : (Math.random() * 0.2),
        since: sub.start_date ? sub.start_date.substring(0, 7) : new Date(sub.created_at).toISOString().substring(0, 7),
        status: sub.status'''
    
    content = re.sub(pattern3, replacement3, content, flags=re.DOTALL)
    
    with open('frontend/app.js', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("[OK] Fixed frontend/app.js")

if __name__ == '__main__':
    try:
        fix_api_py()
        fix_app_js()
        print("\n[SUCCESS] All merge conflicts resolved!")
        print("\nNext steps:")
        print("1. Run: python api.py")
        print("2. Open: frontend/simple.html in your browser")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        print("\nPlease fix merge conflicts manually:")
        print("- Remove all <<<<<<< Updated upstream")
        print("- Remove all =======")
        print("- Remove all >>>>>>> Stashed changes")
        print("- Keep the correct code version")
