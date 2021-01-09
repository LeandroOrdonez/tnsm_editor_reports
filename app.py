import streamlit as st
import numpy as np
import pandas as pd
import json
from matplotlib import pyplot as plt
import seaborn as sns
import datetime

FIELDS_PATH = './fields.json'
PENDING_STATUS_PATH = './pending_status.json'
EDITORS_PATH = './editors.json'

with open(FIELDS_PATH, 'r') as fields_file:
    COLUMNS = json.load(fields_file)

with open(PENDING_STATUS_PATH, 'r') as pstatus_file:
    PENDING_STATUS = json.load(pstatus_file)

with open(EDITORS_PATH, 'r') as editors_file:
    EDITORS = json.load(editors_file)

REPORT_FILE = st.sidebar.file_uploader("Upload TNSM report spreadsheet")
EDITOR = st.sidebar.selectbox('Select an Associate Editor...', EDITORS)

def is_pending(r):
    if pd.notnull(r['Manuscript Status']):
        return r['Manuscript Status'] in PENDING_STATUS

def filter_submitted_per_year(year, count_type='total'):
    if count_type == 'total':
        return report_df[report_df['Submission Year'] == year].copy()
    elif count_type == 'original':
        return report_df[(report_df['Submission Year'] == year) & (report_df['Revised'] == False)].copy()
    else:
        return report_df[(report_df['Submission Year'] == year) & (report_df['Revised'] == True)].copy()

def filter_submitted_per_date_range(from_date, to_date):
    return report_df[(report_df['Original Submission Date'] >= from_date) & (report_df['Original Submission Date'] <= to_date)].copy() 

def filter_per_editor_and_year(editor, year, count_type='total'):
    if count_type == 'original':
        return report_df[
                ((report_df['First Decision Year'] >= year)
                & (report_df['Editor Names'] == editor)
                & (report_df['Revised'] == False)
                & (report_df['Pending'] == False)) 
                |
                ((report_df['First Decision Year'] >= year)
                & (report_df['Editor Names'] == editor)
                & (report_df['Revised'] == True))
            ].copy()
    elif count_type == 'revised':
        return report_df[
                ((report_df['First Decision Year'] >= year)
                & (report_df['Latest Decision'].isnull())
                & (report_df['Editor Names'] == editor)
                & (report_df['Revised'] == True)) 
                |
                ((report_df['Latest Decision Year'] >= year)
                & (report_df['Editor Names'] == editor)
                & (report_df['Revised'] == True)
                & (report_df['Pending'] == False))
            ].copy()
    elif count_type == 'pending':
        return report_df[
                ((report_df['Submission Year'] >= year)
                & (report_df['Editor Names'] == editor)
                & (report_df['Pending'] == True)) 
                |
                ((report_df['Submission Year'] < year)
                & (report_df['Latest Decision Year'] >= year)
                & (report_df['Editor Names'] == editor)
                & (report_df['Pending'] == True))
            ].copy()
    else:
        return report_df[
                ((report_df['First Decision Year'] >= year)
                & (report_df['Editor Names'] == editor)
                & (report_df['Revised'] == False)
                & (report_df['Pending'] == False)) 
                |
                ((report_df['First Decision Year'] >= year)
                & (report_df['Editor Names'] == editor)
                & (report_df['Revised'] == True))
                |
                ((report_df['First Decision Year'] < year)
                & (report_df['Latest Decision Year'] >= year)
                & (report_df['Editor Names'] == editor)
                & (report_df['Revised'] == True)
                & (report_df['Pending'] == False))
            ].copy()

def count_per_editor_and_year(editor, year, count_type='total'):
    return filter_per_editor_and_year(editor, year, count_type).shape[0]

def get_max_days_per_editor(editor, year, type='original'):
    df = filter_per_editor_and_year(editor, year, type)
    return df["# Days Since Latest Submission"].max() if type == 'pending' else df["# Days Between Original Submission & Original Decision"].max()

def get_min_days_per_editor(editor, year, type='original'):
    df = filter_per_editor_and_year(editor, year, type)
    return df["# Days Since Latest Submission"].min() if type == 'pending' else  df["# Days Between Original Submission & Original Decision"].min()

def get_avg_days_per_editor(editor, year, type='original'):
    df = filter_per_editor_and_year(editor, year, type)
    return round(df["# Days Since Latest Submission"].mean(), 1) if type == 'pending' else round(df["# Days Between Original Submission & Original Decision"].mean(), 1)

def get_formatted_report_line(editor, year, type='original'):
    count = count_per_editor_and_year(editor, year, type)
    return f"""
{type.capitalize()} manuscript(s) handled in {year}: {count}
- Time to handle (in days): {get_avg_days_per_editor(editor, year, type)} in average, maximum of {get_max_days_per_editor(editor, year, type)}, minimum of {get_min_days_per_editor(editor, year, type)}
    """ if count > 0 else f"""
{type.capitalize()} manuscript(s) handled in {year}: {count}
    """

def get_list_pending_papers(editor, year):
    df = filter_per_editor_and_year(editor, year, 'pending')
    if df.empty:
        return ""
    else:
        lines = []
        for index, row in df.iterrows():
            lines.append(f"  - '{row['Manuscript Title']}', {row['Manuscript ID - Latest']}, in review for {row['# Days Since Latest Submission']} day(s) with status '{row['Manuscript Status']}'")
        concat_lines = '\n'.join(lines)
        return f"""
- List of pending manuscripts:
{concat_lines}
        """

st.title('IEEE TNSM Editor Performance Reports')

if REPORT_FILE is None:
    st.markdown('No info available yet (*Use the file upload input in the sidebar*)')
    formatted_cols = '\n'.join([f'* {col}' for col in COLUMNS])
    st.text(f"""Be sure to include the following fields when exporting the report:

{formatted_cols}""")
else:
    report_df = pd.read_excel(REPORT_FILE, engine='openpyxl')
    # test if the required columns are present in the provide report
    # assert  set(COLUMNS).issubset(set(report_df.columns))

    # st.header('Data Preview')
    # st.dataframe(report_df.head(5))
    
    report_df['Submission Year'] = pd.DatetimeIndex(report_df['Original Submission Date']).year
    report_df['First Decision Month Number'] = pd.DatetimeIndex(report_df['First Decision Date']).month
    report_df['First Decision Year'] = pd.DatetimeIndex(report_df['First Decision Date']).year
    report_df['Latest Decision Month Number'] = pd.DatetimeIndex(report_df['Latest Decision Date']).month
    report_df['Latest Decision Year'] = pd.DatetimeIndex(report_df['Latest Decision Date']).year
    report_df['Revised'] = report_df.apply(lambda r: '.R' in r['Manuscript ID - Latest'] if type(r['Manuscript ID - Latest']) != float else np.nan , axis=1)
    report_df['Pending'] = report_df.apply(is_pending, axis=1)

    report_df['# Days Since Original Submission'] = pd.DataFrame(report_df['# Days Since Original Submission'].str.split(' ',1).tolist(),
                                columns = ['Days Since Original Submission','rest'])['Days Since Original Submission'].astype(int)
    report_df['# Days Since Latest Submission'] = pd.DataFrame(report_df['# Days Since Latest Submission'].fillna('-1').str.split(' ',1).tolist(),
                                columns = ['Days Since Latest Submission','rest'])['Days Since Latest Submission'].astype(int)

    REPORT_YEAR = report_df['Original Submission Date'].max().year - 1

    # st.header(f'{REPORT_YEAR} Performance Report - {EDITOR}')
    st.text(f"""
{REPORT_YEAR} Performance Report - {EDITOR}
Manuscript(s) handled in {REPORT_YEAR}: {count_per_editor_and_year(EDITOR, REPORT_YEAR)}
{get_formatted_report_line(EDITOR, REPORT_YEAR, 'original')}
{get_formatted_report_line(EDITOR, REPORT_YEAR, 'revised')}
{get_formatted_report_line(EDITOR, REPORT_YEAR, 'pending')}
{get_list_pending_papers(EDITOR, REPORT_YEAR)}
""")
