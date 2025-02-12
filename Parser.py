import sys
import os
import pdfplumber
import json

from configobj import ConfigObj
from dotenv import load_dotenv
from openai import OpenAI
# Initialize default configuration
DEFAULT_INVESTMENT_PAGE_TARGET = "scheduleofinvestments"
DEFAULT_INVESTMENT_CONTINUE_PAGE_TARGET = "(continued)"
DEFAULT_COLCOUNT = 1

# PDFPlumber extraction functions
def extractPageHeader(page, headerHeight):
    return page.crop((0, 0, page.width, headerHeight))

def extractPageFooter(page, footerHeight):
    return page.crop((0, page.height - footerHeight, page.width, page.height))

def extractPageBody(page, headerHeight, footerHeight, columnCount):
    segmentSize = 1 / columnCount
    sections = []
    for column in range(columnCount):
        croppedPage = page.crop((segmentSize * column * float(page.width), headerHeight, segmentSize * (column + 1) * float(page.width), page.height - footerHeight))
        sections.append(croppedPage)
    return sections

def extractPageHeaderText(page, headerHeight):
    return extractPageHeader(page, headerHeight).extract_text(layout=True) + "\n"

def extractPageFooterText(page, footerHeight):
    return extractPageFooter(page, footerHeight).extract_text(layout=True) + "\n"

def extractPageBodyText(page, headerHeight, footerHeight, columnCount):
    reportText = ""
    for column in extractPageBody(page, headerHeight, footerHeight, columnCount):
        reportText += column.extract_text(layout=True) + "\n"
    return reportText

def constructScheduleOfInvestmentData(configFile):
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

    investmentPageTarget = config.get('INVESTMENT_PAGE_TARGET') or DEFAULT_INVESTMENT_PAGE_TARGET
    investmentContinuePageTarget = config.get('INVESTMENT_CONTINUE_PAGE_TARGET') or DEFAULT_INVESTMENT_CONTINUE_PAGE_TARGET

    print("Opening PDF...")
    pdf = pdfplumber.open(pdfDoc)

    # Determine pages that are schedule of investments, or are continued schedule of investments
    investmentPages = []

    # Reduce pages to pages marked as Schedule of Investment or other important keywords in the header
    # To prevent file inconsistencies, remove all whitespace and compare as lowercase
    for page in pdf.pages:
        pageHeaderText = extractPageHeaderText(page, headerHeight)
        processedPageHeader = pageHeaderText.replace(" ", "").lower()

        isContinued = False

        # Ensure we track whether this is a continued page and needs to be combined into the prior page(s)
        if investmentContinuePageTarget in processedPageHeader:
            isContinued = True

        if investmentPageTarget in processedPageHeader:
            pageText = pageHeaderText + extractPageBodyText(page, headerHeight, footerHeight, columnCount)

            if footerHeight:
                pageText += extractPageFooterText(page, footerHeight)
            
            investmentPages.append((pageText, isContinued))

    print("PDF text extracted.")
    return investmentPages

# OpenAI Integration to parse extracted text
# TODO: This could be modified to make all calls async to speed up output time. 
def parseInvestmentThroughAPI(investmentPages, client):
    # Loop through funds, extracting key datapoints
    scheduleOfInvestmentsList = [] # An array of funds found within this document
 
    print("Parsing Schedule of Investment documents.")
    print(f"\r0/{len(investmentPages)} parsed...", end='', flush=True)
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
                { "role": "user", "content": scheduleOfInvestment[0] },
            ],
            model="gpt-4o-mini",
            response_format = { "type": "json_object" }
        )


        jsonResponse = response.choices[0].message.content
        responseDict = json.loads(jsonResponse)

        if investmentPages[index][1]: # This is a continued page - Fold it into the last object
            parentDict = scheduleOfInvestmentsList[len(scheduleOfInvestmentsList) - 1] 
            parentDict['Schedule of Investments'].extend(responseDict['Schedule of Investments'])
        else:
            scheduleOfInvestmentsList.append(responseDict)

        print(f"\r{index + 1}/{len(investmentPages)} parsed...", end='', flush=True)
    print()
    return scheduleOfInvestmentsList

# Pretty print based on configuration
def outputScheduleInvestmentJson(scheduleOfInvestmentsList, outputFile):
    # Output result to file or console

    # TODO: Implement a try/catch and verify safely that ChatGPT returned JSON, as it cannot be guaranteed, even with response_format = { "type": "json_object" }
    completeJson = json.dumps({ "funds": scheduleOfInvestmentsList }, indent=4)

    if outputFile:
        f = open(outputFile, "w")
        f.write(completeJson)
        f.close()
        print(f"JSON results written to {outputFile}")
    else:
        print(completeJson)

def main():
    print("Initializing from config...")

    # Initialize from config and environment variables
    if len(sys.argv) < 2:
        print('Please pass an argument to a config file. See README on Github for further information.')
        exit
    configFile = sys.argv[1]

    outputFile = None
    if len(sys.argv) > 2:
        outputFile = sys.argv[2]

    load_dotenv()
    api_key=os.getenv('API_KEY')

    if len(api_key) == 0:
        print('An OpenAPI Key for gpt-4o-mini is required. See README on Github for further information.')
        exit

    client = OpenAI(
        api_key=api_key
    )

    investmentData = constructScheduleOfInvestmentData(configFile)
    apiResponse = parseInvestmentThroughAPI(investmentData, client)
    outputScheduleInvestmentJson(apiResponse, outputFile)

if __name__=="__main__":
    main()