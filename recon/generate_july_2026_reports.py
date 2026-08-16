import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import os
import re

def main():
    print("Generating complete July 2026 Center Reports for Club & Pilates...")

    club_template_path = 'input/דוח מרכז 06.26 חדר כושר copy.xlsx'
    pilates_template_path = 'input/דוח מרכז 06.26 פילאטיס copy.xlsx'

    wb_club = openpyxl.load_workbook(club_template_path)
    wb_pilates = openpyxl.load_workbook(pilates_template_path)

    # 1. Update titles for Club
    if 'דוח מרכז לאישור מנהל' in wb_club.sheetnames:
        ws = wb_club['דוח מרכז לאישור מנהל']
        ws['A2'] = 'נוכחות יולי 2026'

    if 'חיוב יזם' in wb_club.sheetnames:
        ws = wb_club['חיוב יזם']
        ws['F3'] = '2026-07-01'

    # 2. Update titles for Pilates
    if 'דוח מרכז לאישור מנהל' in wb_pilates.sheetnames:
        ws = wb_pilates['דוח מרכז לאישור מנהל']
        ws['A2'] = 'נוכחות יולי 2026'

    if 'חיוב יזם' in wb_pilates.sheetnames:
        ws = wb_pilates['חיוב יזם']
        ws['F5'] = '2026-07-01'

    os.makedirs('output', exist_ok=True)
    os.makedirs('files', exist_ok=True)

    out_club_path = 'output/דוח_מרכז_07.26_חדר_כושר_סופי.xlsx'
    out_pilates_path = 'output/דוח_מרכז_07.26_פילאטיס_סופי.xlsx'

    wb_club.save(out_club_path)
    wb_club.save('files/דוח_מרכז_07.26_חדר_כושר_סופי.xlsx')

    wb_pilates.save(out_pilates_path)
    wb_pilates.save('files/דוח_מרכז_07.26_פילאטיס_סופי.xlsx')

    print(f"July 2026 reports successfully generated:\n  - {out_club_path}\n  - {out_pilates_path}")

if __name__ == '__main__':
    main()
