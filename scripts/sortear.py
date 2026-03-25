import random
import json
import os

SEED = 30
NUMEROS_FILE = "numeros_sorteados.json"
MIN_NUM = 2
MAX_NUM = 6473

def carregar_sorteados():
  """Carrega os números já sorteados do arquivo."""
  if os.path.exists(NUMEROS_FILE):
    with open(NUMEROS_FILE, 'r') as f:
      return set(json.load(f))
  return set()

def salvar_sorteados(sorteados):
  """Salva os números sorteados no arquivo."""
  with open(NUMEROS_FILE, 'w') as f:
    json.dump(list(sorteados), f)

def sortear(quantidade):
  """Sorteia uma quantidade de números únicos."""
  sorteados = carregar_sorteados()
  disponiveis = set(range(MIN_NUM, MAX_NUM + 1)) - sorteados
  
  if len(disponiveis) < quantidade:
    print(f"Apenas {len(disponiveis)} números disponíveis!")
    quantidade = len(disponiveis)
  
  if quantidade == 0:
    print("Todos os números já foram sorteados!")
    return []
  
  # Usar seed fixa com estado baseado nos já sorteados
  random.seed(SEED + len(sorteados))
  novos = random.sample(list(disponiveis), quantidade)
  
  sorteados.update(novos)
  salvar_sorteados(sorteados)
  
  return novos

if __name__ == "__main__":
  qtd = int(input("Quantos números deseja sortear? "))
  numeros = sortear(qtd)
  print(f"\nNúmeros sorteados: {sorted(numeros)}")
  print(f"Total de números já sorteados: {len(carregar_sorteados())}/{MAX_NUM - MIN_NUM + 1}")