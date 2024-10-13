import requests
from bs4 import BeautifulSoup
import os
import time
import redis
import pymongo
import boto3
import urllib3
from dotenv import load_dotenv


class DentalScraper:
    def __init__(self, max_page, proxies=None):
        self.url = 'https://dentalstall.com/shop/'
        self.proxies = proxies
        self.max_page = max_page
        self.product_data = []
        self.updates = 0
        self.retries = 3
        self.product_data = []
        self.image_dir = "images"
        self.retry_delay = 5

        load_dotenv()

        #redis client for caching mechanism
        self.redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

        #mongodb client initialize
        self.mongo_client = pymongo.MongoClient("mongodb+srv://rsing116:jarvis@my-product-image-atlys.nhsko.mongodb.net/?retryWrites=true&w=majority&appName=my-product-image-atlys", tls = True, tlsAllowInvalidCertificates=True)
        self.db = self.mongo_client["scraper_db"]
        self.products_collection = self.db["products"]

        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv("aws_access_key_id"),
            aws_secret_access_key=os.getenv("aws_secret_access_key"),
            region_name="eu-north-1"
        )

        self.bucket_name = 'my-product-images-atlys'


    #use the commented code below to download and store the images locally
        # Create image directory if it doesn't exist
    #     if not os.path.exists(self.image_dir):
    #         os.makedirs(self.image_dir)

    # # def download_image(self, image_url, product_name):
    # #     # Create a valid image file name
    # #     image_name = product_name.replace(" ", "_").replace("/", "_") + ".jpg"
    # #     image_path = os.path.join(self.image_dir, image_name)

    # #     # Download and save the image
    # #     img_data = requests.get(image_url).content
    # #     with open(image_path, 'wb') as handler:
    # #         handler.write(img_data)

    # #     return image_path
            
    
    def upload_image_to_s3(self, image_url, product_name):
        # Create a valid image file name for S3
        image_name = product_name.replace(" ", "_").replace("/", "_") + ".jpg"

        try:
            # Download image data
            img_data = requests.get(image_url).content

            # Upload image to S3
            self.s3_client.put_object(Bucket=self.bucket_name, Key=image_name, Body=img_data, ContentType='image/jpeg')

            # Return the S3 URL
            s3_url = f"https://{self.bucket_name}.s3.amazonaws.com/{image_name}"
            return s3_url

        except Exception as e:
            print(f"Failed to upload {image_name} to S3: {e}")
            return None


    def scrape_page(self, page_number):
        target = self.url +'/page/' + f'{page_number}' if page_number>1 else self.url
        for attempt in range(3): #retrying each page for 3 times 
            try:
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

                response = requests.get(target, proxies=self.proxies, verify=False)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Find all products
                    products = soup.find_all('li', class_='product')

                    for product in products:
                        # Extract the product name
                        name = product.find('h2', class_='woo-loop-product__title').text.strip()

                        # Extract the product price
                        price = product.find('span', class_='woocommerce-Price-amount').text.strip()
                        price = int(float(price.replace('₹', '')))
                        # print(float(price[1:]))
                        # price = int(price[1:])

                        # Extract the image URL
                        noscript_tag = product.find('noscript')
                        nosoup = BeautifulSoup(noscript_tag.decode_contents(), 'html.parser')
                        image_url = nosoup.find('img')['src']

                        # Download the image and get the path of image in AWS S3
                        s3_image_url = self.upload_image_to_s3(image_url, name)

                        #image path if locally saving the images on pc
                        # image_path = self.download_image(image_url, name)

                        if s3_image_url:
                            # Check if the product already exists in Redis (for caching)
                            cached_price = self.redis_client.get(name)

                            # If product doesn't exist or price has changed, update MongoDB
                            if cached_price is None or int(cached_price) != price:
                                print(f"Updating product: {name}")
                                self.updates +=1

                                # Insert or update the product data in MongoDB
                                self.products_collection.update_one(
                                    {"product_name": name},
                                    {
                                        "$set": {
                                            "product_name": name,
                                            "product_price": price,
                                            "image_url": s3_image_url
                                        }
                                    },
                                    upsert=True
                                )

                                # Update Redis cache with the new price
                                self.redis_client.set(name, price)

                        # Store the product data
                        self.product_data.append({
                            "product_title": name,
                            "product_price": price,
                            "path_to_image": image_url,
                            "link_to_aws_s3": s3_image_url
                        })
                break
            except (requests.RequestException, requests.HTTPError) as e:
                print(f"Attempt {attempt} failed: {e}")
                if attempt < self.retries:
                    print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    print(f"Failed to retrieve page {page_number} after {self.retries} attempts.")



    def scrape_all_pages(self):
        for i in range(1, self.max_page + 1):
            self.scrape_page(i)
