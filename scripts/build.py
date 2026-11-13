"""Windows build with the system .NET Framework C# compiler. No pip required."""
import argparse,hashlib,json,os,re,shutil,subprocess,sys,uuid,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP_FILES=['app.pyw','engine.py','file_drop.py','updater.py','update_config.json','app.ico','Start.cmd','Uninstall.ps1','README.txt','TESTED.txt','THIRD_PARTY.txt']

def main():
    argparse.ArgumentParser(description='Build the official Offline Book Converter.').parse_args()
    sys.path.insert(0,str(ROOT/'app'));from updater import REPOSITORY,version_tuple
    version=json.loads((ROOT/'app/update_config.json').read_text(encoding='utf-8'))['version'];version_tuple(version)
    config={'version':version}
    csc=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    if not csc.is_file():raise SystemExit('Windows with .NET Framework 4.x is required to build the installer.')
    dist=ROOT/'dist';dist.mkdir(exist_ok=True)
    build=ROOT/'build';build.mkdir(exist_ok=True);work=build/('run-'+uuid.uuid4().hex);work.mkdir()
    try:
        stage=work/'app';stage.mkdir()
        for name in APP_FILES:shutil.copyfile(ROOT/'app'/name,stage/name)
        shutil.copytree(ROOT/'app/vendor',stage/'vendor',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copyfile(ROOT/'LICENSE',stage/'LICENSE.txt')
        (stage/'update_config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
        template=(ROOT/'installer/Launcher.cs').read_text(encoding='utf-8-sig')
        template=template.replace('__ASSEMBLY_VERSION__',version+'.0').replace('__VERSION__',version)
        cs=work/'Launcher.cs';cs.write_text(template,encoding='utf-8-sig')
        references=['/r:'+name for name in ['System.Windows.Forms.dll','System.Drawing.dll','System.IO.Compression.dll','Microsoft.CSharp.dll']]
        common=[str(csc),'/nologo','/target:winexe','/win32icon:'+str(stage/'app.ico'),*references]
        subprocess.run([*common,'/out:'+str(stage/'OfflineBookConverter.exe'),str(cs)],check=True)
        manifest=[p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()]+['installed_files.json']
        (stage/'installed_files.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        payload=work/'payload.zip'
        with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(stage.rglob('*')):
                if p.is_file():z.write(p,p.relative_to(stage).as_posix())
        installer=dist/('OfflineBookConverter-Setup-'+version+'.exe')
        subprocess.run([*common,'/define:SETUP','/resource:'+str(payload)+',payload.zip','/out:'+str(installer),str(cs)],check=True)
        portable=dist/('OfflineBookConverter-Portable-'+version+'.zip')
        with zipfile.ZipFile(portable,'w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(stage.rglob('*')):
                if p.is_file():z.write(p,'OfflineBookConverter/'+p.relative_to(stage).as_posix())
        source=dist/('OfflineBookConverter-Source-'+version+'.zip')
        include=['app','installer','scripts','tests','.github']
        with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED) as z:
            for directory in include:
                for p in sorted((ROOT/directory).rglob('*')):
                    if directory=='app' and p.name not in APP_FILES and 'vendor' not in p.relative_to(ROOT/'app').parts:continue
                    if p.is_file() and '__pycache__' not in p.parts and p.name not in ('settings.json',) and not any(part.startswith('.') and part not in ('.github',) for part in p.relative_to(ROOT/directory).parts):
                        z.write(p,p.relative_to(ROOT).as_posix())
            for name in ['README.md','LICENSE','.gitignore','CHANGELOG.md','BUILD.md','SECURITY.md']:
                z.write(ROOT/name,name)
        files=[installer,portable,source]
        (dist/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files),encoding='utf-8')
        print('Built version '+version+'; update repository: '+REPOSITORY)
        for p in files:print(p)
    finally:
        # Only remove this build's verified temporary directory.
        if work.resolve().parent==build.resolve():shutil.rmtree(work)
if __name__=='__main__':main()
