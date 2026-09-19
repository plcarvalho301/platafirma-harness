import re
import glob

def clean_line(line):
    # This was a bad idea: line = line.replace('  ', ' ')
    pass

def process_file(filepath):
    with open(filepath, 'r') as f:
        text = f.read()
    
    # 1. "(dono, DATA)" -> "" or "(dono 02/09/2026)" -> ""
    text = re.sub(r'\(dono,\s*[0-9]{2}/[0-9]{2}(/[0-9]{4})?\)', '', text)
    text = re.sub(r'\(dono\s+[0-9]{2}/[0-9]{2}(/[0-9]{4})?\)', '', text)
    
    # 2. ", dono DATA" after arq:NNNN
    text = re.sub(r'(arq:[0-9]{4}), dono [0-9]{2}/[0-9]{2}(/[0-9]{4})?', r'\1', text)
    
    # 3. "(ordem do dono, DATA)" or "(ordem de DATA;"
    text = re.sub(r'\(ordem do dono,\s*[0-9]{2}/[0-9]{2}(/[0-9]{4})?\)', '', text)
    text = re.sub(r'\(ordem de [0-9]{2}/[0-9]{2}/[0-9]{4};\s*', '(', text)
    
    # 4. "Ordem do dono, DATA, em toda..." -> "Vale em toda..."
    text = re.sub(r'Ordem do dono, [0-9]{2}/[0-9]{2}(/[0-9]{4})?, em toda', 'Vale em toda', text)
    
    # 5. "Regra do dono, DATA. Mover..." -> "Mover..."
    text = re.sub(r'Regra do dono, [0-9]{2}/[0-9]{2}(/[0-9]{4})?\.\s*', '', text)
    
    # 6. Titles: "## Decisão posta é chão firme (dono, 08/09/2026)"
    text = re.sub(r'\(dono, [0-9]{2}/[0-9]{2}(/[0-9]{4})?\)', '', text)
    
    # 7. Sentences starting with "Medido"
    # "Medido 12/09/2026: ordem "Leia a msg do Elias" respondida com "você não\n  colou a mensagem", carta parada na caixa."
    text = re.sub(r'Medido [0-9]{2}/[0-9]{2}/[0-9]{4}:\s*ordem.*?carta parada na caixa\.', '', text, flags=re.DOTALL)
    
    text = re.sub(r'Medido na fita da\s*segurança de 11/09:\s*causa certa no 2º turno, zero leitura, cinco turnos de "não"\.', '', text, flags=re.DOTALL)
    text = re.sub(r'\(medido [0-9]{2}/[0-9]{2}(/[0-9]{4})?\)', '', text)
    text = re.sub(r'Medido [0-9]{2}/[0-9]{2}(/[0-9]{4})?:\s*.*?\.', '', text)
    
    # 8. " (dono 02/09/2026)" in arq lines
    text = re.sub(r'\(arq:([0-9]{4}), dono [0-9]{2}/[0-9]{2}/[0-9]{4}\)', r'(arq:\1)', text)
    
    # Bullets starting with - 2026-08-21 in NEGATIVAS
    # Example: "- 2026-08-21 — propus matar o `entrada.md` ... Ponteiro: ... fita de 15/09."
    # We only want to remove them in gestao-estrategica/persona.md (or similar)
    if 'gestao-estrategica' in filepath:
        text = re.sub(r'- \d{4}-\d{2}-\d{2} — .*?(?=\n- |\n\n|\Z)', '', text, flags=re.DOTALL)
        text = re.sub(r'Ponteiro:.*?(?=\n- |\n\n|\Z)', '', text, flags=re.DOTALL)
    
    # Let's clean up punctuation artifacts ONLY where needed
    text = text.replace(' ()', '')
    text = text.replace('( )', '')
    text = text.replace(' .', '.')
    text = text.replace(', )', ')')
    
    # Re-collapse newlines if they are more than 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    with open(filepath, 'w') as f:
        f.write(text)

files = glob.glob('abertura/*/persona.md') + ['abertura/dono.md']
for f in files:
    process_file(f)
