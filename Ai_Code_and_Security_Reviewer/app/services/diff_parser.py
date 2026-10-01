from dataclasses import dataclass,field


@dataclass
class ChangedFile:
    path: str
    diff_text: str = ""
    added_lines: set[int] = field(default_factory=set)

def parse_diff(raw_diff:str) -> list[ChangedFile]:

    files:list[ChangedFile]=[]
    current: ChangedFile | None  = None
    new_line=0 # line number on the NEW side, advances as we walk hunks

    for line in raw_diff.splitlines():
         # --- new file block ---
        if line.startswith("diff --git"):
            # "diff --git a/foo.py b/foo.py" → take the b/ side
            file_path=line.split(" b/")[-1]
            current=ChangedFile(path=file_path)
            files.append(current)
            continue

        if current is None:
            continue   # junk before the first file block

        # --- hunk header: @@ -a,b +c,d @@ ... ---    
        if line.startswith("@@"):
            # "+c,d" tells us where in the NEW file this hunk starts
            # format: @@ -old_start,old_count +new_start,new_count @@

            try:
                plus_part=line.split("+",1)[1].split(" ",1)[0]  # "c,d"
                new_start=int(plus_part.split(",")[0])
                new_line=new_start
            except (IndexError,ValueError):
                new_line=0
            current.diff_text += line +"\n"
            continue

         # --- content lines inside a hunk ---


        if line.startswith("+") and not line.startswith("+++"):
            # added line: it exists in the NEW file at new_line
            current.added_lines.add(new_line)
            new_line += 1
            current.diff_text += line + "\n"


        elif line.startswith("-") and not line.startswith("---"):
            # removed line: it's gone from the NEW file, so new_line does NOT advance
            current.diff_text += line + "\n"

        elif line.startswith(" "):
            # context line: exists in both, so new_line advances
            new_line += 1
            current.diff_text += line + "\n"

        else:
            # headers like "index ...", "--- a/x", "+++ b/x", "\ No newline..."
            current.diff_text += line + "\n"

    return files