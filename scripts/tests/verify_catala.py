
import sys
import os

# Add engines/catala to path to import the generated module
sys.path.append(os.path.join(os.getcwd(), 'engines', 'catala'))

try:
    import lisr_catala
    print(f"Successfully imported lisr_catala: {lisr_catala}")
    
    # Check if expected classes exist
    if hasattr(lisr_catala, 'Person') and hasattr(lisr_catala, 'PhysicalPersonTax'):
        print("Expected scopes found in generated module.")
    else:
        print("WARNING: Expected scopes (Person, PhysicalPersonTax) NOT found.")
        print(dir(lisr_catala))
        
except ImportError as e:
    print(f"Failed to import lisr_catala: {e}")
    sys.exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit(1)
