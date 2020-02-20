import zipfile
import requests




def download_file_from_google_drive(id, destination):
    try:
        URL = "https://docs.google.com/uc?export=download"

        session = requests.Session()

        response = session.get(URL, params = { 'id' : id }, stream = True)
        token = get_confirm_token(response)

        if token:
            params = { 'id' : id, 'confirm' : token }
            response = session.get(URL, params = params, stream = True)

        save_response_content(response, destination)
    except Exception as e:
        print(f"Download failed with error : {e}")

def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value

    return None

def save_response_content(response, destination):
    CHUNK_SIZE = 32768

    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)

def unzipFile():
    try:
        with zipfile.ZipFile("rlutilities.zip","r") as zip_ref:
            for _file in zip_ref.namelist():
                zip_ref.extract(_file)

    except Exception as e:
        print("Error unzipping the file!")
        print(e)
        _ = input("Press enter to exit")
        quit()

if __name__ == "__main__":
    print("Starting file download...")
    download_file_from_google_drive('1aXUUemEPm5XWFVr5WCzSDvl2IWjXue2v', 'rlutilities.zip')
    print("Download completed successfully.")
    print("Extracting file...")
    unzipFile()
    print("File extracted successfully.")
    print("Setup has completed successfully!")



