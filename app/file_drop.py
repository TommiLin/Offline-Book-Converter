from pathlib import Path
import sys
def create_root():
    sys.path.insert(0,str(Path(__file__).resolve().parent/'vendor'))
    import tkinter
    try:
        from tkinterdnd2 import TkinterDnD
        class DropRoot(tkinter.Tk,TkinterDnD.DnDWrapper):pass
        return DropRoot()
    except ImportError:return tkinter.Tk()
def enable(root,handler):
    sys.path.insert(0,str(Path(__file__).resolve().parent/'vendor'))
    from tkinterdnd2 import TkinterDnD,DND_FILES
    TkinterDnD._require(root)
    def dropped(event):
        try:paths=list(root.tk.splitlist(event.data))
        except Exception:return 'refuse_drop'
        # Dispatch only after the native OLE/Cocoa drop callback has returned.
        root.after(0,handler,paths)
        return 'copy'
    root.drop_target_register(DND_FILES)
    root.dnd_bind('<<Drop>>',dropped)
    return TkinterDnD.TkdndVersion
