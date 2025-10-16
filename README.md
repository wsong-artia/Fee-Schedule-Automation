# Fee-Schedule-Automation

The purpose of this project is to improve efficiency of our quarterly fee schedule research by automating the process. Currently Analytics team invests about 100+ hours per quarter to complete research for ~30 HCPCS/CPT codes; we hope to significantly reduce the time spent on research by webscraping as much states' fee schedules as possible.

The automation process follows these steps:
1. Grab files - Webscrape from individual state's fee schedule website -> download .xlsx, .csv, .docx, .xml, or .pdf file
2. Parse saved files - pandas library for Excel files, docx for doc documents, pdf2docx + add'l libraries for .pdfs
3. Extract the necessary info & columns - we need HCPCS/CPT code, fee, last updated date, state, PA required (Y/N)
4. Transform & Load - output the fee file in standard format 
