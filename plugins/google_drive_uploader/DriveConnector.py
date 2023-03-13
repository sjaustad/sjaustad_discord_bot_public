## NEEDS TESTING
from __future__ import print_function

from googleapiclient import discovery
from httplib2 import Http
from oauth2client import file, client, tools
from settings.server_settings import settings
settings = settings()
from datetime import datetime
import asyncio,time, discord

class DriveConnector:
    def __init__(self):
        self.SCOPES = settings.googledrive.scope
        self.store = file.Storage(f'{settings.server.base_dir}/plugins/google_drive_uploader/storage.json')
        self.creds = self.store.get()
        if not self.creds or self.creds.invalid:
            self.flow = client.flow_from_clientsecrets(settings.googledrive.credentiallocation, self.SCOPES)
            self.creds = tools.run_flow(self.flow, self.store)
        self.drive = discovery.build('drive', 'v3', http=self.creds.authorize(Http()))

    async def create_folder(self, user: discord.user):

        timestamp = str(int(time.time() * 1000))
        folder_name = user.name + '_' + timestamp #+ datetime.now().strftime('%m/%d/%y-%I:%M%p') 
        file_metadata={
            'name': folder_name,
            'mimeType':'application/vnd.google-apps.folder',
            'parents':[settings.googledrive.uploadfolderid]
        }
        #folder_info =self.drive.files().create(body=file_metadata,fields='id').execute()
        gfolder=self.drive.files().create(body=file_metadata,fields='id')
        from concurrent.futures.thread import ThreadPoolExecutor
        loop = asyncio.get_running_loop()
        executor = ThreadPoolExecutor(max_workers=4)
        future = loop.run_in_executor(executor, gfolder.execute)
        folder_info = (await asyncio.gather(future))[0]


        folder_info['folder_name'] = folder_name
        return folder_info
    
    async def upload_file(self, file, gdrive_folder):
        gfile = self.drive.CreateFile({'parents':[{'id':gdrive_folder['id']}]})
        gfile.SetContentFile(file)
        gfile.upload()
        return gfile

    async def share_folder(self, folder_info):
        permission_metadata={
            'role': 'writer',
            'type': 'anyone'
        }
        self.drive.permissions().create(fileId=folder_info['id'],body=permission_metadata).execute()

        #return self.drive.files().get(fileId=folder_info['id'], fields='webViewLink')
        return "https://drive.google.com/drive/folders/" + folder_info['id']
    
    async def check_upload_status(self, folder_info):
        file_list = self.drive.files().list(q = "'" + folder_info['id'] + "' in parents", pageSize=10, fields="nextPageToken, files(id, name)").execute().get('files', [])
        if len(file_list) > 0:

            status = {
                'file_id':file_list[0]['id'],
                'file_name':file_list[0]['name']
            }
        else: status = False
        return status
    
    async def remove_writer_permissions(self, folder_info):
        permission_metadata={
            'role': 'reader',
            'type': 'anyone'
        }
        self.drive.permissions().create(fileId=folder_info['id'],body=permission_metadata).execute()

"""
files = DRIVE.files().list().execute().get('files', [])
for f in files:
    print(f['name'], f['mimeType'])
"""