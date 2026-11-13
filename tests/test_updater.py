import sys,json,unittest,hashlib,io,uuid,shutil,urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import updater as u

def release(version='v1.4.0'):
    base='https://github.com/TommiLin/Offline-Book-Converter/releases/download/'+version+'/'
    return {'tag_name':version,'draft':False,'prerelease':False,'assets':[
        {'name':'OfflineBookConverter-Setup-'+version[1:]+'.exe','browser_download_url':base+'OfflineBookConverter-Setup-'+version[1:]+'.exe','state':'uploaded','size':3},
        {'name':'SHA256SUMS.txt','browser_download_url':base+'SHA256SUMS.txt','state':'uploaded'}]}

class Response(io.BytesIO):
    def __init__(self,data,size=None):super().__init__(data);self.headers={'Content-Length':str(len(data) if size is None else size)}
    def geturl(self):return 'https://release-assets.githubusercontent.com/test/installer'

class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).resolve().parent/'.test-work';self.root.mkdir(exist_ok=True)
        self.folder=self.root/uuid.uuid4().hex;self.folder.mkdir()
    def tearDown(self):shutil.rmtree(self.folder)
    def info(self):return u.release_info(release(),'TommiLin/Offline-Book-Converter','1.3.0')
    def test_repository_is_fixed(self):
        self.assertEqual(u.REPOSITORY,'TommiLin/Offline-Book-Converter')
        with self.assertRaises(u.UpdateError):u.release_info(release(),'other/repo','1.3.0')
    def test_no_published_release(self):
        error=urllib.error.HTTPError('url',404,'Not found',{},None)
        with patch.object(u,'read_bytes',side_effect=error),self.assertRaises(u.NoPublishedRelease):u.check_latest('1.3.0')
    def test_numeric_version_order(self):
        self.assertGreater(u.version_tuple('v1.10.0'),u.version_tuple('1.9.99'))
        for invalid in ('latest','1.4','1.4.0-beta','1.4.0/extra'):
            with self.assertRaises(u.UpdateError):u.version_tuple(invalid)
    def test_same_and_older_versions(self):
        self.assertIsNone(u.release_info(release('v1.3.0'),'TommiLin/Offline-Book-Converter','1.3.0'))
        self.assertIsNone(u.release_info(release('v1.2.0'),'TommiLin/Offline-Book-Converter','1.3.0'))
    def test_prerelease_and_draft_are_ignored(self):
        for flag in ('draft','prerelease'):
            data=release();data[flag]=True;self.assertIsNone(u.release_info(data,'TommiLin/Offline-Book-Converter','1.3.0'))
    def test_missing_assets(self):
        data=release();data['assets'].pop()
        with self.assertRaises(u.UpdateError):u.release_info(data,'TommiLin/Offline-Book-Converter','1.3.0')
    def test_wrong_asset_repository(self):
        data=release();data['assets'][0]['browser_download_url']='https://github.com/other/repo/releases/download/v1.4.0/setup.exe'
        with self.assertRaises(u.UpdateError):u.release_info(data,'TommiLin/Offline-Book-Converter','1.3.0')
    def test_insecure_and_external_urls(self):
        for url in ('http://github.com/TommiLin/Offline-Book-Converter/releases/download/a/b','https://github.com.evil.test/a','https://github.com@evil.test/a'):
            with self.assertRaises(u.UpdateError):u.github_url(url,'TommiLin/Offline-Book-Converter')
    def test_check_latest(self):
        with patch.object(u,'read_bytes',return_value=json.dumps(release()).encode()) as read:
            self.assertEqual(u.check_latest('1.3.0')['version'],'1.4.0')
            read.assert_called_once_with('https://api.github.com/repos/'+u.REPOSITORY+'/releases/latest',2*1024*1024)
    def test_http_and_offline_errors(self):
        for error in (urllib.error.HTTPError('url',404,'Not found',{},None),urllib.error.HTTPError('url',403,'Forbidden',{},None),urllib.error.URLError('offline')):
            with patch.object(u,'read_bytes',side_effect=error),self.assertRaises(u.UpdateError):u.check_latest('1.3.0')
    def test_download_and_checksum(self):
        info=self.info();data=b'exe';checksum=(hashlib.sha256(data).hexdigest()+'  '+info['name']+'\n').encode();events=[]
        with patch.object(u,'read_bytes',return_value=checksum),patch.object(u,'request',return_value=Response(data)):
            output=u.download_update(info,self.folder,lambda count,total:events.append((count,total)))
        self.assertEqual(output.read_bytes(),data);self.assertEqual(events,[(3,3)]);self.assertFalse(list(self.folder.glob('*.part')))
    def test_checksum_mismatch_discards_download(self):
        info=self.info();checksum=('0'*64+'  '+info['name']).encode()
        with patch.object(u,'read_bytes',return_value=checksum),patch.object(u,'request',return_value=Response(b'bad')),self.assertRaises(u.UpdateError):
            u.download_update(info,self.folder)
        self.assertFalse(list(self.folder.iterdir()))
    def test_truncated_download_discards_download(self):
        info=self.info();checksum=(hashlib.sha256(b'exe').hexdigest()+'  '+info['name']).encode()
        with patch.object(u,'read_bytes',return_value=checksum),patch.object(u,'request',return_value=Response(b'exe',100)),self.assertRaises(u.UpdateError):
            u.download_update(info,self.folder)
        self.assertFalse(list(self.folder.iterdir()))
    def test_duplicate_checksums_rejected(self):
        line='0'*64+'  setup.exe\n'
        with self.assertRaises(u.UpdateError):u.checksum_for((line*2).encode(),'setup.exe')
    def test_path_traversal_filename_rejected(self):
        info=self.info();info['name']='../unsafe.exe'
        with self.assertRaises(u.UpdateError):u.download_update(info,self.folder)

if __name__=='__main__':unittest.main()
