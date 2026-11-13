import os,sys,runpy,time,unittest,uuid,shutil
from pathlib import Path
from unittest.mock import patch

@unittest.skipUnless(os.name=='nt','Windows GUI integration tests')
class UpdateUITests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]
        self.module=runpy.run_path(str(root/'app/app.pyw'),run_name='test')
        self.app=self.module['App']();self.app.root.update()
        self.work=root/'tests/.test-work'/uuid.uuid4().hex;self.work.mkdir(parents=True)
    def tearDown(self):
        try:self.app.close()
        except Exception:pass
        shutil.rmtree(self.work)
    def pump(self,condition):
        end=time.monotonic()+4
        while not condition():
            self.app.root.update();time.sleep(.01)
            if time.monotonic()>end:self.fail('Update UI timed out')
    def test_no_repository_settings(self):
        self.assertFalse(hasattr(self.app,'update_settings'))
        self.assertFalse(hasattr(self.app,'configure_updates'))
    def test_unpublished_is_information(self):
        from updater import NoPublishedRelease
        with patch('updater.check_latest',side_effect=NoPublishedRelease()),patch('tkinter.messagebox.showinfo') as info,patch('tkinter.messagebox.showerror') as error:
            self.app.check_updates();self.pump(lambda:not self.app.updating)
            info.assert_called_once();error.assert_not_called()
        self.assertEqual(str(self.app.go['state']),'normal')
    def test_no_update_restores_buttons(self):
        with patch('updater.check_latest',return_value=None),patch('tkinter.messagebox.showinfo'):
            self.app.check_updates();self.pump(lambda:not self.app.updating)
        self.assertIn('latest stable',self.app.status.get());self.assertEqual(str(self.app.go['state']),'normal')
    def test_offline_restores_conversion(self):
        with patch('updater.check_latest',side_effect=OSError('offline')),patch('tkinter.messagebox.showerror'):
            self.app.check_updates();self.pump(lambda:not self.app.updating)
        self.assertIn('Offline conversion is available',self.app.status.get());self.assertEqual(str(self.app.go['state']),'normal')
    def test_download_requires_confirmation_before_install(self):
        installer=self.work/'setup.exe'
        def download(info,folder,progress):
            installer.write_bytes(b'test only');progress(9,9);return installer
        with patch('updater.check_latest',return_value={'version':'1.4.0'}),patch('updater.download_update',side_effect=download),patch('tkinter.messagebox.askyesno',side_effect=[True,False]) as dialog,patch('subprocess.Popen') as launch:
            self.app.check_updates();self.pump(lambda:'checksum verified' in self.app.status.get().lower() or 'SHA-256 verified' in self.app.status.get())
            self.assertEqual(dialog.call_count,2);launch.assert_not_called()
        self.assertFalse(self.app.updating)
    def test_confirmed_install_hands_off_current_folder(self):
        installer=self.work/'setup.exe';installer.write_bytes(b'test only')
        (self.work/'OfflineBookConverter.exe').write_bytes(b'test launcher')
        with patch.dict(self.app.poll.__globals__,{'HERE':self.work}),patch('tkinter.messagebox.askyesno',return_value=True),patch('subprocess.Popen') as launch:
            self.app.messages.put(('update_ready',str(installer)));self.app.poll()
            arguments=launch.call_args.args[0]
            self.assertEqual(arguments[1],'/update-dir');self.assertEqual(Path(arguments[2]),self.work)

if __name__=='__main__':unittest.main()
