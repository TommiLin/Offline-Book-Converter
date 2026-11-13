using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Diagnostics;
using System.Windows.Forms;
using System.Drawing;
using Microsoft.Win32;
using System.Collections.Generic;
[assembly: AssemblyTitle("Offline Book Converter")]
[assembly: AssemblyVersion("__ASSEMBLY_VERSION__")]
[assembly: AssemblyFileVersion("__ASSEMBLY_VERSION__")]

class Program {
    const string Product="Offline Book Converter";
#if SETUP
    public class ApplicationInUseException:IOException {
        public ApplicationInUseException():base("Please close Offline Book Converter, then click Retry. No files have been changed.") {}
    }
    static string UpdateDirectory=null;
#endif
    public static string FindPython() {
        var candidates=new List<string>();
        foreach(string part in (Environment.GetEnvironmentVariable("PATH")??"").Split(';')) {
            try { candidates.Add(Path.Combine(part.Trim('"'),"pythonw.exe")); } catch {}
        }
        foreach(RegistryKey hive in new[]{Registry.CurrentUser,Registry.LocalMachine}) {
            using(var python=hive.OpenSubKey(@"Software\Python\PythonCore")) {
                if(python==null)continue;
                foreach(string ver in python.GetSubKeyNames())using(var key=python.OpenSubKey(ver+@"\InstallPath")) {
                    if(key!=null) { string path=key.GetValue("") as string; if(!String.IsNullOrEmpty(path)) candidates.Add(Path.Combine(path,"pythonw.exe")); }
                }
            }
        }
        string local=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","Python");
        if(Directory.Exists(local))foreach(string folder in Directory.GetDirectories(local,"Python*"))candidates.Add(Path.Combine(folder,"pythonw.exe"));
        foreach(string p in candidates) if(File.Exists(p) && p.IndexOf("WindowsApps",StringComparison.OrdinalIgnoreCase)<0)return p;
        return null;
    }
    [STAThread] static int Main(string[] args) {
        Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
        try {
#if SETUP
            if(args.Length==2 && args[0]=="/check-files") {
                try { CheckFilesAvailable(Path.GetFullPath(args[1]));return 0; }
                catch(ApplicationInUseException) { return 32; }
                catch { return 1; }
            }
            if(args.Length==2 && args[0]=="/extract-only") { Extract(Path.GetFullPath(args[1]),null);return 0; }
            if(args.Length==2 && args[0]=="/update-dir") {
                UpdateDirectory=Path.GetFullPath(args[1]);
                if(!File.Exists(Path.Combine(UpdateDirectory,"app.pyw")) || !File.Exists(Path.Combine(UpdateDirectory,"OfflineBookConverter.exe")))throw new Exception("The selected update folder is not an existing installation.");
            }
            Application.Run(new SetupForm());
#else
            string python=FindPython();
            if(python==null) { MessageBox.Show("Python 3 with Tkinter is required. Install Python, then try again.",Product,MessageBoxButtons.OK,MessageBoxIcon.Information);return 1; }
            string folder=AppDomain.CurrentDomain.BaseDirectory;
            var info=new ProcessStartInfo(python,"\""+Path.Combine(folder,"app.pyw")+"\"");info.WorkingDirectory=folder;info.UseShellExecute=false;info.CreateNoWindow=true;
            Process.Start(info);
#endif
            return 0;
        } catch(Exception ex) { MessageBox.Show(ex.Message,Product,MessageBoxButtons.OK,MessageBoxIcon.Error);return 1; }
    }
#if SETUP
    static string PackagePath(string destination,string relative) {
        relative=relative.Replace('/',Path.DirectorySeparatorChar);
        string path=Path.GetFullPath(Path.Combine(destination,relative));
        string prefix=Path.GetFullPath(destination).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;
        if(!path.StartsWith(prefix,StringComparison.OrdinalIgnoreCase) || Path.IsPathRooted(relative))throw new InvalidDataException("Invalid package entry.");
        return path;
    }
    public static void CheckFilesAvailable(string destination) {
        // Check every target before creating or replacing even the first file.
        using(Stream stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
        using(var archive=new ZipArchive(stream,ZipArchiveMode.Read)) {
            foreach(var entry in archive.Entries) {
                string path=PackagePath(destination,entry.FullName);
                if(!File.Exists(path))continue;
                try { using(var probe=new FileStream(path,FileMode.Open,FileAccess.ReadWrite,FileShare.None)) {} }
                catch(IOException ex) {
                    int code=ex.HResult & 0xffff;
                    if(code==32 || code==33)throw new ApplicationInUseException();
                    throw;
                }
                catch(UnauthorizedAccessException) {
                    // A loaded Windows DLL may report access denied instead of sharing violation.
                    if(String.Equals(Path.GetExtension(path),".dll",StringComparison.OrdinalIgnoreCase))throw new ApplicationInUseException();
                    throw;
                }
            }
        }
    }
    public static void Extract(string destination,Action<int> progress) {
        CheckFilesAvailable(destination);
        Directory.CreateDirectory(destination);
        using(Stream stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
        using(var archive=new ZipArchive(stream,ZipArchiveMode.Read)) {
            int index=0;
            foreach(var entry in archive.Entries) {
                string path=PackagePath(destination,entry.FullName);
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                using(var input=entry.Open())using(var output=new FileStream(path,FileMode.Create,FileAccess.Write))input.CopyTo(output);
                if(progress!=null)progress(++index*100/archive.Entries.Count);
            }
        }
    }
    public static void Shortcut(string path,string target,string description) {
        Type type=Type.GetTypeFromProgID("WScript.Shell");dynamic shell=Activator.CreateInstance(type);dynamic link=shell.CreateShortcut(path);
        link.TargetPath=target;link.WorkingDirectory=Path.GetDirectoryName(target);link.IconLocation=target+",0";link.Description=description;link.Save();
    }
    class SetupForm:Form {
        TextBox folder;Button install;ProgressBar bar;Label status,title;CheckBox desktop,launch,guide;string installedDirectory;
        public SetupForm() {
            Text=Product+" Setup";ClientSize=new Size(570,360);FormBorderStyle=FormBorderStyle.FixedDialog;MaximizeBox=false;StartPosition=FormStartPosition.CenterScreen;
            Icon=Icon.ExtractAssociatedIcon(Application.ExecutablePath);
            title=new Label{Text=Product+" __VERSION__",Font=new Font("Segoe UI",19,FontStyle.Bold),Location=new Point(22,22),AutoSize=true};Controls.Add(title);
            Controls.Add(new Label{Text="Offline conversion and readable contents. No administrator access needed.",Location=new Point(24,70),Size=new Size(520,28)});
            Controls.Add(new Label{Text="Requires Python 3 with Tkinter and Calibre (installed separately).",Location=new Point(24,100),Size=new Size(520,28)});
            Controls.Add(new Label{Text="Install folder",Location=new Point(24,136),AutoSize=true});
            folder=new TextBox{Text=UpdateDirectory??Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","OfflineBookConverter"),Location=new Point(24,159),Width=435};Controls.Add(folder);
            var browse=new Button{Text="Browse...",Location=new Point(468,157),Width=80};browse.Click+=(s,e)=>{using(var dialog=new FolderBrowserDialog()){if(dialog.ShowDialog()==DialogResult.OK)folder.Text=dialog.SelectedPath;}};Controls.Add(browse);
            desktop=new CheckBox{Text="Create a desktop shortcut",Checked=true,Location=new Point(24,195),Width=300};Controls.Add(desktop);
            bar=new ProgressBar{Location=new Point(24,230),Size=new Size(524,18)};Controls.Add(bar);
            status=new Label{Text="Close Offline Book Converter before installing.",Location=new Point(24,259),Size=new Size(380,80)};Controls.Add(status);
            install=new Button{Text="Install",Location=new Point(438,270),Size=new Size(110,32)};install.Click+=Install;Controls.Add(install);
        }
        void Install(object sender,EventArgs e) {
            install.Enabled=false;
            try {
                string destination=Path.GetFullPath(folder.Text.Trim());
                if(destination==Path.GetPathRoot(destination))throw new Exception("Choose an application folder, not a drive root.");
                if(Directory.Exists(destination) && Directory.GetFileSystemEntries(destination).Length>0 && !(File.Exists(Path.Combine(destination,"OfflineBookConverter.exe")) && File.Exists(Path.Combine(destination,"engine.py"))))throw new Exception("Choose an empty folder or an existing Offline Book Converter installation.");
                bar.Value=0;status.Text="Checking application files...";status.Refresh();
                CheckFilesAvailable(destination);
                status.Text="Installing application files...";Extract(destination,p=>{bar.Value=p;bar.Refresh();});
                string launcher=Path.Combine(destination,"OfflineBookConverter.exe");
                string menu=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs),Product);Directory.CreateDirectory(menu);
                Shortcut(Path.Combine(menu,Product+".lnk"),launcher,Product);
                if(desktop.Checked)Shortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),Product+".lnk"),launcher,Product);
                string uninstall=Path.Combine(destination,"Uninstall.ps1");
                using(var key=Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\OfflineBookConverter")) {
                    key.SetValue("DisplayName",Product);key.SetValue("DisplayVersion","__VERSION__");key.SetValue("DisplayIcon",launcher+",0");key.SetValue("Publisher","Offline Book Converter");key.SetValue("InstallLocation",destination);
                    key.SetValue("UninstallString","powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \""+uninstall+"\"");
                    key.SetValue("NoModify",1);key.SetValue("NoRepair",1);
                }
                ShowCompletion(destination,FindPython()!=null);
            } catch(ApplicationInUseException ex) {
                bar.Value=0;status.Text=ex.Message;install.Text="Retry";install.Enabled=true;
            } catch(Exception ex) { status.Text="Installation could not finish. "+ex.Message;install.Text="Retry";install.Enabled=true; }
        }
        void ShowCompletion(string destination,bool pythonAvailable) {
            installedDirectory=destination;
            foreach(Control control in Controls)control.Visible=(control==title || control==status || control==install);
            status.Location=new Point(24,90);status.Size=new Size(520,75);status.ForeColor=Color.FromArgb(36,112,74);
            status.Text="Installation completed successfully.\n\n"+(pythonAvailable?"Offline Book Converter is ready to use.":"Install Python 3 with Tkinter and Calibre before launching the app.");
            launch=new CheckBox{Text="Launch Offline Book Converter",Checked=pythonAvailable,Enabled=pythonAvailable,Location=new Point(24,185),Size=new Size(500,28)};
            guide=new CheckBox{Text="View quick guide",Checked=false,Location=new Point(24,220),Size=new Size(500,28)};
            Controls.Add(launch);Controls.Add(guide);
            launch.CheckedChanged+=(s,e)=>CompletionChanged();
            install.Click-=Install;install.Click+=FinishSetup;install.Enabled=true;
            CompletionChanged();AcceptButton=install;
        }
        void CompletionChanged() { install.Text=launch.Checked?"Open app":"Close setup"; }
        void FinishSetup(object sender,EventArgs e) {
            install.Enabled=false;
            try {
                if(launch.Checked) {
                    var start=new ProcessStartInfo(Path.Combine(installedDirectory,"OfflineBookConverter.exe"));
                    start.WorkingDirectory=installedDirectory;start.UseShellExecute=false;
                    Process.Start(start);
                    launch.Checked=false;
                }
                if(guide.Checked) {
                    var start=new ProcessStartInfo(Path.Combine(installedDirectory,"README.txt"));
                    start.UseShellExecute=true;Process.Start(start);
                    guide.Checked=false;
                }
                Close();
            } catch(Exception ex) {
                status.Text="Installation is complete. The selected item could not be opened.\n\n"+ex.Message;
                install.Enabled=true;
            }
        }
    }
#endif
}
