"""O extrator preserva a contagem que a porta já produz (#2856 linha 500)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from oplog_extracao import bloco_giro

def test_tokens_atravessam_o_extrator():
    giro = bloco_giro({"tool": "acervo", "evento": "verbo", "exit_code": 0,
                       "tokens": 321, "metodo_tokens": "tokenizador qwen2.5"})
    assert giro["tokens"] == 321
    assert giro["metodo_tokens"] == "tokenizador qwen2.5"
