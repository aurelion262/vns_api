from vnstock_data.explorer.kbs.company import Company
from vnstock_data.explorer.kbs.listing import Listing

def test_kbs():
    print("Testing Company...")
    c = Company('TCB')
    print("Overview:", type(c.overview()))
    print("Shareholders:", type(c.shareholders()))
    
    print("\nTesting Listing...")
    l = Listing()
    print("All Symbols:", type(l.all_symbols()))
    print("All Indices:", type(l.all_indices()))
    
if __name__ == '__main__':
    test_kbs()
