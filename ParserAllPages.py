import pdfplumber
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key=os.getenv('API_KEY')
targetString = os.getenv('INVESTMENT_PAGE_TARGET')
continuedTargetString = os.getenv('INVESTMENT_CONTINUE_PAGE_TARGET')


pdf = pdfplumber.open("PDFs/fundamental-intl-equity-sar.pdf")

# Get full report text
reportText = ""
for page in pdf.pages:
    reportText += page.extract_text(layout=True) + "\n"

# Determine pages that are schedule of investments, or are continued schedule of investments
targetPages = []
processedReport = reportText

# Reduce pages to pages marked as Schedule of Investment or other important keywords
# To prevent file inconsistencies, remove all whitespace and compare as lowercase

for page in pdf.pages:
    pageText = page.extract_text(layout=True)
    processedPageText = pageText.replace(" ", "").lower()
    for index, pageLine  in enumerate(processedPageText.split()):
        if targetString in pageLine:
            if continuedTargetString in pageLine:
                targetPages.append((index, 0, pageText))
                break
            else:
                 targetPages.append((index, 1, pageText)) # The results from this page should be folded into the first page's data
                 break

# client = OpenAI(
#     api_key
# )
# response = client.chat.completions.create(
#     messages=[
#         { "role": "system", "content": "You are parsing a report of a mutual fund." },
#         { "role": "assistant", "content": "For every Schedule of Investments contained within this report, what is the Name and first page number?" },
#         { "role": "assistant", "content": "Response should be in JSON format, where each Schedule of Investments is an array item. { {[\"Fund Name\": Fund Name, \"Page\": Page Number]},... }" },
#         { "role": "user", "content": reportText },
#     ],
#     model="gpt-4o-mini",
# )

# print(response.choices[0].message.content)

f = open("fullFile.txt", "w", encoding="utf-8")
f.write(reportText)
f.close()