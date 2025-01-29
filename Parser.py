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

    jsonResponse = '{\n    "Fund Name": "BlackRock International Fund",\n    "Report Date": "2024-08-31",\n    "Schedule of Investments": [\n        {\n            "Security Name": "XP, Inc., Class A",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Brazil",\n            "Number of Shares": 1727039,\n            "Principle": null,\n            "Market Value": "$31,794,788"\n        },\n        {\n            "Security Name": "Canadian National Railway Co",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Canada",\n            "Number of Shares": 590129,\n            "Principle": null,\n            "Market Value": "$69,533,324"\n        },\n        {\n            "Security Name": "Canadian Pacific Kansas City Ltd",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Canada",\n            "Number of Shares": 863943,\n            "Principle": null,\n            "Market Value": "$71,716,917"\n        },\n        {\n            "Security Name": "Teck Resources Ltd., Class B",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Canada",\n            "Number of Shares": 520627,\n            "Principle": null,\n            "Market Value": "$24,929,366"\n        },\n        {\n            "Security Name": "Tencent Holdings Ltd",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "China",\n            "Number of Shares": 1620900,\n            "Principle": null,\n            "Market Value": "$78,613,506"\n        },\n        {\n            "Security Name": "Novo Nordisk A/S, Class B",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Denmark",\n            "Number of Shares": 770797,\n            "Principle": null,\n            "Market Value": "$107,071,543"\n        },\n        {\n            "Security Name": "Air Liquide SA",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "France",\n            "Number of Shares": 152299,\n            "Principle": null,\n            "Market Value": "$28,426,318"\n        },\n        {\n            "Security Name": "Cie de Saint-Gobain SA",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "France",\n            "Number of Shares": 592413,\n            "Principle": null,\n            "Market Value": "$51,768,531"\n        },\n        {\n            "Security Name": "LVMH Moët Hennessy Louis Vuitton SE",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "France",\n            "Number of Shares": 74437,\n            "Principle": null,\n            "Market Value": "$55,404,705"\n        },\n        {\n            "Security Name": "adidas AG, Class N",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Germany",\n            "Number of Shares": 135103,\n            "Principle": null,\n            "Market Value": "$34,662,479"\n        },\n        {\n            "Security Name": "Beiersdorf AG",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Germany",\n            "Number of Shares": 598034,\n            "Principle": null,\n            "Market Value": "$86,475,780"\n        },\n        {\n            "Security Name": "Deutsche Telekom AG, Registered Shares",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Germany",\n            "Number of Shares": 3162576,\n            "Principle": null,\n            "Market Value": "$89,984,829"\n        },\n        {\n            "Security Name": "Infineon Technologies AG, Class N",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Germany",\n            "Number of Shares": 861798,\n            "Principle": null,\n            "Market Value": "$31,627,294"\n        },\n        {\n            "Security Name": "Ferrari NV",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Italy",\n            "Number of Shares": 93070,\n            "Principle": null,\n            "Market Value": "$46,247,153"\n        },\n        {\n            "Security Name": "Intesa Sanpaolo SpA",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Italy",\n            "Number of Shares": 8971786,\n            "Principle": null,\n            "Market Value": "$37,496,526"\n        },\n        {\n            "Security Name": "Nintendo Co. Ltd",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Japan",\n            "Number of Shares": 913900,\n            "Principle": null,\n            "Market Value": "$49,701,748"\n        },\n        {\n            "Security Name": "Recruit Holdings Co. Ltd",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Japan",\n            "Number of Shares": 987300,\n            "Principle": null,\n            "Market Value": "$61,569,960"\n        },\n        {\n            "Security Name": "Sony Group Corp",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Japan",\n            "Number of Shares": 954100,\n            "Principle": null,\n            "Market Value": "$92,923,774"\n        },\n        {\n            "Security Name": "ASML Holding NV",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Netherlands",\n            "Number of Shares": 70926,\n            "Principle": null,\n            "Market Value": "$63,963,482"\n        },\n        {\n            "Security Name": "Samsung Electronics Co. Ltd",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "South Korea",\n            "Number of Shares": 1060195,\n            "Principle": null,\n            "Market Value": "$58,881,452"\n        },\n        {\n            "Security Name": "Julius Baer Group Ltd., Registered Shares",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Switzerland",\n            "Number of Shares": 572769,\n            "Principle": null,\n            "Market Value": "$33,517,571"\n        },\n        {\n            "Security Name": "Taiwan Semiconductor Manufacturing Co. Ltd",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "Taiwan",\n            "Number of Shares": 2287000,\n            "Principle": null,\n            "Market Value": "$67,707,491"\n        },\n        {\n            "Security Name": "AstraZeneca PLC",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "United Kingdom",\n            "Number of Shares": 298684,\n            "Principle": null,\n            "Market Value": "$52,349,042"\n        },\n        {\n            "Security Name": "RELX PLC",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "United Kingdom",\n            "Number of Shares": 788577,\n            "Principle": null,\n            "Market Value": "$36,818,991"\n        },\n        {\n            "Security Name": "Standard Chartered PLC",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "United Kingdom",\n            "Number of Shares": 6186681,\n            "Principle": null,\n            "Market Value": "$63,657,224"\n        },\n        {\n            "Security Name": "Baker Hughes Co., Class A",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "United States",\n            "Number of Shares": 1080704,\n            "Principle": null,\n            "Market Value": "$38,008,360"\n        },\n        {\n            "Security Name": "Cadence Design Systems, Inc.",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "United States",\n            "Number of Shares": 176006,\n            "Principle": null,\n            "Market Value": "$47,333,293"\n        },\n        {\n            "Security Name": "Mastercard, Inc., Class A",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "United States",\n            "Number of Shares": 172840,\n            "Principle": null,\n            "Market Value": "$83,540,486"\n        },\n        {\n            "Security Name": "Thermo Fisher Scientific, Inc.",\n            "Security Type": "Common Stock",\n            "Sector": null,\n            "Country": "United States",\n            "Number of Shares": 94919,\n            "Principle": null,\n            "Market Value": "$58,381,829"\n        },\n        {\n            "Security Name": "BlackRock Liquidity Funds, T-Fund, Institutional Shares",\n            "Security Type": "Money Market Fund",\n            "Sector": null,\n            "Country": null,\n            "Number of Shares": null,\n            "Principle": "$15,397,393",\n            "Market Value": "$15,397,393"\n        }\n    ]\n}'
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

