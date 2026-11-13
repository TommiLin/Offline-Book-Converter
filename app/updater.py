"""Opt-in GitHub Releases updater. Standard library only; no tokens stored."""
import hashlib,json,re,urllib.request,urllib.error
from pathlib import Path
from urllib.parse import urlsplit

class UpdateError(Exception):pass
class NoPublishedRelease(UpdateError):pass
REPOSITORY='TommiLin/Offline-Book-Converter'

def version_tuple(value):
    match=re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)',value or '')
    if not match:raise UpdateError('Release versions must use vMAJOR.MINOR.PATCH, for example v1.4.0.')
    return tuple(map(int,match.groups()))

def github_url(url,repository=None):
    repository=REPOSITORY
    parts=urlsplit(url)
    if parts.scheme!='https' or parts.hostname!='github.com' or parts.username or parts.password or parts.port:
        raise UpdateError('The release asset is not a GitHub HTTPS download.')
    if repository and not parts.path.lower().startswith('/'+repository.lower()+'/releases/download/'):
        raise UpdateError('The release download belongs to a different repository.')
    return url

def request(url):
    return urllib.request.urlopen(urllib.request.Request(url,headers={
        'User-Agent':'OfflineBookConverter-Updater','Accept':'application/vnd.github+json' if 'api.github.com/' in url else 'application/octet-stream',
        'X-GitHub-Api-Version':'2022-11-28'}),timeout=25)

def read_bytes(url,limit):
    with request(url) as response:
        data=response.read(limit+1)
    if len(data)>limit:raise UpdateError('GitHub response exceeded the allowed size.')
    return data

def release_info(data,repository,current):
    if repository!=REPOSITORY:raise UpdateError('Updates must use the official repository.')
    if data.get('draft') or data.get('prerelease'):return None
    version=data.get('tag_name','');version_tuple(version)
    if version_tuple(version)<=version_tuple(current):return None
    version=version.lstrip('v')
    installer='OfflineBookConverter-Setup-'+version+'.exe'
    assets={a.get('name'):a for a in data.get('assets',[]) if a.get('state','uploaded')=='uploaded'}
    if installer not in assets or 'SHA256SUMS.txt' not in assets:
        raise UpdateError('The latest release is incomplete: installer or SHA256SUMS.txt is missing.')
    url=github_url(assets[installer].get('browser_download_url',''),repository)
    sums=github_url(assets['SHA256SUMS.txt'].get('browser_download_url',''),repository)
    return {'version':version,'name':installer,'url':url,'checksums_url':sums,'size':assets[installer].get('size',0),'repository':repository}

def check_latest(current):
    repository=REPOSITORY
    try:
        raw=read_bytes('https://api.github.com/repos/'+repository+'/releases/latest',2*1024*1024)
        return release_info(json.loads(raw.decode('utf-8')),repository,current)
    except urllib.error.HTTPError as error:
        if error.code==404:raise NoPublishedRelease('No update release has been published yet.') from error
        if error.code==403:raise UpdateError('GitHub refused this request or its request limit was reached. Try again later.') from error
        raise UpdateError('GitHub returned HTTP '+str(error.code)+'.') from error
    except (urllib.error.URLError,TimeoutError,OSError) as error:
        raise UpdateError('Could not reach GitHub. Check your connection and try again. Offline conversion is still available.') from error

def checksum_for(data,name):
    matches=[]
    for line in data.decode('utf-8-sig').splitlines():
        match=re.fullmatch(r'([0-9a-fA-F]{64})\s+\*?(.+)',line)
        if match and match[2]==name:matches.append(match[1].lower())
    if len(matches)!=1:raise UpdateError('Installer checksum is missing or duplicated in SHA256SUMS.txt.')
    return matches[0]

def download_update(info,folder,progress=lambda current,total:None):
    if info.get('repository')!=REPOSITORY:raise UpdateError('Updates must use the official repository.')
    name=info['name']
    if not re.fullmatch(r'OfflineBookConverter-Setup-\d+\.\d+\.\d+\.exe',name):raise UpdateError('Unexpected installer filename.')
    url=github_url(info['url'],info['repository']);sums=github_url(info['checksums_url'],info['repository'])
    expected=checksum_for(read_bytes(sums,1024*1024),name)
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    target=folder/name;partial=folder/(name+'.part');digest=hashlib.sha256();count=0
    try:
        with request(url) as response,partial.open('wb') as output:
            final=urlsplit(response.geturl())
            if final.scheme!='https' or not (final.hostname=='github.com' or (final.hostname or '').endswith('.githubusercontent.com')):
                raise UpdateError('Unexpected GitHub download redirect.')
            total=int(response.headers.get('Content-Length',info.get('size',0)) or 0)
            if total>100*1024*1024:raise UpdateError('Installer is unexpectedly large.')
            while True:
                block=response.read(65536)
                if not block:break
                count+=len(block)
                if count>100*1024*1024:raise UpdateError('Installer exceeded the size limit.')
                digest.update(block);output.write(block);progress(count,total)
        if not count or (total and count!=total):raise UpdateError('Download was incomplete. Try again.')
        if digest.hexdigest()!=expected:raise UpdateError('Installer checksum did not match. The download was discarded.')
        partial.replace(target);return target
    finally:
        if partial.exists():partial.unlink()
