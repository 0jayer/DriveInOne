# an interface for different cloud storage services, such as Google Drive, Dropbox, OneDrive, or even local drives if they are available online 
# it provides a unified API for uploading, downloading, deleting, and listing files and folders in the cloud storage services.
# it also provides a way to authenticate and authorize the user to access the cloud storage services.
# the implementation of the interface is done in a separate module for each cloud storage service, such as google_drive.py, dropbox.py, onedrive.py, etc.
# the main module, drive.py, imports the specific cloud storage service module based on the user's choice and provides a unified API for the user to interact with the cloud storage services.  

#create a interface
from abc import ABC, abstractmethod

class CloudStorage(ABC):

    @abstractmethod
    def authenticate(self):
        """Authenticate the user to access the cloud storage service."""
        pass

    @abstractmethod
    def upload_file(self, file_path, destination_path):
        """Upload a file to the cloud storage service."""
        pass

    @abstractmethod
    def download_file(self, file_path, destination_path):
        """Download a file from the cloud storage service."""
        pass

    @abstractmethod
    def get_quota(self):
        """Get the storage quota of the cloud storage service."""
        pass

    @abstractmethod
    def list_files(self, folder_path):
        """List the files in a folder in the cloud storage service."""
        pass

    @abstractmethod
    def delete_file(self, file_path):
        """Delete a file from the cloud storage service."""
        pass
    

    