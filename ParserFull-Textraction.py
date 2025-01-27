import pdfplumber
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key=os.getenv('API_KEY')
targetString = os.getenv('INVESTMENT_PAGE_TARGET')
continuedTargetString = os.getenv('INVESTMENT_CONTINUE_PAGE_TARGET')


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
    pageText = page.extract_text(layout=True)
    processedPageText = pageText.replace(" ", "").lower()
    for index, pageLine  in enumerate(processedPageText.split()):
        if targetString in pageLine:
            if continuedTargetString in pageLine:
                investmentPages.append((index, 0, pageText))
                break
            else:
                 investmentPages.append((index, 1, pageText)) # The results from this page should be folded into the first page's data
                 break

client = OpenAI(
    api_key
)

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

