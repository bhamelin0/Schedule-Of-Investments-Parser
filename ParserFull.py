import pdfplumber
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key=os.getenv('API_KEY')
targetString = os.getenv('INVESTMENT_PAGE_TARGET')
continuedTargetString = os.getenv('INVESTMENT_CONTINUE_PAGE_TARGET')

#pdf = pdfplumber.open("PDFs/fundamental-intl-equity-sar.pdf")
# pdf = pdfplumber.open("PDFs/fqr-retail-blackrock-international-fund.pdf")
pdf = pdfplumber.open("PDFs/document.pdf")

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
        if pageLine.startswith(targetString):
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
            { "role": "assistant", "content": "What is the Fund Name and date (in ISO format) in  of this Schedule of Investments document?" },
            { "role": "assistant", "content": "Response should be in JSON format as { \"Fund Name\": Fund Name, \"Date\":date }" },
            { "role": "user", "content": scheduleOfInvestment[2] },
        ],
        model="gpt-4o-mini",
    )
    print(response.choices[0].message.content)

