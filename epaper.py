import requests, json, shutil, os, tempfile, fpdf
from datetime import datetime, timedelta

BASE_ADDR = 'https://reader3.isu.pub/elmundocomsv'
READER_FILE = 'reader3_4.json'

# Downloads the json object that describe the epaper edition
def download_epaper_json(edition:str) -> dict:
  json_addr:str = f'{BASE_ADDR}/{edition}/{READER_FILE}'
  print(f'Downloading epaper json from: {json_addr}')
  response = requests.get(json_addr)
  json_response:dict = response.json()
  return json_response

# Downloads and copy the images extracting the url from the epaper json file
def download_epaper_images(edition:str, epaper_json:dict) -> list[str]:
  imgs_collection_paths:list[str] = []
  epaper_dir:str = f'{tempfile.gettempdir()}/{edition}'
  print(f'Creating directory: {epaper_dir}')
  os.makedirs(epaper_dir, exist_ok=True)
  epaper_pages:list[dict] = epaper_json["document"]["pages"]
  page_counter = 1
  for epaper_page in epaper_pages:
    img_url:str = f'http://{epaper_page["imageUri"]}'
    print(f'Requesting image: {img_url}')
    r = requests.get(img_url, stream=True)
    img_file_path = f'{epaper_dir}/{page_counter}.jpg'
    with open(img_file_path, 'wb') as out_file:
      r.raw.decode_content = True
      shutil.copyfileobj(r.raw, out_file)
    imgs_collection_paths.append(img_file_path)
    page_counter += 1
    del r
  return imgs_collection_paths

# Merge a list of images into a pdf
def merge_images_to_pdf(images_path:list[str], output_path:str):
  pdf = fpdf.FPDF()
  for img_path in images_path:
    pdf.add_page()
    print(f'Embedding image: {img_path}')
    pdf.image(img_path, x=0, y=0, w=210, h=297)
  pdf.output(output_path, 'F')

# Download the todays epaper version of el mundo
def download_epaper():
  date = datetime.utcnow() - timedelta(hours=6)
  edition:str = f'mundo{date.strftime("%d%m%y")}'
  # Download the epaper json object
  epaper_json = download_epaper_json(edition)
  # Download the epaper images, store them in temp dir edition
  images_path_collection = download_epaper_images(edition, epaper_json)
  # Create pdf from images with the edition name
  pdf_output_path = f'{tempfile.gettempdir()}\{edition}\{edition}.pdf'
  merge_images_to_pdf(images_path_collection, pdf_output_path)

# Starts the epaper download job
download_epaper()