"""Run with calibre-debug -e tests/test_chapterless.py (uses bundled lxml)."""
import sys,unittest,uuid,shutil,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
try:
    import engine
    import calibre.ptempfile as pt
except ImportError:raise unittest.SkipTest('Run engine regression tests with calibre-debug -e tests/test_chapterless.py')
BASE=ROOT/'tests/.test-work';BASE.mkdir(parents=True,exist_ok=True)
pt._base_dir=str(BASE);tempfile.tempdir=str(BASE)

class ChapterlessTests(unittest.TestCase):
    def setUp(self):self.folder=BASE/uuid.uuid4().hex;self.folder.mkdir()
    def tearDown(self):shutil.rmtree(self.folder)
    def source(self,ncx=None):
        body='<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Continuous story</title></head><body><p>A continuous story has no chapters.</p><p>Its last sentence must survive.</p></body></html>'
        (self.folder/'book.xhtml').write_text(body,encoding='utf-8')
        nav='<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>' if ncx is not None else ''
        opf=self.folder/'book.opf'
        opf.write_text('''<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Continuous story</dc:title><dc:creator>Test</dc:creator><dc:language>en</dc:language><dc:identifier id="id">chapterless-fixture</dc:identifier></metadata><manifest><item id="body" href="book.xhtml" media-type="application/xhtml+xml"/>'''+nav+'''</manifest><spine'''+(' toc="ncx"' if ncx is not None else '')+'''><itemref idref="body"/></spine></package>''',encoding='utf-8')
        if ncx is not None:(self.folder/'toc.ncx').write_text(ncx,encoding='utf-8')
        return opf
    def test_missing_navigation_is_not_an_error_and_creates_no_toc(self):
        opf=self.source();original=opf.read_bytes();entries,notes,name=engine.fix_book(opf)
        self.assertEqual(entries,[]);self.assertIsNone(name);self.assertTrue(notes);self.assertEqual(opf.read_bytes(),original)
        self.assertFalse(list(self.folder.glob('clean-toc-*')))
    def test_empty_navigation_is_not_an_error(self):
        opf=self.source('<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/"><navMap/></ncx>')
        original=opf.read_bytes();entries,notes,name=engine.fix_book(opf)
        self.assertFalse(entries);self.assertIsNone(name);self.assertEqual(opf.read_bytes(),original)
    def test_broken_navigation_is_still_an_error(self):
        opf=self.source('<ncx><broken>')
        with self.assertRaises(Exception):engine.fix_book(opf)
    def test_unresolvable_chapter_link_is_still_an_error(self):
        opf=self.source('<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/"><navMap><navPoint id="x"><navLabel><text>Chapter</text></navLabel><content src="missing.xhtml"/></navPoint></navMap></ncx>')
        with self.assertRaisesRegex(ValueError,'Missing target'):engine.fix_book(opf)
    def test_chapterless_conversion_all_output_formats(self):
        opf=self.source('<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/"><head/><docTitle><text>Continuous story</text></docTitle><navMap/></ncx>')
        epub=self.folder/'source.epub'
        with zipfile.ZipFile(epub,'w') as z:
            z.writestr('mimetype','application/epub+zip')
            z.writestr('META-INF/container.xml','<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="book.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
            for name in ('book.opf','book.xhtml','toc.ncx'):z.write(self.folder/name,name)
        for suffix in ('.mobi','.epub','.azw3'):
            with self.subTest(format=suffix):
                output=self.folder/('out'+suffix);report=engine.run({'input':str(epub),'output':str(output)})
                self.assertTrue(output.is_file());self.assertTrue(report['verification']['output_reopened'])
                if not report['entries']:
                    self.assertGreater(report['verification']['text_characters'],30)
    def test_readable_content_check_rejects_empty_output(self):
        opf=self.source();(self.folder/'book.xhtml').write_text('<html xmlns="http://www.w3.org/1999/xhtml"><head/><body/></html>')
        epub=self.folder/'empty.epub'
        with zipfile.ZipFile(epub,'w') as z:
            z.writestr('mimetype','application/epub+zip');z.write(opf,'book.opf');z.write(self.folder/'book.xhtml','book.xhtml')
        with self.assertRaisesRegex(ValueError,'no readable content'):engine.verify_result(epub,[])

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ChapterlessTests))
    sys.exit(0 if result.wasSuccessful() else 1)
