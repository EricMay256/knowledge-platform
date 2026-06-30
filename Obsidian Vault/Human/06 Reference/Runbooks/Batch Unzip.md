---
Type: Runbook
Status:
CreatedAt: 2026-06-27T23:34:03Z
LastUpdated: 2026-06-29T22:06:52Z
Tags:
Aliases:
Related:
---
# Batch Unzip

Purpose: Extract every zip in this folder into a new folder named after itself

Ubuntu Terminal (WSL):

```Bash
for oldname in *; do newname=`echo $oldname | sed -e 's/ //g'`; mv "$oldname" "$newname"; done
```

Pros: Works, for all files at once

```Bash
////Combined whitespace stripping and subsequent unzipping. 7z and tar untested

for oldname in *; do newname=`echo $oldname | sed -e 's/ //g'`; mv "$oldname" "$newname"; done

for file in *.zip; do

    directory="${file%.zip}"

    mkdir -p "$directory" && unzip "$file" -d "$directory"

done

for file in *.7z; do

    directory="${file%.7z}"

    mkdir -p "$directory" && 7z x "$file" -o"$directory"

done

for file in *.rar; do

    directory="${file%.rar}"

    mkdir -p "$directory" && unrar x "$file" "$directory"

done

for file in *.tar*; do

    directory="${file%.tar*}"

    mkdir -p "$directory" && tar -xvf "$file" -C "$directory"

done
```

Windows Cmd

```cmd
for /r %f in (*.zip) do 7z x %f -o*

for /r %f in (*.rar) do 7z x %f -o*

for /r %f in (*.7z) do 7z x %f -o*

for /r %f in (*.tar) do 7z x %f -o*
```

Issues: Fails to operate when spaces exist in the filepath

Powershell for Windows

```Powershell
$f = "a.zip"; $d = $f.Substring(0,$f.Length-4 ); 7z x $f -o$($d)
```

Issues: Output directory not suitably detected

Ubuntu Terminal (WSL):

```Bash
for file in *.zip; do

    directory="${file%.zip}"

    mkdir -p "$directory" && unzip "$file" -d "$directory"

done
```

Purpose: Strip all whitespaces out from files and folders in current directory

Powershell for Windows

```Powershell
get-childitem | foreach { $space = ($_ -contains(" "));

if($space){rename-item -Path $_ -NewName $_.Name.Replace(" ", "_") } }

Issue: Worked once?
```
