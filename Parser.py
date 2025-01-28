import pdfplumber
import os
from dotenv import load_dotenv
from openai import OpenAI
from PyPDF2 import PdfReader


load_dotenv()

api_key=os.getenv('API_KEY')
targetString = os.getenv('INVESTMENT_PAGE_TARGET')
continuedTargetString = os.getenv('INVESTMENT_CONTINUE_PAGE_TARGET')

pdf = pdfplumber.open("../PDFs/document.pdf")
page = pdf.pages[19]

# Normal text
extractedText = page.extract_text(layout=True)

# Column split text



# Extract Header
headerHeight = int(os.getenv('DOC_HEADER'))
pageHeader = page.crop((0, 0, page.width, headerHeight))
pageHeader.to_image(resolution=300).save("Header.png")

# Extract Footer
footerHeight = int(os.getenv('DOC_FOOTER'))
pageFooter = page.crop((0, footerHeight, page.width, page.height))
pageFooter.to_image(resolution=300).save("Footer.png")

colCount = int(os.getenv('DOC_COLCOUNT'))
segmentSize = 1 / colCount



# Combine segments into valid text output
reportText = pageHeader.extract_text(layout=True) + "\n"

for column in range(colCount):
    croppedPage = page.crop((segmentSize * column * float(page.width), headerHeight, segmentSize * (column + 1) * float(page.width), footerHeight))
    croppedPage.to_image(resolution=300).save(f'CroppedPage{column}.png')
    reportText += croppedPage.extract_text(layout=True)+ "\n"

reportText += pageFooter.extract_text(layout=True)+ "\n"

f = open("CroppedStrategy.txt", "w")
f.write(reportText)
f.close()



# # Attempt to view table with various settings for analysis
# im = page.to_image(resolution=300)
# im.save("Sample.png")

# table_settings = {
#     "vertical_strategy": "text", 
#     "horizontal_strategy": "text",
#     "snap_tolerance": 10,
#     "snap_x_tolerance": 10,
#     "snap_y_tolerance": 10,
#     "join_tolerance": 10,
#     "join_x_tolerance": 10,
#     "join_y_tolerance": 10,
#     "edge_min_length": 10,
#     "intersection_tolerance": 10,
#     "intersection_x_tolerance": 10,
#     "intersection_y_tolerance": 10,
#     "text_tolerance": 10,
#     "text_x_tolerance": 10,
#     "text_y_tolerance": 10,
# }

# im.debug_tablefinder(table_settings)
# im.save("TableResults.png")
# # No good! Can't determine correct area of table. Can't be relied upon as a measure to count separate table columns

# # Try with PyPDF2 instead
# with open('../PDFs/document.pdf', 'rb') as f:
#     pdf = PdfReader(f)
#     testPage = pdf.pages[19]
#     textOfPage = testPage.extract_text()
#     f = open("textSampleFromPyPDF2.txt", "w")
#     f.write(textOfPage)
#     f.close()
# No good! Misses some text in titles, depending on formatting!




# foundText = page.extract_text(layout=True)


# client = OpenAI(
#     api_key
# )
# response = client.chat.completions.create(
#     messages=[
#         { "role": "system", "content": "You are parsing the Schedule of Investments document of a mutual fund." },
#         { "role": "assistant", "content": "What is the Fund Name and date (in ISO format) in  of this Schedule of Investments document?" },
#         { "role": "assistant", "content": "Response should be in JSON format as { \"Fund Name\": Fund Name, \"Date\":date }" },
#         { "role": "user", "content": foundText },
#     ],
#     model="gpt-4o-mini",
# # )

# print(response.choices[0].message.content)

# f = open("foundTextLayouWithGPT.txt", "w")
# f.write(foundText)
# f.close()