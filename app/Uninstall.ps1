Add-Type -AssemblyName System.Windows.Forms
$answer = [System.Windows.Forms.MessageBox]::Show('Remove Offline Book Converter? Your original and converted books will be kept. Close the converter first.', 'Uninstall Offline Book Converter', 'YesNo', 'Question')
if ($answer -ne 'Yes') { exit }
$installFolder = $PSScriptRoot
$knownFiles = @('app.pyw','engine.py','windows_drop.py','file_drop.py','platform_support.py','covers.py','library.py','kindle.py','online_dialogs.py','updater.py','update_config.json','app.ico','app.png','app.icns','Start.cmd','README.txt','LICENSE.txt','THIRD_PARTY.txt','TESTED.txt','OfflineBookConverter.exe','Uninstall.ps1','installed_files.json')
$manifest = Join-Path $installFolder 'installed_files.json'
if (Test-Path -LiteralPath $manifest) { $knownFiles += @(Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json) }
$prefix = [IO.Path]::GetFullPath($installFolder).TrimEnd('\') + '\'
$ownedDirectories = @()
try {
    foreach ($name in $knownFiles) {
        if ([IO.Path]::IsPathRooted($name) -or ($name -split '[\\/]') -contains '..') { throw 'Invalid installation manifest' }
        $file = [IO.Path]::GetFullPath((Join-Path $installFolder $name))
        if (-not $file.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Installation path escaped the application folder' }
        $parent = [IO.Path]::GetDirectoryName($file)
        while ($parent.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { $ownedDirectories += $parent; $parent = [IO.Path]::GetDirectoryName($parent) }
        if (Test-Path -LiteralPath $file) { Remove-Item -LiteralPath $file -ErrorAction Stop }
    }
    foreach ($directory in ($ownedDirectories | Sort-Object Length -Descending | Select-Object -Unique)) {
        if ($directory.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $directory) -and @(Get-ChildItem -LiteralPath $directory -Force).Count -eq 0) { Remove-Item -LiteralPath $directory }
    }
    $menu = Join-Path ([Environment]::GetFolderPath('Programs')) 'Offline Book Converter'
    $shortcuts = @((Join-Path $menu 'Offline Book Converter.lnk'), (Join-Path ([Environment]::GetFolderPath('DesktopDirectory')) 'Offline Book Converter.lnk'))
    foreach ($shortcut in $shortcuts) { if (Test-Path -LiteralPath $shortcut) { Remove-Item -LiteralPath $shortcut } }
    if ((Test-Path -LiteralPath $menu) -and @(Get-ChildItem -LiteralPath $menu -Force).Count -eq 0) { Remove-Item -LiteralPath $menu }
    Remove-Item -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\OfflineBookConverter' -ErrorAction SilentlyContinue
    if (@(Get-ChildItem -LiteralPath $installFolder -Force).Count -eq 0) { Remove-Item -LiteralPath $installFolder }
    [System.Windows.Forms.MessageBox]::Show('Application removed. Books and any remaining temporary files were kept.', 'Offline Book Converter') | Out-Null
} catch {
    [System.Windows.Forms.MessageBox]::Show(('Could not finish removal. Close the app and run uninstall again. ' + $_.Exception.Message), 'Offline Book Converter') | Out-Null
}
