import pdfplumber
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key=os.getenv('API_KEY')
targetString = os.getenv('INVESTMENT_PAGE_TARGET')
continuedTargetString = os.getenv('INVESTMENT_CONTINUE_PAGE_TARGET')

pdf = pdfplumber.open("PDFs/document.pdf")
page = pdf.pages[19]


im = page.to_image(resolution=300)
im.save("Sample.png")

table_settings = {
    "vertical_strategy": "text", 
    "horizontal_strategy": "text",
    "snap_tolerance": 10,
    "snap_x_tolerance": 10,
    "snap_y_tolerance": 10,
    "join_tolerance": 10,
    "join_x_tolerance": 10,
    "join_y_tolerance": 10,
    "edge_min_length": 10,
    "intersection_tolerance": 10,
    "intersection_x_tolerance": 10,
    "intersection_y_tolerance": 10,
    "text_tolerance": 10,
    "text_x_tolerance": 10,
    "text_y_tolerance": 10,
}

im.debug_tablefinder(table_settings)
im.save("TableResults.png")

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