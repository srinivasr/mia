import requests
from bs4 import BeautifulSoup

url = 'https://www.example.com' # Replace with your target URL
response = requests.get(url)

if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
    print(soup.title.text) # Example: prints the page title
else:
    print('Failed to retrieve the webpage')