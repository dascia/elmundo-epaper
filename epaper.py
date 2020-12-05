import requests, json, shutil, os, tempfile, fpdf, time
from datetime import datetime, timedelta
from b2sdk.v1 import InMemoryAccountInfo, B2Api

BASE_ADDR = 'https://reader3.isu.pub/elmundocomsv'
READER_FILE = 'reader3_4.json'

# Use you blaze information
BLAZE_APP_KEY = os.getenv('BACKBLAZE_APP_KEY')
BLAZE_APP_KEY_ID = os.getenv('BACKBLAZE_APP_KEY_ID')
BLAZE_BUCKET_NAME = os.getenv('BACKBLAZE_BUCKET_NAME')

# Downloads the json object that describe the epaper edition
def download_epaper_json(edition:str) -> dict:
  json_addr:str = f'{BASE_ADDR}/{edition}/{READER_FILE}'
  print(f'Downloading epaper json from: {json_addr}')
  response = requests.get(json_addr)
  response.raise_for_status()
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
    if (r.status_code == 200):
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

# Upload the file to backblaze storage service
def upload_epaper_to_backblaze(pdf_info:dict, app_key_id:str, app_key:str, bucket_name:str):
  info:InMemoryAccountInfo = InMemoryAccountInfo()
  b2_api:B2Api = B2Api(info)
  b2_api.authorize_account('production', app_key_id, app_key)
  bucket = b2_api.get_bucket_by_name(bucket_name)
  print(f'Uploading {pdf_info["cover_file_path"]}')
  bucket.upload_local_file(local_file=pdf_info['cover_file_path'], file_name = f'cover_{pdf_info["edition"]}.jpg')
  print(f'Uploading {pdf_info["epaper_file_path"]}')
  bucket.upload_local_file(local_file=pdf_info['epaper_file_path'], file_name = f'{pdf_info["edition"]}.pdf')
  print('Files uploaded.')

  # Download the todays epaper version of el mundo and returns the pdf local file path and file name
def download_epaper(edition: str) -> dict:
  # Download the epaper json object
  epaper_json = download_epaper_json(edition)
  # Download the epaper images, store them in temp dir edition
  images_path_collection = download_epaper_images(edition, epaper_json)
  # Create pdf from images with the edition name
  epaper_filename = f'{edition}.pdf'
  pdf_output_path = f'{tempfile.gettempdir()}/{edition}/{epaper_filename}'
  merge_images_to_pdf(images_path_collection, pdf_output_path)
  return { 'edition': edition, 'cover_file_path': images_path_collection[0],  'epaper_file_path': pdf_output_path }

# # Starts the epaper download job
date = datetime.utcnow() - timedelta(hours=6)
edition:str = f'mundo{date.strftime("%d%m%y")}'
is_task_successful:bool = False
while(!is_task_successful):
  try:
    epaper_file_info:dict = download_epaper(edition)
    # Upload the pdf file
    upload_epaper_to_backblaze(epaper_file_info, BLAZE_APP_KEY_ID, BLAZE_APP_KEY, BLAZE_BUCKET_NAME)
    is_task_successful = True
  except Exception as ex:
    print(f"Error processing the newspaper edition: {ex}")
    # if scripts fails execute it again in 15 minutes
    time.sleep(900)