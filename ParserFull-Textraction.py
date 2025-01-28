import sys
import os
import pdfplumber

from configobj import ConfigObj
from dotenv import load_dotenv
from openai import OpenAI

if len(sys.argv == 0):
    print('Please pass an argument to a config file. See README on Github for further information.')
    exit

load_dotenv()
api_key=os.getenv('API_KEY')

if len(api_key) is 0:
    print('An OpenAPI Key for gpt-4o-mini is required. See README on Github for further information.')
    exit

client = OpenAI(
    api_key
)

# Initialize default configuration
DEFAULT_INVESTMENT_PAGE_TARGET = "scheduleofinvestments"
DEFAULT_INVESTMENT_CONTINUE_PAGE_TARGET = "(continued)"
DEFAULT_COLCOUNT = 1

# Load data from passed configuration file
config = ConfigObj('myConfigFile.ini')
pdfDoc = config.get('DOC') or ''
headerHeight = int(config.get('DOC_HEADER')) or 0
footerHeight = int(config.get('DOC_FOOTER')) or 0
investmentPageTarget = config.get('INVESTMENT_PAGE_TARGET') or DEFAULT_INVESTMENT_PAGE_TARGET
investmentContinuePageTarget = config.get('INVESTMENT_CONTINUE_PAGE_TARGET') or DEFAULT_INVESTMENT_CONTINUE_PAGE_TARGET
columCount = int(config.get('DOC_COLCOUNT')) or DEFAULT_COLCOUNT
segmentSize = 1 / columCount

def extractPageText(page):
    # Extract Header
    pageHeader = page.crop((0, 0, page.width, headerHeight))
    pageHeader.to_image(resolution=300).save("Header.png")

    # Extract Footer
    pageFooter = page.crop((0, footerHeight, page.width, page.height))
    pageFooter.to_image(resolution=300).save("Footer.png")

    # Combine segments into valid text output
    reportText = pageHeader.extract_text(layout=True) + "\n"

    for column in range(columCount):
        croppedPage = page.crop((segmentSize * column * float(page.width), headerHeight, segmentSize * (column + 1) * float(page.width), footerHeight))
        croppedPage.to_image(resolution=300).save(f'CroppedPage{column}.png')
        reportText += croppedPage.extract_text(layout=True) + "\n"

    reportText += pageFooter.extract_text(layout=True) + "\n"

pdf = pdfplumber.open("PDFs/fqr-retail-blackrock-international-fund.pdf")

# Get full report text
reportText = ""
for page in pdf.pages:
    reportText += page.extract_text(layout=True) + "\n"

# Determine pages that are schedule of investments, or are continued schedule of investments
investmentPages = []
processedReport = reportText

# Reduce pages to pages marked as Schedule of Investment or other important keywords
# To prevent file inconsistencies, remove all whitespace and compare as lowercase
for page in pdf.pages:
    pageText = extractPageText(page)
    processedPageText = pageText.replace(" ", "").lower()
    for index, pageLine  in enumerate(processedPageText.split()):
        if investmentPageTarget in pageLine:
            if investmentContinuePageTarget in pageLine:
                investmentPages.append((index, 0, pageText))
                break
            else:
                 investmentPages.append((index, 1, pageText)) # The results from this page should be folded into the first page's data
                 break

# Loop through funds, extracting key datapoints
for scheduleOfInvestment in investmentPages:
    response = client.chat.completions.create(
        messages=[
            { "role": "system", "content": "You are parsing the Schedule of Investments document of a mutual fund." },
            { "role": "assistant", "content": '''
                Extract the Fund Name and the Report Date in ISO format. 
                Extract a list of each holding item within the schedule of investments. Each holding item should contain the following values:
                    Security Name, Security Type, Sector, Country, Number of Shares, Principle Amount, Market Value.
                    If a value is not present, they should be returned as null.
            ''' },
            { "role": "assistant", "content": '''Response should be in JSON format as 
            { 
                "Fund Name": Fund Name, 
                "Report Date": Report Date,
                "Schedule of Investments": [
                    {
                        "Security Name": Security Name,
                        "Security Type": Security Type,
                        "Sector": Business Sector,
                        "Country": Country,
                        "Number of Shares": Number of Shares,
                        "Principle":  Principal Amount,
                        "Market Value": Market Value
                    },
                ]
            }''' 
            },
            { "role": "assistant", "content": '''Example: { 
                "Fund Name": The Hartford Balanced Income Fund, 
                "Report Date": April 30, 2023,
                "Schedule of Investments": [
                    {
                        "Security Name": "JetBlue Airways Corp",
                        "Security type": "Convertible Bonds",
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
    )
    print(response.choices[0].message.content)

