# Schedule Of Investments Parser

## Description

A python script to analyze mutual fund PDF releases and convert core points into JSON.
See the /examples folder for examples of input, configuration, and output.

### Dependencies

Ensure uv is installed to retrieve dependencies: `pip install uv`.

Install remaining dependencies with `uv sync`

### Installing

This project requires an OpenAI API key to run.
This can be configured by adding a `.env` file to root.
```
API_KEY = "{Your_Api_Key}"
```
### Configuration

For a given PDF, there should be a configuration.ini file. The file should contain the following information:
```
DOC = "examples/document.pdf" # The location of the PDF
DOC_HEADER = 80 # The height of the header of every Schedule of investment page in the PDF
DOC_FOOTER = 0 # The height of the footer of every Schedule of investment page in the PDF
DOC_COLCOUNT = 2 # The number of columns in every Schedule of investment page in the PDF
INVESTMENT_PAGE_TARGET = "scheduleofinvestments" # A normalized target string used to identify page headers that contain Schedule of Investment data. Remove any whitespace or capital letters.
INVESTMENT_CONTINUE_PAGE_TARGET = "(continued)" # A normalized target string used to identify page headers that continue the previous Schedule of Investment page. Remove any whitespace or capital letters.
```

If you are not sure how to find header/footer height, run `py checkHeaders.py {configuration.ini} {pageNumber}` and sample images of your configuration will be generated for review. In a release version of this project,
a UI including a view of the page will allow easy adjustment of this configuration file, instead of relying on image generation or PDF knowledge.

### Executing program

* To run the parser, call `py .\parser.py configuration.ini outputfile.json`

To run this on an existing example file:
```
py .\parser.py .\examples\fqr-retail-blackrock-international-fund.ini .\examples\fqr-retail-blackrock-international-fund.json
```

## Version History

* 0.1
    * Initial Release
