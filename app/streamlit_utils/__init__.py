import os
# Change to jgarcia directory
if os.getcwd() == "/home/vulcano/streamlit":
        os.chdir("..")

import sys
if "./streamlit" not in sys.path:
    sys.path.append("./streamlit")
if "./digivolcan/functions" not in sys.path:
    sys.path.append("./digivolcan/functions")
