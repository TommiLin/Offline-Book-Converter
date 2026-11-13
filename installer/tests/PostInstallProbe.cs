// Tests completion UI and launches a harmless fixture executable, never user apps.
using System;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Windows.Forms;
class PostInstallProbe {
    static object Field(object form,string name) { return form.GetType().GetField(name,BindingFlags.Instance|BindingFlags.NonPublic).GetValue(form); }
    static Form Completion(Type type,string folder,bool python) {
        var form=(Form)Activator.CreateInstance(type,true);
        type.GetMethod("ShowCompletion",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(form,new object[]{folder,python});
        return form;
    }
    static void Finish(Form form) { form.GetType().GetMethod("FinishSetup",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(form,new object[]{null,EventArgs.Empty}); }
    static void Check(bool condition,string message) { if(!condition)throw new Exception(message); }
    [STAThread] static int Main(string[] args) {
        Application.EnableVisualStyles();
        try {
            var type=Assembly.LoadFrom(args[0]).GetType("Program+SetupForm");string target=args[1];string marker=Path.Combine(target,"launched.txt");
            using(var form=Completion(type,target,true)) {
                Check(((CheckBox)Field(form,"launch")).Checked,"Launch should default to on.");
                Check(!((CheckBox)Field(form,"guide")).Checked,"Guide should default to off.");
                Check(((Button)Field(form,"install")).Text=="Open app","The action must be explicit.");
                Finish(form);
            }
            for(int i=0;i<100 && !File.Exists(marker);i++)Thread.Sleep(50);
            Check(File.Exists(marker),"Selected app was not launched.");File.Delete(marker);
            using(var form=Completion(type,target,true)) {
                ((CheckBox)Field(form,"launch")).Checked=false;
                Check(((Button)Field(form,"install")).Text=="Close setup","Unchecked launch should close setup.");Finish(form);
            }
            Check(!File.Exists(marker),"Unchecked launch must not start the app.");
            using(var form=Completion(type,target,false)) {
                var launch=(CheckBox)Field(form,"launch");Check(!launch.Checked && !launch.Enabled,"Missing Python must disable launch.");Finish(form);
            }
            Check(!File.Exists(marker),"Missing Python must not launch the app.");
            Console.WriteLine("PASS: completion options, selected launch, unchecked close and missing-Python behavior.");return 0;
        } catch(Exception ex) { Console.WriteLine(ex);return 1; }
    }
}
