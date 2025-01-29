import sys
import pdfplumber
from configobj import ConfigObj
from parser import extractPageBody, extractPageFooter, extractPageHeader, DEFAULT_COLCOUNT, DEFAULT_INVESTMENT_CONTINUE_PAGE_TARGET, DEFAULT_INVESTMENT_PAGE_TARGET

# Initialize from config and environment variables
if len(sys.argv) < 2:
    print('Please pass an argument to a config file. See README on Github for further information.')
    exit
configFile = sys.argv[1]

testPage = 0
if len(sys.argv) > 2:
    testPage = int(sys.argv[2])

# Load data from passed configuration file
config = ConfigObj(configFile)
pdfDoc = config.get('DOC') or ''
if len(pdfDoc) == 0:
    print('A DOC must be referenced in the config file. See README on Github for further information.')
    exit

headerHeight = config.get('DOC_HEADER')
headerHeight = int(headerHeight) if headerHeight and headerHeight.isdigit() else 0 

footerHeight = config.get('DOC_FOOTER')
footerHeight = int(footerHeight) if footerHeight and footerHeight.isdigit() else 0 

columnCount = config.get('DOC_COLCOUNT')
columnCount = int(columnCount) if columnCount and columnCount.isdigit() else DEFAULT_COLCOUNT 
segmentSize = 1 / columnCount

investmentPageTarget = config.get('INVESTMENT_PAGE_TARGET') or DEFAULT_INVESTMENT_PAGE_TARGET
investmentContinuePageTarget = config.get('INVESTMENT_CONTINUE_PAGE_TARGET') or DEFAULT_INVESTMENT_CONTINUE_PAGE_TARGET

print("Opening PDF...")
pdf = pdfplumber.open(pdfDoc)
testPage = pdf.pages[testPage]

if headerHeight > 0:
    pageHeader = extractPageHeader(testPage, headerHeight)
    pageHeader.to_image().save('Header-Test-Image.png')

if footerHeight > 0:
    pageFooter = extractPageFooter(testPage, footerHeight)
    pageFooter.to_image().save('Footer-Test-Image.png')

pageBodySegments = extractPageBody(testPage, headerHeight, footerHeight, columnCount)
for index, column in enumerate(pageBodySegments):
    column.to_image().save(f'{index}-Body-Test-Image.png')

print("Sample segment images created.")