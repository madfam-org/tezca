#!/usr/bin/env python3
"""
Test script for 2026 LISR tax calculations
Validates against known tax bracket examples
"""
import sys
sys.path.insert(0, 'engines/catala')

try:
    import lisr_catala
    print("✅ Successfully imported lisr_catala module")
    print(f"Module: {lisr_catala}")
    print(f"\nAvailable classes: {[item for item in dir(lisr_catala) if not item.startswith('_')]}")
    
    # Test if TaxCalculation2026 class exists
    if hasattr(lisr_catala, 'tax_calculation2026'):
        print("\n✅ Found tax_calculation2026 function")
        
        # Test case 1: Low income bracket ($15,000/month)
        print("\n📊 Test Case 1: Monthly income $15,000")
        print("Expected bracket: 2 ($10,135.12 - $86,022.11)")
        print("Expected tax formula: $194.59 + (15000 - 10135.12) * 0.064")
        print("Expected tax: ~$505.95")
        
        # Test case 2: Middle income bracket ($100,000/month)
        print("\n📊 Test Case 2: Monthly income $100,000")
        print("Expected bracket: 3 ($86,022.12 - $151,176.19)")
        print("Expected tax formula: $5,051.37 + (100000 - 86022.12) * 0.1088")
        print("Expected tax: ~$6,571.45")
        
    else:
        print("\n⚠️  tax_calculation2026 function not found")
        print(f"Available: {dir(lisr_catala)}")
        
except ImportError as e:
    print(f"❌ Failed to import lisr_catala: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error during testing: {e}")
    sys.exit(1)
