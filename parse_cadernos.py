import os
import glob
import subprocess

def process_cadernos():
    repo_dir = "/home/claudinho/AI/platafirma-harness"
    compilado_path = os.path.join(repo_dir, "registro/diarios-de-bordo-compilados.md")
    
    sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=repo_dir).decode("utf-8").strip()
    
    cadernos = []
    for root, dirs, files in os.walk(os.path.join(repo_dir, "abertura")):
        for f in files:
            if f == "caderno.md":
                cadernos.append(os.path.join(root, f))
                
    cadernos.sort()
    
    compilado_content = [f"arquivo lossless; varredura no harness @{sha}; triagem para expediente é passo futuro\n\n"]
    
    for filepath in cadernos:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        header = []
        body = []
        
        # We consider the title and the FIRST paragraph after it as the header.
        # Alternatively, anything before the first `## ` or before the second paragraph.
        # Let's find the first `## `
        idx = 0
        while idx < len(lines):
            if lines[idx].startswith("## "):
                break
            # Also, if we've seen the title, and a paragraph, and now there is an empty line, and the next line is NOT part of the charter
            # Let's just say everything before the first `## ` is header, EXCEPT if it's too long. The charter is usually short.
            idx += 1
            
        # Let's refine the logic to "title + 1st paragraph"
        # 1. Skip leading empty lines
        idx = 0
        while idx < len(lines) and not lines[idx].strip():
            header.append(lines[idx])
            idx += 1
            
        # 2. Title
        if idx < len(lines) and lines[idx].startswith("# "):
            header.append(lines[idx])
            idx += 1
            
        # 3. Empty lines after title
        while idx < len(lines) and not lines[idx].strip():
            header.append(lines[idx])
            idx += 1
            
        # 4. Charter paragraph (read until next empty line or heading)
        if idx < len(lines) and not lines[idx].startswith("#"):
            while idx < len(lines) and lines[idx].strip() and not lines[idx].startswith("#"):
                header.append(lines[idx])
                idx += 1
                
        # 5. Empty lines after charter
        while idx < len(lines) and not lines[idx].strip():
            header.append(lines[idx])
            idx += 1
            
        # The rest is body
        body = lines[idx:]
        
        # If body has content, we add it to compilation
        if "".join(body).strip():
            rel_path = os.path.relpath(filepath, repo_dir)
            
            # cadeira/chapeu
            parts = rel_path.split("/")
            if len(parts) >= 4: # abertura / cadeira / chapeu / caderno.md
                cadeira_chapeu = f"{parts[1]}/{parts[-2]}"
            else: # abertura / cadeira / caderno.md
                cadeira_chapeu = f"{parts[1]}/head"
                
            compilado_content.append(f"## {cadeira_chapeu} — {rel_path}\n\n")
            compilado_content.append("".join(body))
            if not body[-1].endswith("\n"):
                compilado_content.append("\n")
            compilado_content.append("\n")
            
        # Rewrite the original file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("".join(header))

    os.makedirs(os.path.dirname(compilado_path), exist_ok=True)
    with open(compilado_path, 'w', encoding='utf-8') as f:
        f.write("".join(compilado_content))
        
    print(f"Compilado gravado em {compilado_path}")

if __name__ == '__main__':
    process_cadernos()
