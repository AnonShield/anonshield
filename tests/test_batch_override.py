import sys
sys.path.insert(0, 'src')

# Test 1: batch_size=2000 com --use-datasets
print("Test 1: batch_size=2000 com --use-datasets")
batch_size = 2000
use_datasets = True
if use_datasets:
    original = batch_size
    batch_size = max(batch_size, 128)
    print(f"  Original: {original} → Novo: {batch_size}")
    print(f"  ✅ Mantém o valor do usuário (maior que 128)")

print()

# Test 2: batch_size=50 com --use-datasets  
print("Test 2: batch_size=50 com --use-datasets")
batch_size = 50
use_datasets = True
if use_datasets:
    original = batch_size
    batch_size = max(batch_size, 128)
    print(f"  Original: {original} → Novo: {batch_size}")
    print(f"  ⚠️  Força mínimo de 128 (ignora valor menor do usuário)")

print()
print("CONCLUSÃO:")
print("  • Não sobrescreve valores MAIORES que 128 ✅")
print("  • Força MÍNIMO de 128 se usuário definir menor ⚠️")
print("  • Pode ser problemático se usuário quer batch pequeno intencional")
