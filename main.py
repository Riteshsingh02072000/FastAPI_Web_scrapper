from fastapi import FastAPI, HTTPException, Header, Depends
from scraper import DentalScraper
from typing import Optional
from dotenv import load_dotenv
import os
from notification import EmailNotifier

app = FastAPI()
# STATIC_TOKEN = "itssafehere"
notifier = EmailNotifier()

#verifying the static token
load_dotenv()
def verify_token(token: Optional[str] = None):
    if token != os.getenv("STATIC_TOKEN"):
        raise HTTPException(status_code=401, detail="Invalid or missing token")

@app.get("/scrape/")
def scrape_products(max_page: int, proxy_string: Optional[str] = None, token: Optional[str] = None):
    verify_token(token)
    proxies = None
    if proxy_string:
        proxies = {
            'http': proxy_string,
            'https': proxy_string,
        }

    if max_page <= 0:
        raise HTTPException(status_code=400, detail="max_page should be greater than 0")
    
    # Creating an instance of DentalScraper with the given max_page while calling the FastAPI
    scraper = DentalScraper(max_page, proxies=proxies)

    # Scrape the data of products
    scraper.scrape_all_pages()

    num_products_scraped = len(scraper.product_data)
    num_db_updates = scraper.updates


    #printing the stats of current session in console
    print(f"Web Scrapping Successful!! Number of Products scraped: {num_products_scraped} \n& Number of Updates in DB during current session: {num_db_updates}")

    subject = "Scraping Session Completed"
    body = (
        f"Scraping session completed successfully.\n"
        f"Number of Products Scraped: {num_products_scraped}\n"
        f"Number of Updates in DB: {num_db_updates}"
    )

    # Send the email notification
    notifier.send_email(subject, body)


    # Return the structured product data 
    return {"products": scraper.product_data}