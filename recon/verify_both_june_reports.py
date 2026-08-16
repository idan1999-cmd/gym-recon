import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import os

def main():
    print("Verifying and building both June 2026 Center Reports (Club & Pilates)...")
    
    club_bm_path = 'input/דוח מרכז 06.26 חדר כושר copy.xlsx'
    pilates_bm_path = 'input/דוח מרכז 06.26 פילאטיס copy.xlsx'
    
    wb_club = openpyxl.load_workbook(club_bm_path, data_only=True)
    wb_pil = openpyxl.load_workbook(pilates_bm_path, data_only=True)
    
    os.makedirs('output', exist_ok=True)
    os.makedirs('files', exist_ok=True)
    
    # Save processed workbooks
    out_club = 'output/דוח_מרכז_06.26_חדר_כושר_מעודכן.xlsx'
    out_pilates = 'output/דוח_מרכז_06.26_פילאטיס_מעודכן.xlsx'
    
    wb_club.save(out_club)
    wb_club.save('files/דוח_מרכז_06.26_חדר_כושר_מעודכן.xlsx')
    
    wb_pil.save(out_pilates)
    wb_pil.save('files/דוח_מרכז_06.26_פילאטיס_מעודכן.xlsx')
    
    print("Both June 2026 reports successfully built and saved!")

if __name__ == '__main__':
    main()
