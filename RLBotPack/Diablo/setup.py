import urllib.request
import zipfile


def downloadFile():
    try:
        urllib.request.urlretrieve("https://urlzs.com/XSvMA", 'rlutilities.zip')
    except Exception as e:
        print("Error downloading file!")
        print(e)
        _ = input("Press enter to exit")
        quit()

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
    downloadFile()
    print("Download completed successfully.")
    print("Extracting file...")
    unzipFile()
    print("File extracted successfully.")
    print("Setup has completed successfully!")