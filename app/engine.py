"""Offline converter worker. Executed with calibre-debug, not system Python."""
import sys, os, json, tempfile, uuid, re, zipfile, hashlib
from pathlib import Path
from urllib.parse import urlsplit, unquote
from lxml import etree

# Python 3.13's Windows 0700 temporary directory ACL can reject restricted users.
_mkdir = os.mkdir
def mkdir(path, mode=0o777, *, dir_fd=None):
    return _mkdir(path, 0o777, dir_fd=dir_fd)
os.mkdir = mkdir

N = {'o':'http://www.idpf.org/2007/opf', 'n':'http://www.daisy.org/z3986/2005/ncx/'}
X = 'http://www.w3.org/1999/xhtml'
def tag(name): return '{%s}%s' % (X,name)
def text(node): return ''.join(node.itertext()).strip()
def progress(percent, stage):
    print('PROGRESS_JSON:'+json.dumps({'percent':percent,'stage':stage}),flush=True)
def convert(src, dst, opts=()):
    from calibre.ebooks.conversion.cli import main
    previous=os.getcwd()
    try:
        main(['ebook-convert', str(src), str(dst), *opts])
    finally: os.chdir(previous)

def local_target(base, href, root):
    url=urlsplit(href)
    if url.scheme or url.netloc: raise ValueError('External navigation target: '+href)
    path=(base.parent / unquote(url.path)).resolve() if url.path else base.resolve()
    if not path.is_relative_to(root.resolve()): raise ValueError('Target outside book: '+href)
    return path,unquote(url.fragment)

def parse(path): return etree.parse(str(path),etree.XMLParser(resolve_entities=False,no_network=True))
def check_links(base, entries, root):
    cache={}
    for label,href,depth,group in entries:
        path,anchor=local_target(base,href,root)
        if not path.is_file(): raise ValueError('Missing target for '+label+': '+href)
        if anchor:
            if path not in cache: cache[path]=parse(path)
            if not cache[path].xpath('//*[@id=$a or @name=$a]',a=anchor):
                raise ValueError('Missing anchor for '+label+': '+href)

def fix_book(opf, chapter_prefix=True):
    root=opf.parent; package=parse(opf)
    ncx_item=package.xpath('//o:item[@media-type="application/x-dtbncx+xml"]',namespaces=N)
    if not ncx_item:
        return [],['No chapter navigation in source; converted without contents repair.'],None
    ncx_path=root/ncx_item[0].get('href'); ncx=parse(ncx_path)
    points=ncx.xpath('//n:navPoint',namespaces=N)
    if not points:
        return [],['Source has no chapter entries; converted as a continuous book without contents repair.'],None
    entries=[]
    for p in points:
        label=text(p.find('n:navLabel/n:text',N))
        href=p.find('n:content',N).get('src')
        dest,frag=local_target(ncx_path,href,root)
        rel=dest.relative_to(root).as_posix()+('#'+frag if frag else '')
        entries.append((label,rel,len(p.xpath('ancestor::n:navPoint',namespaces=N)),bool(p.findall('n:navPoint',N))))
    check_links(opf,entries,root)
    warnings=[]
    # Remove the old inline TOC only when its tail consists entirely of navigation.
    # Otherwise keep its contents and strip blockquote wrappers in that TOC region.
    refs=package.xpath('//o:guide/o:reference[@type="toc"]',namespaces=N)
    for ref in refs:
        old,anchor=local_target(opf,ref.get('href'),root)
        if not old.is_file():continue
        doc=parse(old)
        found=doc.xpath('//*[@id=$a or @name=$a]',a=anchor) if anchor else doc.xpath('//*[local-name()="body"]')
        if found:
            h=found[0]
            body=doc.xpath('//*[local-name()="body"]')[0]
            if h is body: region=list(body)
            else:
                while h.getparent() is not body and h.getparent() is not None: h=h.getparent()
                region=list(body)[list(body).index(h):] if h.getparent() is body else []
            nav_labels={e[0] for e in entries}
            region_links=[a for e in region for a in e.xpath('.//*[local-name()="a"][@href]')]
            leftover=''.join(''.join(e.itertext()) for e in region)
            for a in region_links:leftover=leftover.replace(text(a),'',1)
            leftover=re.sub(r'\s+','',leftover).lower()
            pure_nav=bool(region_links) and all(text(a).lstrip('— ') in nav_labels for a in region_links) and leftover in ('','tableofcontents','contents','оглавление')
            if pure_nav:
                # Leave all old IDs addressable without keeping a duplicate contents list.
                ids=[e.get('id') or e.get('name') for top in region for e in top.iter() if e.get('id') or e.get('name')]
                for element in region:body.remove(element)
                for old_id in ids:etree.SubElement(body,tag('a'),id=old_id)
                moved=etree.SubElement(body,tag('p'));moved.text='Contents is available from the book navigation menu.'
                region=[]
            # If mixed with prose, preserve the original content and neutralize wrappers.
            for element in region:
                for b in list(element.xpath('.//*[local-name()="blockquote"]'))[::-1]:
                    b.tag=tag('div'); b.attrib.pop('class',None); b.set('style','margin:0;padding:0;text-indent:0')
                if etree.QName(element).localname=='blockquote':
                    element.tag=tag('div'); element.attrib.pop('class',None); element.set('style','margin:0;padding:0;text-indent:0')
            doc.write(str(old),encoding='utf-8',xml_declaration=True)
        ref.getparent().remove(ref)
    name='clean-toc-'+uuid.uuid4().hex[:8]+'.xhtml'
    html=etree.Element(tag('html'),nsmap={None:X});head=etree.SubElement(html,tag('head'))
    etree.SubElement(head,tag('title')).text='Contents'
    body=etree.SubElement(html,tag('body'));etree.SubElement(body,tag('h1')).text='Contents'
    for i,(label,href,depth,group) in enumerate(entries):
        p=etree.SubElement(body,tag('p'),id='entry-'+str(i),style='margin-left:0;margin-right:0;text-indent:0;margin-top:%sem;margin-bottom:0.35em'%('1.2' if group else '0.3'))
        container=etree.SubElement(p,tag('b')) if group else p
        a=etree.SubElement(container,tag('a'),href=href)
        a.text=('— ' if chapter_prefix and not group and re.match(r'^(глава|chapter)\b',label,re.I) else '')+label
    etree.ElementTree(html).write(str(root/name),encoding='utf-8',xml_declaration=True)
    manifest=package.find('o:manifest',N);spine=package.find('o:spine',N)
    item_id='clean-toc-'+uuid.uuid4().hex[:8]
    etree.SubElement(manifest,'{%s}item'%N['o'],id=item_id,href=name,attrib={'media-type':'application/xhtml+xml'})
    etree.SubElement(spine,'{%s}itemref'%N['o'],idref=item_id)
    guide=package.find('o:guide',N)
    if guide is None:guide=etree.SubElement(package.getroot(),'{%s}guide'%N['o'])
    etree.SubElement(guide,'{%s}reference'%N['o'],type='toc',title='Contents',href=name)
    package.write(str(opf),encoding='utf-8',xml_declaration=True)
    if not any(e[3] for e in entries):warnings.append('Source navigation has no hierarchy. Group headings cannot be inferred reliably; all entries were preserved.')
    return entries,warnings,name

def verify_result(output, expected):
    with tempfile.TemporaryDirectory(prefix='verify-') as temp:
        folder=Path(temp)
        if output.suffix=='.mobi':
            from calibre.ebooks.mobi.reader.mobi6 import MobiReader
            cache={};reader=MobiReader(str(output));reader.extract_content(str(folder),cache)
            for filename,tree in cache.items():
                Path(filename).write_bytes(etree.tostring(tree,encoding='utf-8',xml_declaration=True))
            opf=folder/'index.opf'
        elif output.suffix=='.epub':
            with zipfile.ZipFile(output) as z:z.extractall(folder/'unpacked')
            folder=folder/'unpacked';opf=next(folder.rglob('*.opf'))
        else:
            convert(output,folder/'book.epub', ['--no-chapters-in-toc','--chapter','/'])
            with zipfile.ZipFile(folder/'book.epub') as z:z.extractall(folder/'unpacked')
            folder=folder/'unpacked';opf=next(folder.rglob('*.opf'))
        package=parse(opf)
        if not expected:
            manifest={item.get('id'):item.get('href') for item in package.xpath('//o:manifest/o:item',namespaces=N)}
            checked=characters=images=0
            for item in package.xpath('//o:spine/o:itemref',namespaces=N):
                href=manifest.get(item.get('idref'))
                if not href:raise ValueError('Output spine references a missing document.')
                path,_=local_target(opf,href,folder)
                if not path.is_file():raise ValueError('Output reading document is missing.')
                doc=parse(path);bodies=doc.xpath('//*[local-name()="body"]')
                if not bodies:raise ValueError('Output reading document has no body.')
                checked+=1
                characters+=sum(len(re.sub(r'\s+','',text(body))) for body in bodies)
                images+=len(doc.xpath('//*[local-name()="img" or local-name()="image"]'))
            if not checked or not (characters or images):raise ValueError('Output has no readable content.')
            if output.suffix=='.mobi':
                import struct
                raw=output.read_bytes();offset=struct.unpack_from('>I',raw,78)[0]
                if struct.unpack_from('>I',raw,offset+36)[0]!=6:raise ValueError('Output is not legacy MOBI 6.')
            return {'verified_links':0,'output_reopened':True,'contents_check':'not_applicable_no_source_chapters','spine_documents_checked':checked,'text_characters':characters}
        refs=package.xpath('//o:reference[@type="toc"]',namespaces=N)
        if not refs: raise ValueError('Output has no Go To → Contents destination.')
        path,anchor=local_target(opf,refs[0].get('href'),folder)
        doc=parse(path); nodes=doc.xpath('//*[@id=$a or @name=$a]',a=anchor) if anchor else []
        if nodes:
            h=nodes[0];body=doc.xpath('//*[local-name()="body"]')[0]
            while h.getparent() is not body: h=h.getparent()
            region=list(body)[list(body).index(h):]
        else:region=[doc.getroot()]
        links=[a for e in region for a in e.xpath('.//*[local-name()="a"][@href]')]
        labels=[text(a).lstrip('— ') for a in links]
        if labels != [e[0] for e in expected]:raise ValueError('Output contents entries differ from the source navigation.')
        check_links(path,[(text(a),a.get('href'),0,False) for a in links],folder)
        if any(e.xpath('.//*[local-name()="blockquote"]') for e in region):raise ValueError('Output contents contains blockquote indentation.')
        for entry,a in zip(expected,links):
            if entry[3] and not a.xpath('ancestor::*[local-name()="b" or local-name()="strong" or contains(concat(" ",normalize-space(@class)," ")," bold ")] | .//*[local-name()="b" or local-name()="strong" or contains(concat(" ",normalize-space(@class)," ")," bold ")]'):
                # EPUB preserves bold through CSS; MOBI uses explicit b tags.
                if output.suffix=='.mobi':raise ValueError('Group heading lost bold formatting: '+entry[0])
        if output.suffix=='.mobi':
            import struct
            raw=output.read_bytes();offset=struct.unpack_from('>I',raw,78)[0]
            if struct.unpack_from('>I',raw,offset+36)[0]!=6:raise ValueError('Output is not legacy MOBI 6.')
        return {'verified_links':len(links),'toc_blockquotes':0,'output_reopened':True}

def run(job):
    source=Path(job['input']).resolve(); output=Path(job['output']).resolve()
    if source==output or output.exists():raise ValueError('Output already exists. Choose a new output name.')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='book-') as temp:
        folder=Path(temp);oeb=folder/'oeb'
        progress(2,'Reading source book')
        convert(source,oeb,['--chapter','/','--no-chapters-in-toc'])
        progress(30,'Repairing contents and checking source links')
        opf=next(oeb.glob('*.opf'))
        entries,warnings,_=fix_book(opf,job.get('chapter_prefix',True))
        candidate=folder/('result'+output.suffix)
        options=['--no-chapters-in-toc','--chapter','/','--chapter-mark','none']
        if output.suffix=='.mobi':options+=['--mobi-file-type','old','--output-profile','kindle','--no-inline-toc']
        elif output.suffix=='.azw3':options+=['--output-profile','kindle','--no-inline-toc']
        progress(40,'Building output book')
        convert(opf,candidate,options)
        progress(80,'Reopening output and verifying navigation')
        verification=verify_result(candidate,entries)
        progress(96,'Saving verified book and report')
        report={'input':str(source),'output':str(output),'entries':len(entries),'contents_repaired':bool(entries),'bold_group_headings':sum(e[3] for e in entries),'warnings':warnings,'verification':verification,'device_tested':False,'sha256':hashlib.sha256(candidate.read_bytes()).hexdigest()}
        import shutil
        # Exclusive creation prevents accidental overwrite, including concurrent jobs.
        with candidate.open('rb') as src,output.open('xb') as dst:shutil.copyfileobj(src,dst)
        report_path=Path(job.get('report',str(output.parent/'Diagnostics'/'report.json')))
        report_path.parent.mkdir(parents=True,exist_ok=True)
        report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        progress(100,'Complete')
        return report

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(line_buffering=True)
    import calibre.ptempfile as pt
    temp_root=Path(__file__).resolve().parent/'.work'
    temp_root.mkdir(parents=True,exist_ok=True);pt._base_dir=str(temp_root);tempfile.tempdir=str(temp_root)
    try:
        job=json.loads(Path(sys.argv[-1]).read_text(encoding='utf-8'))
        print('RESULT_JSON:'+json.dumps(run(job),ensure_ascii=True))
    except Exception:
        import traceback
        traceback.print_exc();sys.exit(1)

