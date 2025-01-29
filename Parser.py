import sys
import os
import pdfplumber
import json

from configobj import ConfigObj
from dotenv import load_dotenv
from openai import OpenAI

# Initialize from config and environment variables
if len(sys.argv) < 2:
    print('Please pass an argument to a config file. See README on Github for further information.')
    exit
configFile = sys.argv[1]

outputFile = None
if len(sys.argv) == 3:
    outputFile = sys.argv[2]

load_dotenv()
api_key=os.getenv('API_KEY')

if len(api_key) == 0:
    print('An OpenAPI Key for gpt-4o-mini is required. See README on Github for further information.')
    exit

client = OpenAI(
    api_key=api_key
)

# Initialize default configuration
DEFAULT_INVESTMENT_PAGE_TARGET = "scheduleofinvestments"
DEFAULT_INVESTMENT_CONTINUE_PAGE_TARGET = "(continued)"
DEFAULT_COLCOUNT = 1

def extractPageHeader(page):
    return page.crop((0, 0, page.width, headerHeight)).extract_text(layout=True) + "\n"

def extractPageFooter(page):
    return page.crop((0, footerHeight, page.width, page.height)).extract_text(layout=True) + "\n"

def extractPageBody(page):
    reportText = ""
    for column in range(columCount):
        croppedPage = page.crop((segmentSize * column * float(page.width), headerHeight, segmentSize * (column + 1) * float(page.width), footerHeight))
        reportText += croppedPage.extract_text(layout=True) + "\n"
    return reportText

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

columCount = config.get('DOC_COLCOUNT')
columCount = int(columCount) if columCount and columCount.isdigit() else DEFAULT_COLCOUNT 
segmentSize = 1 / columCount

investmentPageTarget = config.get('INVESTMENT_PAGE_TARGET') or DEFAULT_INVESTMENT_PAGE_TARGET
investmentContinuePageTarget = config.get('INVESTMENT_CONTINUE_PAGE_TARGET') or DEFAULT_INVESTMENT_CONTINUE_PAGE_TARGET

pdf = pdfplumber.open(pdfDoc)

# Get full report text
reportText = ""
for page in pdf.pages:
    reportText += page.extract_text() + "\n"

# Determine pages that are schedule of investments, or are continued schedule of investments
investmentPages = []
processedReport = reportText

# Reduce pages to pages marked as Schedule of Investment or other important keywords in the header
# To prevent file inconsistencies, remove all whitespace and compare as lowercase
for page in pdf.pages:
    pageHeaderText = extractPageHeader(page)
    processedPageText = pageHeaderText.replace(" ", "").lower()

    isContinued = False
    if investmentContinuePageTarget in processedPageText:
        isContinued = True

    if investmentPageTarget in processedPageText:
        investmentPages.append((pageHeaderText + extractPageBody(page) + extractPageFooter(page), isContinued)) 

# Loop through funds, extracting key datapoints
scheduleOfInvestmentsList = [] # An array of funds found within this document

for index, scheduleOfInvestment in enumerate(investmentPages):
    response = client.chat.completions.create(
        messages=[
            { "role": "system", "content": "You are parsing the Schedule of Investments document of a mutual fund." },
            { "role": "assistant", "content": '''
                Extract the Fund Name and the Report Date in ISO format. 
                Extract a list of each holding item within the schedule of investments. Each holding item should contain the following values:
                    Security Name, Security Type, Sector, Country, Number of Shares, Principle Amount, Market Value.
                    If a value is not present, they should be returned as null.
            ''' },
            { "role": "assistant", "content": 
            '''Response must be RFC8259 compliant valid JSON. FORMAT:
                { 
                    "Fund Name": Fund Name, 
                    "Report Date": Report Date,
                    "Schedule of Investments": [
                        {
                            "Security Name": Security Name,
                            "Security Type": Security Type,
                            "Sector": Business Sector or Type of Business,
                            "Country": Country,
                            "Number of Shares": Number of Shares,
                            "Principle":  Principal Amount,
                            "Market Value": Market Value
                        },
                    ]
                }''' 
            },
            { "role": "assistant", "content": '''EXAMPLE: 
                { 
                    "Fund Name": The Hartford Balanced Income Fund, 
                    "Report Date": April 30, 2023,
                    "Schedule of Investments": [
                        {
                            "Security Name": "JetBlue Airways Corp",
                            "Security Type": "Convertible Bonds",
                            "Sector": Airlines,
                            "Country": Canada,
                            "Number of Shares": 12345,
                            "Principle":  "$1,499,000",
                            "Market Value": "$1,167,870"
                        },
                        {
                            "Security Name": "Block, inc.",
                            "Sector": null,
                            "Country": null,
                            "Number of Shares": null,
                            "Principle":  "$1,499,000",
                            "Market Value": "$1,167,870"
                        }
                    ]
                }'''
            },
            { "role": "user", "content": scheduleOfInvestment[2] },
        ],
        model="gpt-4o-mini",
        response_format = { "type": "json_object" }
    )

    jsonResponse = response.choices[0].message.content
    responseDict = json.loads(jsonResponse)

    if investmentPages[index][1]: # This is a continued page - Fold it into the last object
        parentDict = scheduleOfInvestmentsList[len(scheduleOfInvestmentsList) - 1] 

        # Fold the original dict into the updated dict to prevent overwrites
        responseDict.update(parentDict)
        scheduleOfInvestmentsList[len(scheduleOfInvestmentsList) - 1] = responseDict
    else:
        scheduleOfInvestmentsList.append(responseDict)

# Output result to file or console
completeJson = json.dumps({ "funds": scheduleOfInvestmentsList })

if outputFile:
    f = open(outputFile, "w")
    f.write(json.dumps(completeJson))
    f.close()
else:
    print(completeJson)

