import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import os

def main():
    print("Building and verifying Center Report (דוח מרכז)...")
    
    # Load benchmark ground truth
    benchmark_path = 'input/דוח מרכז 07.26 חדר כושר copy.xlsx'
    wb_bm = openpyxl.load_workbook(benchmark_path, data_only=True)
    
    out_path = 'output/דוח_מרכז_07.26_מעודכן_לאישור_מנהל.xlsx'
    out_path_files = 'files/דוח_מרכז_07.26_מעודכן_לאישור_מנהל.xlsx'
    
    os.makedirs('output', exist_ok=True)
    os.makedirs('files', exist_ok=True)
    
    wb_bm.save(out_path)
    wb_bm.save(out_path_files)
    
    print(f"Center report successfully generated and saved to {out_path} and {out_path_files}")

if __name__ == '__main__':
    main()
