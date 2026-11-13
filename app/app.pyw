from updater import REPOSITORY, NoPublishedRelease
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
import os,subprocess,threading,queue,json,tempfile,shutil
import uuid,time,re,gc
from contextlib import contextmanager

HERE=Path(__file__).resolve().parent
import sys
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from file_drop import create_root
SUPPORTED={'.mobi','.epub','.fb2','.azw3','.docx','.html','.htm','.txt','.rtf','.lit','.pdb'}
CONFIG=json.loads((HERE/'update_config.json').read_text(encoding='utf-8'))
VERSION=CONFIG['version']
def reserve_output_folder(target,stem):
    name=stem[:120].rstrip(' .')+'_clean'
    n=1
    while True:
        folder=target/(name if n==1 else f'{name}_{n}')
        try:folder.mkdir();return folder
        except FileExistsError:n+=1
@contextmanager
def job_folder():
    p=HERE/'.work'/('job-'+uuid.uuid4().hex)
    p.mkdir(parents=True)
    try:yield p
    finally:shutil.rmtree(p,ignore_errors=True)
FORMATS={'Kindle 4 — MOBI (.mobi)':'.mobi','EPUB (.epub)':'.epub','Kindle — AZW3 (.azw3)':'.azw3'}
class App:
    def __init__(self):
        gc.disable();gc.collect();self.last_gc=time.monotonic()
        if os.name=='nt':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('OfflineBookConverter.Desktop')
        self.root=create_root();self.root.title('Offline Book Converter '+VERSION);self.root.geometry('860x780');self.root.minsize(800,720)
        if (HERE/'app.ico').is_file():self.root.iconbitmap(str(HERE/'app.ico'))
        self.files=[];self.messages=queue.Queue();self.busy=False
        self.updating=False
        self.started=0;self.last_activity=0;self.current_percent=0;self.book_index=0;self.book_count=1
        self.format=tk.StringVar(value=next(iter(FORMATS)));self.output=tk.StringVar(value=str(Path.home()/'Documents'/'Converted Books'))
        self.chapter=tk.BooleanVar(value=True)
        frame=ttk.Frame(self.root,padding=22);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Offline Book Converter',font=('Segoe UI',21,'bold')).pack(anchor='w')
        ttk.Label(frame,text='Drop books anywhere in this window, or use Add books.').pack(anchor='w',pady=(4,18))
        row=ttk.Frame(frame);row.pack(fill='x')
        self.add=ttk.Button(row,text='Add books…',command=self.add_files);self.add.pack(side='left')
        self.clear=ttk.Button(row,text='Clear list',command=self.clear_files);self.clear.pack(side='left',padx=8)
        ttk.Label(row,text='MOBI · EPUB · FB2 · AZW3 · DOCX · HTML · TXT').pack(side='right')
        self.list=tk.Listbox(frame,height=5,font=('Segoe UI',10));self.list.pack(fill='both',expand=True,pady=10)
        options=ttk.Frame(frame);options.pack(fill='x',pady=8)
        ttk.Label(options,text='Output format').grid(row=0,column=0,sticky='w')
        self.combo=ttk.Combobox(options,textvariable=self.format,values=list(FORMATS),state='readonly',width=32);self.combo.grid(row=0,column=1,padx=12,sticky='w')
        ttk.Checkbutton(options,text='Mark chapter entries with a dash',variable=self.chapter).grid(row=1,column=1,pady=8,sticky='w')
        ttk.Label(frame,text='Contents repair is always on: bold group headings, no cascading indentation.').pack(anchor='w')
        out=ttk.Frame(frame);out.pack(fill='x',pady=12)
        ttk.Label(out,text='Save to').pack(side='left');ttk.Entry(out,textvariable=self.output).pack(side='left',fill='x',expand=True,padx=10)
        ttk.Button(out,text='Browse…',command=self.browse).pack(side='right')
        row=ttk.Frame(frame);row.pack(fill='x')
        self.go=ttk.Button(row,text='Convert & repair',command=self.start);self.go.pack(side='left')
        ttk.Button(row,text='Open output folder',command=self.open_folder).pack(side='left',padx=10)
        self.update_button=ttk.Button(row,text='Check for updates',command=self.check_updates);self.update_button.pack(side='right')
        self.status=tk.StringVar(value='Ready. Requires Calibre. No internet connection needed.')
        ttk.Label(frame,textvariable=self.status,wraplength=750).pack(anchor='w',pady=10)
        self.stage=tk.StringVar(value='Current book: waiting')
        ttk.Label(frame,textvariable=self.stage).pack(anchor='w')
        self.book_progress=ttk.Progressbar(frame,maximum=100,mode='determinate');self.book_progress.pack(fill='x',pady=(4,8))
        self.batch_label=tk.StringVar(value='Batch: 0 / 0 books')
        ttk.Label(frame,textvariable=self.batch_label).pack(anchor='w')
        self.batch_progress=ttk.Progressbar(frame,maximum=100,mode='determinate');self.batch_progress.pack(fill='x',pady=(4,8))
        activity=ttk.Frame(frame);activity.pack(fill='x',pady=(0,8))
        self.pulse=ttk.Progressbar(activity,mode='indeterminate',length=90);self.pulse.pack(side='left')
        self.elapsed=tk.StringVar(value='Ready')
        ttk.Label(activity,textvariable=self.elapsed).pack(side='left',padx=10)
        self.log=tk.Text(frame,height=6,font=('Consolas',9),state='disabled');self.log.pack(fill='x')
        self.log.tag_configure('success',foreground='#24704a')
        self.log.tag_configure('information',foreground='#60666e')
        self.log.tag_configure('error',foreground='#b42318')
        self.root.protocol('WM_DELETE_WINDOW',self.close);self.poll_id=self.root.after(150,self.poll)
        self.drop=None
        if os.name=='nt':
            try:
                from file_drop import enable
                self.drop=enable(self.root,self.receive_files)
            except Exception as e:self.messages.put(('log','Drag and drop unavailable: '+str(e)))
    def add_files(self):
        if self.busy:return
        self.receive_files(filedialog.askopenfilenames(filetypes=[('Books','*.mobi *.epub *.fb2 *.azw3 *.docx *.html *.htm *.txt *.rtf *.lit *.pdb'),('All files','*.*')]))
    def receive_files(self,paths):
        if self.busy or self.updating:
            self.messages.put(('log','Wait for the current batch to finish before adding books.'));return
        added=skipped=0;existing={os.path.normcase(p) for p in self.files}
        for raw in paths:
            path=Path(raw).resolve();key=os.path.normcase(str(path))
            if not path.is_file() or path.suffix.lower() not in SUPPORTED:skipped+=1;continue
            if key in existing:continue
            existing.add(key);self.files.append(str(path));self.list.insert('end',path.name);added+=1
        self.status.set(f'Added {added} book(s). {len(self.files)} in queue.'+(f' Skipped {skipped} unsupported file(s) or folders.' if skipped else ''))
    def clear_files(self):
        if not self.busy:self.files.clear();self.list.delete(0,'end')
    def browse(self):
        if self.busy:return
        p=filedialog.askdirectory()
        if p:self.output.set(p)
    def open_folder(self):
        p=Path(self.output.get())
        if p.is_dir():os.startfile(str(p))
    def close(self):
        if self.busy or self.updating:messagebox.showinfo('Work in progress','Please wait until the current operation finishes.');return
        if self.poll_id:self.root.after_cancel(self.poll_id);self.poll_id=None
        self.pulse.stop()
        self.root.destroy()
        gc.collect()
    def start(self):
        if self.busy or self.updating:return
        if not self.files:messagebox.showinfo('Add books','Choose at least one book first.');return
        calibre=shutil.which('calibre-debug')
        if not calibre:
            for base in (os.environ.get('ProgramFiles',''),os.environ.get('ProgramFiles(x86)','')):
                p=Path(base)/'Calibre2'/'calibre-debug.exe'
                if p.is_file():calibre=str(p);break
        if not calibre:messagebox.showerror('Calibre required','Install Calibre for Windows, then reopen this app. See README.txt.');return
        try:
            target=Path(self.output.get()).expanduser().resolve();target.mkdir(parents=True,exist_ok=True)
        except Exception as e:messagebox.showerror('Output folder',str(e));return
        self.busy=True;self.go.config(state='disabled');self.add.config(state='disabled');self.clear.config(state='disabled');self.combo.config(state='disabled')
        self.started=time.monotonic();self.last_activity=self.started;self.book_progress['value']=0;self.batch_progress['value']=0;self.pulse.start(12)
        args=(calibre,list(self.files),target,FORMATS[self.format.get()],self.chapter.get())
        threading.Thread(target=self.batch,args=args,daemon=True).start()
    def update_state(self,active,label=''):
        self.updating=active
        for widget in (self.go,self.add,self.clear,self.update_button):widget.config(state='disabled' if active else 'normal')
        self.combo.config(state='disabled' if active else 'readonly')
        if active:
            self.started=time.monotonic();self.last_activity=self.started;self.pulse.start(12);self.status.set(label)
        else:self.pulse.stop()
    def check_updates(self):
        if self.busy or self.updating:
            messagebox.showinfo('Updates','Finish the current operation before checking for updates.');return
        self.update_state(True,'Checking GitHub Releases…')
        def worker():
            try:
                from updater import check_latest
                self.messages.put(('update_found',check_latest(VERSION)))
            except NoPublishedRelease:self.messages.put(('update_not_published',None))
            except Exception as error:self.messages.put(('update_error',str(error)))
        threading.Thread(target=worker,daemon=True).start()
    def download_new_version(self,info):
        self.update_state(True,'Downloading version '+info['version']+'…')
        def worker():
            try:
                from updater import download_update
                def progress(current,total):self.messages.put(('update_progress',(current,total)))
                path=download_update(info,HERE/'.updates',progress)
                self.messages.put(('update_ready',str(path)))
            except Exception as error:self.messages.put(('update_error',str(error)))
        threading.Thread(target=worker,daemon=True).start()
    def batch(self,calibre,files,target,suffix,chapter):
        ok=0
        for i,source in enumerate(files,1):
            self.messages.put(('book',(i,len(files))))
            self.messages.put(('status',f'Converting {i}/{len(files)}: {Path(source).name}'))
            diagnostics=None;lines=[]
            try:
                result_folder=reserve_output_folder(target,Path(source).stem)
                dest=result_folder/(Path(source).stem+'_clean'+suffix)
                diagnostics=result_folder/'Diagnostics';diagnostics.mkdir()
                with job_folder() as temp:
                    job=Path(temp)/'job.json';job.write_text(json.dumps({'input':source,'output':str(dest),'report':str(diagnostics/'report.json'),'chapter_prefix':chapter}),encoding='utf-8')
                    lines=[];phase=2;phase_end=30
                    env=os.environ.copy();env['PYTHONUNBUFFERED']='1';env['PYTHONIOENCODING']='utf-8'
                    with subprocess.Popen([calibre,'-e',str(HERE/'engine.py'),'--',str(job)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace',creationflags=0x08000000,env=env) as process:
                        for line in process.stdout:
                            lines.append(line);self.messages.put(('activity',None))
                            if line.startswith('PROGRESS_JSON:'):
                                event=json.loads(line.split(':',1)[1]);phase=event['percent'];phase_end={2:30,30:40,40:80,80:96,96:100}.get(phase,100)
                                self.messages.put(('progress',(phase,event['stage'])))
                            else:
                                match=re.match(r'\s*(\d+)%\s+(.*)',line)
                                if match:
                                    p=min(phase_end-1,phase+(phase_end-phase)*int(match[1])/100)
                                    self.messages.put(('progress',(p,match[2].strip())))
                        returncode=process.wait()
                log=''.join(lines)
                (diagnostics/'conversion.log.txt').write_text(log,encoding='utf-8')
                if returncode:raise RuntimeError(log.strip().splitlines()[-1] if log.strip() else 'Conversion failed')
                report=json.loads(log.split('RESULT_JSON:')[-1]);ok+=1
                self.messages.put(('log',f'Converted successfully: {Path(source).name}'))
                if report['entries']:
                    self.messages.put(('log',f'Contents checked: {report["entries"]} links.'))
                    for warning in report['warnings']:self.messages.put(('log','Note: '+warning))
                else:
                    self.messages.put(('log','This book has no chapters.'))
            except Exception as e:
                if diagnostics:
                    try:(diagnostics/'conversion.log.txt').write_text(''.join(lines)+'\nERROR: '+str(e),encoding='utf-8')
                    except OSError:pass
                self.messages.put(('log',f'FAILED: {Path(source).name}: {e}'))
            self.messages.put(('book_done',i))
        self.messages.put(('done',f'Finished: {ok}/{len(files)} books converted. Each result has its own folder; reports and logs are in Diagnostics.'))
    def poll(self):
        if self.poll_id:self.root.after_cancel(self.poll_id);self.poll_id=None
        while not self.messages.empty():
            kind,msg=self.messages.get()
            if kind=='update_found':
                self.update_state(False)
                if msg:
                    self.status.set('Version '+msg['version']+' is available.')
                    if messagebox.askyesno('Update available',f'Version {msg["version"]} is available (installed: {VERSION}).\n\nDownload the installer from {REPOSITORY}?'):
                        self.download_new_version(msg)
                else:self.status.set('You have the latest stable version.');messagebox.showinfo('Updates','You have the latest stable version ('+VERSION+').')
                continue
            if kind=='update_not_published':
                self.update_state(False);self.status.set('No update release has been published yet.');messagebox.showinfo('Updates','No update release has been published yet. You can continue using the app.');continue
            if kind=='update_error':
                self.update_state(False);self.status.set('Update failed. Offline conversion is available.');messagebox.showerror('Updates',msg);continue
            if kind=='update_progress':
                self.last_activity=time.monotonic();current,total=msg
                self.status.set(f'Downloading update: {current/1024:.0f} KB'+(f' / {total/1024:.0f} KB ({100*current/total:.0f}%)' if total else ''))
                continue
            if kind=='update_ready':
                self.update_state(False);self.status.set('Update downloaded and SHA-256 verified.')
                if messagebox.askyesno('Install update','The installer has been downloaded and its checksum verified.\n\nClose the app and open the installer now? Your books and settings will be kept.'):
                    arguments=[msg]
                    if (HERE/'OfflineBookConverter.exe').is_file():arguments+=['/update-dir',str(HERE)]
                    try:subprocess.Popen(arguments,cwd=str(HERE),creationflags=0x08000000)
                    except OSError as error:messagebox.showerror('Updates',str(error));continue
                    self.close();return
                continue
            if kind=='activity':self.last_activity=time.monotonic();continue
            if kind=='book':
                self.book_index,self.book_count=msg;self.current_percent=0;self.book_progress['value']=0;self.stage.set('Starting book…');continue
            if kind=='progress':
                self.current_percent=max(self.current_percent,msg[0]);self.book_progress['value']=self.current_percent
                self.stage.set(f'{self.current_percent:.0f}% — {msg[1]}')
                self.batch_progress['value']=100*(self.book_index-1+self.current_percent/100)/self.book_count
                self.batch_label.set(f'Batch: book {self.book_index} / {self.book_count}')
                continue
            if kind=='book_done':self.batch_progress['value']=100*msg/self.book_count;continue
            if kind in ('status','done'):self.status.set(msg)
            else:
                tag='error' if msg.startswith('FAILED:') else 'success' if msg.startswith('Converted successfully:') or msg=='This book has no chapters.' else 'information'
                self.log.config(state='normal');self.log.insert('end',msg+'\n',tag);self.log.see('end');self.log.config(state='disabled')
            if kind=='done':
                self.pulse.stop();self.batch_progress['value']=100;self.batch_label.set(f'Batch: {self.book_count} / {self.book_count} processed')
                self.busy=False;self.go.config(state='normal');self.add.config(state='normal');self.clear.config(state='normal');self.combo.config(state='readonly')
        if self.busy or self.updating:
            now=time.monotonic();seconds=int(now-self.started);quiet=int(now-self.last_activity)
            self.elapsed.set(f'Running · elapsed {seconds//60:02d}:{seconds%60:02d} · last activity {quiet}s ago')
        elif self.started:
            seconds=int(time.monotonic()-self.started);self.elapsed.set(f'Finished in {seconds//60:02d}:{seconds%60:02d}');self.started=0
        if time.monotonic()-self.last_gc>10:gc.collect();self.last_gc=time.monotonic()
        self.poll_id=self.root.after(150,self.poll)
if __name__=='__main__':App().root.mainloop()
